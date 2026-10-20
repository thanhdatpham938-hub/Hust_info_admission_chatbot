"""Cac node cua graph (PLAN - StateGraph (v1), muc 2-4).

Moi node la ham async nhan ChatState, tra phan state can ghi (LangGraph ghi de theo khoa). `turn` ghi de ca dict
nen moi node tra {**turn, ...}. Phu thuoc ben ngoai (Router, bang tool, ToolContext, ngay) TIEM vao qua GraphDeps:
test thay bang ban gia, khong goi OpenAI, khong can DB.

Moi nhanh ket thuc o save_context; node tra loi chi dat `outcome`, save_context quyet ngu canh (PLAN StateGraph 3).
"""

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.graph import templates as T
from app.graph.context_rules import (build_pending, merge_context, merge_pick, pick_choice, register_unclear,
                                     update_context)
from app.graph.dispatch import TOOL_TIMEOUT_S, run_calls
from app.graph.router import RouterError, calls_as_dicts, looks_english
from app.graph.state import ChatState, ConvContext, append_message, empty_context, new_turn
from app.tools.common import TOO_MANY_MESSAGE

REFUSAL = {"OTHER_UNIVERSITY": "other_university", "GENERAL_OFF_TOPIC": "off_topic"}
# fallback_reason -> outcome cho save_context. "not_found"/"low_confidence" tinh la answered: cau hoi hop le, nen
# nho nganh da xac nhan cho luot sau (PLAN StateGraph 3). Tu choi va loi he thong giu nguyen ngu canh.
OUTCOME = {"other_university": "refused", "off_topic": "refused", "other_language": "refused",
           "no_tool": "refused", "too_many": "refused", "llm_error": "refused", "database_error": "refused",
           "internal_error": "refused", "cancel": "cancel", "released": "released",
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
    async def router_node(s: ChatState) -> dict:
        ctx, t = _ctx(s), s["turn"]
        q = t["question"]
        history = (s.get("messages") or [])[:-1]          # tin nhan cuoi la cau hien tai: route() tu them
        try:
            out = await deps.route(q, ctx, history, deps.today())
        except RouterError:
            lang = "en" if looks_english(q) else ctx.get("last_language", "vi")
            return {"turn": {**t, "language": lang, "intent": "UNKNOWN", "route": "fallback",
                             "fallback_reason": "llm_error", "error_code": "LLM_ERROR"}}
        t = {**t, "router": out.model_dump(mode="json"), "language": out.language, "intent": out.intent}
        pending = ctx.get("pending")
        if pending:                                        # dang cho chon: xet pick_status truoc (PLAN State 4.3c)
            if out.pick_status == "cancel":
                return {"turn": {**t, "route": "fallback", "fallback_reason": "cancel"}}
            if out.pick_status == "unclear":
                new_ctx, released = register_unclear(ctx)
                if released:
                    return {"context": new_ctx, "turn": {**t, "route": "fallback", "fallback_reason": "released",
                                                         "released_pending": pending}}
                return {"context": new_ctx, "turn": {**t, "intent": "CLARIFICATION_NEEDED",
                                                     "route": "clarification", "fallback_reason": "unclear"}}
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
        return {"turn": {**t, "route": "answer"}}

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

    # ------------------------------------------------------------ answer (TAM: ban nhap tu du lieu tho, muc 7)
    async def answer(s: ChatState) -> dict:
        t = s["turn"]
        blocks, sources = [], []
        for c, r in zip(t["calls"], t["results"]):
            blocks.append({"tool": c["tool"], "status": r.get("status"), "data": _compact(r.get("data")),
                           "missing": r.get("missing") or None})
            for src in r.get("sources") or []:
                if src.get("url") and src["url"] not in {x["url"] for x in sources}:
                    sources.append({"title": src.get("title", ""), "url": src["url"]})
        text = json.dumps(blocks, ensure_ascii=False, indent=1)
        return {"turn": {**t, "answer": text, "citations": sources, "draft": True, "outcome": "answered",
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
            "announcement": announcement, "fallback": fallback, "answer": answer, "save_context": save_context}


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


def _compact(x):
    """Bo truong rong cho ban nhap gon."""
    if isinstance(x, dict):
        return {k: _compact(v) for k, v in x.items() if v not in (None, [], {}, "")}
    if isinstance(x, list):
        return [_compact(v) for v in x]
    return x


__all__ = ["GraphDeps", "make_nodes", "calls_as_dicts"]
