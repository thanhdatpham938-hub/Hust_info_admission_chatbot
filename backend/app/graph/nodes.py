"""Cac node cua graph (PLAN - StateGraph (v1), muc 2-4).

Moi node la ham async nhan ChatState, tra phan state can ghi (LangGraph ghi de theo khoa). `turn` ghi de ca dict
nen moi node tra {**turn, ...}. Phu thuoc ben ngoai (Router, bang tool, ToolContext, ngay) TIEM vao qua GraphDeps:
test thay bang ban gia, khong goi OpenAI, khong can DB.

Moi nhanh ket thuc o save_context; node tra loi chi dat `outcome`, save_context quyet ngu canh (PLAN StateGraph 3).
"""

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.graph import render
from app.graph import templates as T
from app.graph.context_rules import (
    build_pending,
    merge_context,
    merge_pick,
    pick_choice,
    register_unclear,
    update_context,
)
from app.graph.dispatch import TOOL_TIMEOUT_S, run_calls
from app.graph.guardrails.check import finalize, text_only_missing_citation, verify
from app.graph.prefilter import GATE_INTENT, prefilter
from app.graph.router import RouterError, calls_as_dicts, looks_english
from app.graph.state import (
    ChatState,
    ConvContext,
    append_message,
    empty_context,
    new_turn,
)
from app.graph.synthesizer import SynthError, build_evidence
from app.graph.synthesizer import generate as generate_text
from app.schemas.rag import RagSearchInput
from app.tools.common import TOO_MANY_MESSAGE
from app.tools.tuition import NEED_SCOPE_MESSAGE

log = logging.getLogger(__name__)
MAX_REWRITES = 2           # nguoi dung chot 2026-10-20 (Q7): viet lai toi da 2 lan, van sai -> template_answer
REFUSAL = {"OTHER_UNIVERSITY": "other_university", "GENERAL_OFF_TOPIC": "off_topic"}
# fallback_reason -> outcome cho save_context. "not_found"/"low_confidence" tinh la answered: cau hoi hop le, nen
# nho nganh da xac nhan cho luot sau (PLAN StateGraph 3). Tu choi va loi he thong giu nguyen ngu canh.
OUTCOME = {"other_university": "refused", "off_topic": "refused", "other_language": "refused",
           "no_tool": "refused", "too_many": "refused", "llm_error": "refused", "database_error": "refused",
           "internal_error": "refused", "cancel": "cancel", "released": "released", "empty_input": "refused",
           "too_long": "refused",
           "not_found": "answered", "low_confidence": "answered"}
ERROR_REASON = {"DATABASE_ERROR": "database_error", "LLM_ERROR": "llm_error", "INTERNAL_ERROR": "internal_error"}


@dataclass
class GraphDeps:
    route: Callable[..., Awaitable]                       # app.graph.router.route hoac ban gia
    tools: dict | None = None                             # None = 7 tool that (dispatch.TOOLS)
    tool_ctx: Callable[[], Awaitable] | None = None       # tra ToolContext; None = tool tu nap
    program_group: Mapping[str, str] = field(default_factory=dict)   # pick_choice buoc 5b
    today: Callable[[], date] = date.today
    tool_timeout: float = TOOL_TIMEOUT_S
    synthesize: Callable[..., Awaitable[str]] | None = None   # (payload, issues) -> van ban; None = OpenAI that
    program_names: Mapping[str, tuple[str, str | None]] = field(default_factory=dict)   # Q6 = C


def _ctx(s: ChatState) -> ConvContext:
    return s.get("context") or empty_context()


def make_nodes(deps: GraphDeps) -> dict[str, Callable]:
    # ------------------------------------------------------------ start_turn
    async def start_turn(s: ChatState) -> dict:
        incoming = s.get("turn") or {}
        q = incoming.get("question", "")
        return {"turn": new_turn(q, incoming.get("choice")), "context": _ctx(s),
                "messages": append_message(s.get("messages") or [], "user", q)}

    # ------------------------------------------------------------ pick_choice (duong tat, khong LLM)
    async def pick_node(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        p = ctx["pending"]
        out = pick_choice(t["question"], p, t.get("choice"), deps.program_group)
        lang = ctx.get("last_language", "vi")
        if out.calls:
            return {"turn": {**t, "calls": out.calls, "language": lang,
                             "intent": p.get("intent", ctx.get("last_intent") or "ADMISSION_QUERY"),
                             "route": "run_tools"}}
        if out.too_many:
            return {"turn": {**t, "language": lang, "intent": "CLARIFICATION_NEEDED", "route": "clarification",
                             "fallback_reason": "too_many_choices"}}
        return {"turn": {**t, "route": "router"}}

    # ------------------------------------------------------------ router (LLM)
    def unclear_turn(ctx: ConvContext, t: dict) -> dict:
        """Dang cho chon ma khong ro chon gi (PLAN State 4.3c): hoi lai, den MAX_UNCLEAR thi tha pending."""
        new_ctx, released = register_unclear(ctx)
        if released:
            return {"context": new_ctx, "turn": {**t, "route": "fallback", "fallback_reason": "released",
                                                 "released_pending": ctx["pending"]}}
        return {"context": new_ctx, "turn": {**t, "intent": "CLARIFICATION_NEEDED", "route": "clarification",
                                             "fallback_reason": "unclear"}}

    async def router_node(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        q = t["question"]
        gate = prefilter(q, ctx)                           # PLAN Toi uu Router A: code tu quyet -> khong goi LLM
        if gate:
            lang = "en" if looks_english(q) else ctx.get("last_language", "vi")
            if gate == "unclear":
                return unclear_turn(ctx, {**t, "language": lang})
            return {"turn": {**t, "language": lang, "intent": GATE_INTENT.get(gate, "UNKNOWN"), "route": "fallback",
                             "fallback_reason": gate}}
        history = (s.get("messages") or [])[:-1]          # tin nhan cuoi la cau hien tai: route() tu them
        # Co ToolContext thi Router dung bo quet goi y + kiem sau (PLAN Sua loi, buoc 3); test gia khong truyen
        kw = {"tctx": await deps.tool_ctx()} if deps.tool_ctx else {}
        try:
            out = await deps.route(q, ctx, history, deps.today(), **kw)
        except RouterError as e:
            log.warning("Router loi: %s", e)          # do 2026-10-21: 31 cau loi ma khong biet loai loi gi
            lang = "en" if looks_english(q) else ctx.get("last_language", "vi")
            return {"turn": {**t, "language": lang, "intent": "UNKNOWN", "route": "fallback",
                             "fallback_reason": "llm_error", "error_code": "LLM_ERROR"}}
        t = {**t, "router": out.model_dump(mode="json"), "language": out.language, "intent": out.intent}
        pending = ctx.get("pending")
        if pending:                                        # dang cho chon: xet pick_status truoc (PLAN State 4.3c)
            if out.pick_status == "cancel":
                return {"turn": {**t, "route": "fallback", "fallback_reason": "cancel"}}
            if out.pick_status == "unclear":
                return unclear_turn(ctx, t)
            if out.pick_status == "picked":
                return {"turn": {**t, "route": "merge"}}
        if out.language == "other":
            return {"turn": {**t, "route": "fallback", "fallback_reason": "other_language"}}
        if out.intent in REFUSAL:
            return {"turn": {**t, "route": "fallback", "fallback_reason": REFUSAL[out.intent]}}
        if out.intent == "UNKNOWN":
            return {"turn": {**t, "route": "fallback", "fallback_reason": "no_tool"}}
        if out.intent == "CLARIFICATION_NEEDED":
            return {"turn": {**t, "route": "clarification", "fallback_reason": "missing_info"}}
        return {"turn": {**t, "route": "merge"}}

    # ------------------------------------------------------------ merge (C1-C5)
    async def merge_node(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        r = t["router"]
        router_calls = [{"tool": c["tool"], "args": c["args"]} for c in r["calls"]]
        pending = ctx.get("pending")
        calls = None
        if pending and r.get("pick_status") == "picked":
            calls = merge_pick(pending, r.get("picked") or [], router_calls)     # None: picked sai -> cau moi
        if calls is None:
            base = {**ctx, "pending": None} if pending else ctx                   # C5: cau moi thi bo pending
            calls = merge_context(router_calls, r.get("refers_to_context", False), base)
        if not calls:
            return {"turn": {**t, "calls": [], "route": "fallback", "fallback_reason": "no_tool"}}
        return {"turn": {**t, "calls": calls, "route": "run_tools"}}

    # ------------------------------------------------------------ run_tools
    async def run_tools(s: ChatState) -> dict:
        t = s["turn"]
        tctx = await deps.tool_ctx() if deps.tool_ctx else None
        results = await run_calls(t["calls"], tctx, deps.tools, deps.tool_timeout)
        return {"turn": {**t, "results": results}}

    # ------------------------------------------------------------ check_status (PLAN StateGraph 4)
    async def check_status(s: ChatState) -> dict:
        t = s["turn"]
        res = t["results"]
        st = [r.get("status") for r in res]
        if "ambiguous" in st:
            return {"turn": {**t, "route": "clarification", "fallback_reason": "ambiguous"}}
        swapped = None if t.get("rerouted") else _tuition_to_rag(t)
        if swapped:                                        # buoc 4 (PLAN Sua loi): chay lai mot lan, lenh khac giu done
            return {"turn": {**t, "calls": swapped, "rerouted": True, "route": "run_tools"}}
        if "invalid" in st:                                # Q1 = A: tu choi ca luot
            too_many = any(r.get("status") == "invalid" and (r.get("message") or "").startswith(TOO_MANY_MESSAGE)
                           for r in res)
            return {"turn": {**t, "route": "fallback", "fallback_reason": "too_many" if too_many else "no_tool",
                             "error_code": "INVALID_REQUEST"}}
        if t.get("intent") == "ANNOUNCEMENT_QUERY" and _channels(t):
            return {"turn": {**t, "route": "announcement"}}
        if all(x in ("not_found", "error") for x in st):
            errs = [r["error_code"] for r in res if r.get("status") == "error"]
            if len(errs) == len(res):
                return {"turn": {**t, "route": "fallback", "fallback_reason": ERROR_REASON.get(errs[0],
                                                                                              "internal_error"),
                                 "error_code": errs[0]}}
            has_missing = any(r.get("missing") for r in res)
            low = any(r.get("error_code") == "LOW_RETRIEVAL_CONFIDENCE" for r in res)
            reason = "low_confidence" if low and not has_missing else "not_found"
            return {"turn": {**t, "route": "fallback", "fallback_reason": reason}}
        return {"turn": {**t, "route": "generate"}}

    # ------------------------------------------------------------ clarification
    async def clarification(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        lang, reason = t.get("language", "vi"), t.get("fallback_reason")
        if reason == "missing_info":
            missing = (t.get("router") or {}).get("missing_info") or "ngành, năm"
            return {"turn": {**t, "answer": T.render("missing_info", lang, missing_info=missing),
                             "clarification": None, "pending_new": None, "outcome": "clarify",
                             "intent_final": "CLARIFICATION_NEEDED"}}
        if reason == "ambiguous":
            pending = build_pending(t["calls"], t["results"])
            pending["intent"] = t.get("intent", "ADMISSION_QUERY")
            code = "ambiguous"
        else:                                              # unclear / too_many_choices: van giu pending cu
            pending = ctx["pending"]
            code = reason
        cands = pending["candidates"]
        text = T.render(code, lang, mention=pending["mention"], kind=T.kind_name(pending["entity_type"], lang),
                        choices=T.choices_block(cands), codes=" / ".join(c["code"] for c in cands))
        return {"turn": {**t, "answer": text, "pending_new": pending, "outcome": "clarify",
                         "clarification": {"mention": pending["mention"], "choices": cands},
                         "intent_final": "CLARIFICATION_NEEDED"}}

    # ------------------------------------------------------------ announcement (AC9)
    async def announcement(s: ChatState) -> dict:
        t = s["turn"]
        lang = t.get("language", "vi")
        chans = _channels(t)
        text = "\n".join(T.render("announcement", lang, faculty=name, url=url) for name, url in chans)
        return {"turn": {**t, "answer": text, "outcome": "answered", "intent_final": "ANNOUNCEMENT_QUERY",
                         "citations": [{"title": name, "url": url} for name, url in chans]}}

    # ------------------------------------------------------------ fallback (cau mau)
    async def fallback(s: ChatState) -> dict:
        t = s["turn"]
        lang, reason = t.get("language", "vi"), t.get("fallback_reason") or "no_tool"
        kw = {}
        if reason == "not_found":
            kw["missing"], kw["available"] = T.missing_parts(t.get("results") or [], lang)
        if reason == "released":
            p = t.get("released_pending") or {}
            kw["mention"] = p.get("mention", "")
            kw["example"] = (p.get("candidates") or [{"code": "IT1"}])[-1]["code"]
        lang_used = "other" if reason == "other_language" else lang
        intent = {"cancel": "UNKNOWN", "released": "UNKNOWN", "llm_error": "UNKNOWN"}.get(reason,
                                                                                         t.get("intent", "UNKNOWN"))
        return {"turn": {**t, "answer": T.render(reason, lang_used, **kw), "outcome": OUTCOME.get(reason, "refused"),
                         "intent_final": intent}}

    # ------------------------------------------------------------ generate (LLM viet, PLAN Synthesizer 2-3)
    async def generate(s: ChatState) -> dict:
        t = s["turn"]
        ev = t.get("evidence") or build_evidence(
            t["question"], t.get("intent", "UNKNOWN"), t.get("language", "vi"),
            (t.get("router") or {}).get("scope_note"), t["calls"], t["results"], deps.program_names, deps.today())
        synth = deps.synthesize or generate_text
        text = None
        for _ in range(2):                                  # loi goi OpenAI: thu lai 1 lan (muc 4.4)
            try:
                text = await synth(ev["payload"], t.get("verify_issues") or None)
                break
            except SynthError as e:
                log.warning("Synthesizer loi: %s", e)
        if text is None:
            return {"turn": {**t, "evidence": ev, "route": "template_answer", "synth_error": True}}
        return {"turn": {**t, "evidence": ev, "draft_text": text, "route": "verify"}}

    # ------------------------------------------------------------ verify (code kiem, PLAN Synthesizer 4)
    async def verify_node(s: ChatState) -> dict:
        t = s["turn"]
        ev, lang = t["evidence"], t.get("language", "vi")
        text, issues, used = verify(t["draft_text"], ev)
        log_ = (t.get("verify_log") or []) + [issues]
        if not issues:
            answer, citations = finalize(text, ev, used, lang)
            return {"turn": {**t, "answer": answer, "citations": citations, "draft": False, "verify_log": log_,
                             "outcome": "answered", "intent_final": t.get("intent", "UNKNOWN"),
                             "route": "save_context"}}
        if t.get("retry", 0) < MAX_REWRITES:               # Q7: viet lai toi da 2 lan
            return {"turn": {**t, "verify_issues": issues, "retry": t.get("retry", 0) + 1, "verify_log": log_,
                             "route": "generate"}}
        if text_only_missing_citation(issues, ev):         # N13: noi that, khong dan doan van ban tho
            return {"turn": {**t, "verify_issues": issues, "verify_log": log_, "route": "fallback",
                             "fallback_reason": "low_confidence"}}
        return {"turn": {**t, "verify_issues": issues, "verify_log": log_, "route": "template_answer"}}

    # ------------------------------------------------------------ template_answer (code dung tu du lieu tho)
    async def template_node(s: ChatState) -> dict:
        t = s["turn"]
        lang = t.get("language", "vi")
        return {"turn": {**t, "answer": render.template_answer(t["evidence"], t["results"], lang),
                         "citations": t["evidence"]["sources"], "used_template": True, "outcome": "answered",
                         "intent_final": t.get("intent", "UNKNOWN")}}

    # ------------------------------------------------------------ save_context (mot cho duy nhat doi ngu canh)
    async def save_context(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        outcome = t.get("outcome", "refused")
        if outcome == "answered":
            new = update_context(ctx, "answered", t.get("calls") or [], t.get("results") or [],
                                 intent=t.get("intent_final"))
        elif outcome == "clarify":
            new = update_context(ctx, "clarify", pending=t.get("pending_new"))
        else:
            new = update_context(ctx, outcome)            # refused / cancel / released
        new["last_language"] = t.get("language") or ctx.get("last_language", "vi")
        return {"context": new, "messages": append_message(s.get("messages") or [], "assistant", t.get("answer", ""))}

    return {"start_turn": start_turn, "pick_choice": pick_node, "router": router_node, "merge": merge_node,
            "run_tools": run_tools, "check_status": check_status, "clarification": clarification,
            "announcement": announcement, "fallback": fallback, "generate": generate, "verify": verify_node,
            "template_answer": template_node, "save_context": save_context}


def _tuition_to_rag(t: dict) -> list[dict] | None:
    """Hoc phi KHONG gan nganh / nhom (sinh vien nuoc ngoai, hoc lai, hoc ky he) nam trong van ban quy dinh hoc phi:
    lenh tuition_fees bi invalid vi thieu pham vi -> doi sang rag_search voi `need` cua Router (luon tieng Viet).
    Chuyen tat dinh bang code thay vi day Router them quy tac (S29). Da co rag_search thi chi bo lenh hoc phi.
    Tra None neu khong co gi de doi."""
    calls, res = t.get("calls") or [], t.get("results") or []
    bad = {i for i, (c, r) in enumerate(zip(calls, res))
           if c["tool"] == "tuition_fees" and r.get("status") == "invalid" and r.get("message") == NEED_SCOPE_MESSAGE}
    if not bad:
        return None
    has_rag = any(c["tool"] == "rag_search" for c in calls)
    query = (t.get("router") or {}).get("need") or t["question"]
    out = []
    for i, (c, r) in enumerate(zip(calls, res)):
        if i not in bad:
            out.append({**c, "done": r})
        elif not has_rag:
            out.append({"tool": "rag_search", "args": RagSearchInput(query=query).model_dump(),
                        "done": None})
            has_rag = True
    return out


def _channels(t: dict) -> list[tuple[str, str]]:
    """(ten Truong/Khoa, official_channel_url) tu ket qua university_info."""
    out = []
    for c, r in zip(t.get("calls") or [], t.get("results") or []):
        if c["tool"] != "university_info" or r.get("status") not in ("ok", "partial"):
            continue
        for f in (r.get("data") or {}).get("faculties") or []:
            if f.get("official_channel_url"):
                out.append((f.get("faculty_name", ""), f["official_channel_url"]))
    return out


__all__ = ["GraphDeps", "make_nodes", "calls_as_dicts"]
