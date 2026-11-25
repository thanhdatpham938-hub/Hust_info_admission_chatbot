"""Do Router that (goi OpenAI) -> AC3 (PRD 21) va pick_status (PLAN - Router (v1), muc 5).

  router_cases.csv       intent (AC3), tool, ngon ngu, scope_note, "doan ma", query T7 tieng Viet
  router_pick_cases.csv  pick_status / picked khi bot dang cho nguoi dung chon

Nhan do tro ly soan nhap, NGUOI DUNG soat (cot `duyet`). Ca sai KHONG sua nhan cho khop, KHONG dua cau do vao vi du
cua prompt: sua prompt bang quy tac (PLAN Router muc 5).

Dung: python scripts/eval_router.py [--limit N]        (mac dinh chay 1 lan; --runs N neu that su can)
      -> in so do + ghi docs/ghi_chu/<ngay> - Do AC3 Router.md
      --raw FILE            ghi dau ra tho (can cho --only-failed lan sau)
      --only-failed FILE    chi chay lai ca sai trong FILE (--raw lan truoc); ghi "(mot phan)", KHONG phai so AC3
      --no-cache            khong doc cache, goi OpenAI that
      --today YYYY-MM-DD    ngay dua vao prompt; giu co dinh thi dung lai cache qua nhieu ngay
Ton phi THAT (goi OpenAI that): ~0,18 USD moi lan chay du bo 215 cau. Cache (data/cache/eval_router.json, PLAN - Toi
uu Router (v1) buoc B): cau co prompt + ngu canh + ngay y het lan truoc thi lay lai ket qua, khong goi API.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
import build_db  # noqa: E402
from app.core.llm import get_llm  # noqa: E402
from app.entity_resolution.normalize import compact  # noqa: E402
from app.graph.prefilter import GATE_INTENT, prefilter
from app.graph.router import (  # noqa: E402
    RouterError,
    calls_as_dicts,
    looks_english,
    route,
)
from app.graph.state import empty_context  # noqa: E402
from app.tools.context import ToolContext  # noqa: E402

EVAL = ROOT / "backend" / "tests" / "eval"
OUT = ROOT / "docs" / "ghi_chu" / f"{date.today()} - Do AC3 Router.md"
OUT_PARTIAL = OUT.with_name(f"{OUT.stem} (mot phan).md")
CACHE = ROOT / "data" / "cache" / "eval_router.json"          # data/* ngoai git
CONCURRENCY = 8
VI_CHARS = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I)
COHORT_NAMES = {"K71+": "Khoá 71 trở về sau (nhập học từ 2026)", "K70-": "Khoá 70 trở về trước"}


def load_cache(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def cache_key(kw: dict) -> str:
    """Khoa = moi thu quyet dinh dau ra LLM. Sua prompt / vi du / schema / ngay -> khoa doi -> cache tu vo hieu;
    sua code SAU LLM (router_check, postprocess, prefilter...) -> khoa giu -> do lai mien phi."""
    blob = json.dumps({"model": kw["model"], "temperature": kw.get("temperature"), "max_tokens": kw.get("max_tokens"),
                       "schema": kw["response_format"].model_json_schema(), "messages": kw["messages"]},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class UsageClient:
    """Boc client de dem token va thoi gian tung lan goi ma khong sua route(). Co cache theo cache_key
    (PLAN - Toi uu Router (v1), buoc B): chi luu khi LLM tra JSON hop le."""

    def __init__(self, inner, cache: dict | None = None, read_cache: bool = True):
        self.inner, self.log = inner, []
        self.cache = {} if cache is None else cache
        self.read_cache = read_cache
        self.chat = self
        self.completions = self

    async def parse(self, **kw):
        key = cache_key(kw)
        hit = self.cache.get(key) if self.read_cache else None
        if hit:
            self.log.append({**hit["usage"], "s": 0.0, "from_cache": True})
            msg = SimpleNamespace(parsed=kw["response_format"].model_validate_json(hit["content"]),
                                  content=hit["content"], refusal=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
        t = time.perf_counter()
        r = await self.inner.chat.completions.parse(**kw)
        u = r.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        usage = {"in": u.prompt_tokens, "out": u.completion_tokens, "cached": cached}
        self.log.append({**usage, "s": time.perf_counter() - t, "from_cache": False})
        if r.choices[0].message.parsed is not None:
            self.cache[key] = {"content": r.choices[0].message.content, "usage": usage}
        return r


def parse_call(spec: str) -> dict:
    """'admission_scores years=[2025]' -> {"tool": ..., "args": {...}} (cot pending_call)."""
    tool, *rest = spec.split(" ", 1)
    args = {}
    for k, v in re.findall(r"(\w+)=(\[[^\]]*\]|\S+)", rest[0] if rest else ""):
        args[k] = json.loads(v) if v.startswith("[") else v
    return {"tool": tool, "args": args}


def build_pending(r: dict, ctx: ToolContext) -> dict:
    codes = r["pending_candidates"].split(";")
    cohort = all(c in COHORT_NAMES for c in codes)
    call = parse_call(r["pending_call"])
    if not cohort:
        call["args"].setdefault("programs", [r["pending_mention"]])
    return {"calls": [{**call, "done": None}], "index": 0, "retries": 0,
            "mention": "khoá học" if cohort else r["pending_mention"],
            "field": "cohort" if cohort else "programs", "entity_type": "cohort" if cohort else "program",
            "candidates": [{"code": c, "name": COHORT_NAMES[c] if cohort else ctx.aliases.name("program", c)}
                           for c in codes]}


def guessed_codes(calls: list[dict], question: str, known: set[str], allowed: set[str]) -> list[str]:
    """Ma nganh/Truong co trong args ma nguoi dung KHONG go (Router doan ma, PLAN Router 3.3)."""
    q = compact(question)
    out = []
    for c in calls:
        a = c["args"]
        vals = [*a.get("programs", []), *a.get("faculties", []), a.get("faculty") or ""]
        for v in vals:
            k = compact(v)
            if k and k in known and k not in q and v not in allowed:
                out.append(v)
    return out


async def run_once(cases, picks, ctx, known, client, today):
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(kind, r):
        async with sem:
            c = empty_context()
            allowed: set[str] = set()
            question = r["question"] if kind == "case" else r["message"]
            if kind == "pick":
                c["pending"] = build_pending(r, ctx)
                allowed = {x["code"] for x in c["pending"]["candidates"]}
            gate = prefilter(question, c)
            if gate:                    # graph that chan o router_node, khong goi LLM (PLAN Toi uu Router A)
                return {"id": r["id"], "intent": GATE_INTENT.get(gate, "UNKNOWN"), "topic": None, "need": "",
                        "language": "en" if looks_english(question) else "vi", "scope": None, "refers": False,
                        "pick_status": "unclear" if gate == "unclear" else None, "picked": [], "missing": None,
                        "calls": [], "s": 0.0, "guess": [], "fixes": [], "gate": gate}
            t = time.perf_counter()
            try:
                out = await route(question, c, today=today, client=client, tctx=ctx)   # bo quet + kiem sau (buoc 3)
            except RouterError as e:
                return {"id": r["id"], "error": str(e)[:200], "s": time.perf_counter() - t}
            calls = calls_as_dicts(out)
            return {"id": r["id"], "intent": out.intent, "topic": out.topic, "need": out.need,
                    "language": out.language, "scope": out.scope_note,
                    "refers": out.refers_to_context, "pick_status": out.pick_status, "picked": out.picked,
                    "missing": out.missing_info, "calls": calls, "s": time.perf_counter() - t,
                    "guess": guessed_codes(calls, question, known, allowed), "fixes": out.fixes}

    jobs = [one("case", r) for r in cases] + [one("pick", r) for r in picks]
    return await asyncio.gather(*jobs)


def tools_ok(r: dict, got: dict) -> bool:
    called = {c["tool"] for c in got["calls"]}
    req = {t for t in r["required_tools"].split(";") if t}
    opt = {t for t in r["optional_tools"].split(";") if t}
    return req <= called <= req | opt


def failed_ids(prev_run: list[dict], cases, picks) -> set[str]:
    """--only-failed: ca sai intent / sai tool / loi LLM / sai pick_status o lan chay truoc (file --raw)."""
    by = {x["id"]: x for x in prev_run}
    bad = {r["id"] for r in cases
           if "error" in by.get(r["id"], {"error": ""}) or by[r["id"]].get("intent") != r["expected_intent"]
           or not tools_ok(r, by[r["id"]])}
    bad |= {r["id"] for r in picks if by.get(r["id"], {}).get("pick_status") != r["expected_pick_status"]}
    return bad


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else "—"


def score_run(cases, picks, res):
    by = {x["id"]: x for x in res}
    m = {"errors": [x for x in res if "error" in x]}
    ok = lambda r: by[r["id"]].get("intent") == r["expected_intent"]  # noqa: E731
    m["intent"] = sum(ok(r) for r in cases)
    m["intent_approved"] = (sum(ok(r) for r in cases if r["duyet"]), sum(1 for r in cases if r["duyet"]))
    en = [r for r in cases if r["language"] == "en"]
    m["intent_en"] = (sum(ok(r) for r in en), len(en))
    m["tools"] = sum("error" not in by[r["id"]] and tools_ok(r, by[r["id"]]) for r in cases)
    m["language"] = sum(by[r["id"]].get("language") == r["language"] for r in cases)
    lang_focus = [r for r in cases if r["language"] != "vi" or "chèn tiếng Anh" in r["category"]]
    m["language_focus"] = (sum(by[r["id"]].get("language") == r["language"] for r in lang_focus), len(lang_focus))
    scoped = [r for r in cases if r["scope_note"]]
    m["scope"] = (sum(by[r["id"]].get("scope") == r["scope_note"] for r in scoped), len(scoped))
    m["guess"] = [(r["id"], by[r["id"]]["guess"]) for r in cases + picks if by[r["id"]].get("guess")]
    m["fixes"] = [(r["id"], by[r["id"]]["fixes"]) for r in cases + picks if by[r["id"]].get("fixes")]
    t7_en = [(r["id"], c["args"]["query"]) for r in en for c in by[r["id"]].get("calls", [])
             if c["tool"] == "rag_search"]
    m["t7_vi"] = (sum(bool(VI_CHARS.search(q)) for _, q in t7_en), len(t7_en))
    m["t7_not_vi"] = [(i, q) for i, q in t7_en if not VI_CHARS.search(q)]
    m["pick"] = sum(by[r["id"]].get("pick_status") == r["expected_pick_status"] for r in picks)
    picked = [r for r in picks if r["expected_pick_status"] == "picked"]
    m["picked"] = (sum(set(by[r["id"]].get("picked") or []) == set(r["expected_picked"].split(";"))
                       for r in picked), len(picked))
    pick_intent = [r for r in picks if r["expected_intent"]]
    m["pick_intent"] = (sum(by[r["id"]].get("intent") == r["expected_intent"] for r in pick_intent), len(pick_intent))
    m["gated"] = sum(1 for x in res if x.get("gate"))
    return m


def fmt_call(c):
    a = {k: v for k, v in c["args"].items() if v not in ([], None, "") and not (k == "top_k" and v == 5)
         and not (k == "limit" and v == 10) and not (k == "order" and v == "desc")}
    return f"{c['tool']} {json.dumps(a, ensure_ascii=False)}"


def report(cases, picks, runs, usage, n_runs, today: date, partial: bool = False):
    lines = [f"# Đo AC3 Router — {date.today()}" + (" (MỘT PHẦN)" if partial else ""), "",
             f"Sinh bởi `scripts/eval_router.py` (PLAN - Router (v1), mục 5). Model `gpt-4o-mini`, nhiệt độ 0, "
             f"{n_runs} lần chạy, {len(cases)} ca `router_cases.csv` + {len(picks)} ca `router_pick_cases.csv`. "
             f"Ngày đưa vào prompt: {today}.", "",
             "Nhãn cả hai file đã được người dùng duyệt (cột `duyet`). Router chạy KÈM bộ quét gợi ý và kiểm sau "
             "(PLAN - Sua loi sau chay thu Synthesizer (v1), bước 3); mục 6 liệt kê mọi chỗ code đã sửa. "
             "Ca bị cổng `prefilter` chặn không gọi LLM, giống graph thật (PLAN - Toi uu Router (v1), bước A).", ""]
    if partial:
        lines += [("> **Chạy một phần (`--only-failed`)**: chỉ các ca sai ở lần trước. KHÔNG dùng làm số AC3 chính "
                   "thức: không chứng minh được ca đúng trước đó vẫn đúng."), ""]
    scores = [score_run(cases, picks, r) for r in runs]
    n = len(cases)
    lines += ["## 1. Chỉ số theo từng lần chạy", "",
              "| Chỉ số | " + " | ".join(f"Lần {i + 1}" for i in range(n_runs)) + " |",
              "|---|" + "---|" * n_runs]
    rows = [("**AC3 intent** (ngưỡng 95%)", lambda m: pct(m["intent"], n)),
            ("AC3 trên ca đã duyệt", lambda m: pct(*m["intent_approved"])),
            ("AC3 phần tiếng Anh", lambda m: pct(*m["intent_en"])),
            ("Tool đúng (required ⊆ gọi ⊆ required ∪ optional)", lambda m: pct(m["tools"], n)),
            ("Ngôn ngữ (cả bộ)", lambda m: pct(m["language"], n)),
            ("Ngôn ngữ trên ca en / other / Việt chèn Anh", lambda m: pct(*m["language_focus"])),
            ("`scope_note` trên ca có nhãn", lambda m: pct(*m["scope"])),
            ("**Đoán mã** (ngưỡng 0, sau kiểm sau Router)", lambda m: str(len(m["guess"]))),
            ("Router điền chữ không có trong câu → code sửa (bước 3b; số ca)", lambda m: str(len(m["fixes"]))),
            ("`query` T7 tiếng Việt ở câu tiếng Anh", lambda m: pct(*m["t7_vi"])),
            ("`pick_status` đúng", lambda m: pct(m["pick"], len(picks))),
            ("`picked` đúng (ca picked)", lambda m: pct(*m["picked"])),
            ("Intent ở ca đang chờ chọn", lambda m: pct(*m["pick_intent"])),
            ("Ca do cổng `prefilter` xử lý (không gọi LLM)", lambda m: str(m["gated"])),
            ("Lỗi gọi LLM", lambda m: str(len(m["errors"])))]
    for name, f in rows:
        lines.append(f"| {name} | " + " | ".join(f(m) for m in scores) + " |")

    # Chi phi / do tre chi tinh lan goi THAT; lan lay tu cache (eval_router.json) khong ton tien
    real = [u for u in usage if not u.get("from_cache")]
    lines += ["", "## 2. Độ trễ và token (lần gọi thật)", "",
              (f"- Lần gọi OpenAI thật: **{len(real)}**; lấy từ cache: {len(usage) - len(real)} "
               "(chi phí chỉ tính lần gọi thật).")]
    if real:
        lat = sorted(u["s"] for u in real)
        p95 = lat[max(0, -(-95 * len(lat) // 100) - 1)]      # phan vi tri gan nhat, khong ngoai suy khi it mau
        tin = [u["in"] for u in real]
        cached = sum(u["cached"] for u in real)
        out_tok = sum(u["out"] for u in real)
        lines += [f"- Thời gian một lần gọi Router: P50 **{statistics.median(lat):.2f} s**, "
                  f"P95 **{p95:.2f} s**, max {max(lat):.2f} s ({len(lat)} lần gọi, "
                  f"{CONCURRENCY} lần song song).",
                  f"- Token vào trung bình {statistics.mean(tin):.0f}, ra trung bình "
                  f"{out_tok / len(real):.0f}; phần vào được cache: {100 * cached / sum(tin):.0f}%.",
                  f"- Ước tính chi phí đợt đo (giá gpt-4o-mini 0,15 USD/1M vào, 0,075 USD/1M vào đã cache, "
                  f"0,60 USD/1M ra): **{(0.15 * (sum(tin) - cached) + 0.075 * cached + 0.6 * out_tok) / 1e6:.3f} USD**."]

    # do on dinh
    by_run = [{x["id"]: x for x in r} for r in runs]
    flips = [r for r in cases + picks if len({b[r["id"]].get("intent") for b in by_run}) > 1]
    lines += ["", "## 3. Độ ổn định giữa các lần", "",
              f"{len(flips)} ca đổi intent giữa các lần chạy" + (":" if flips else ".")]
    for r in flips:
        q = r.get("question") or r.get("message")
        lines.append(f"- {r['id']} \"{q}\": " + " / ".join(b[r['id']].get('intent', 'LỖI') for b in by_run))

    # ca sai (lan 1)
    first = by_run[0]
    lines += ["", "## 4. Ca sai intent (lần 1), theo nhóm", ""]
    wrong = defaultdict(list)
    for r in cases:
        g = first[r["id"]]
        if g.get("intent") != r["expected_intent"]:
            wrong[r["category"]].append((r, g))
    if not wrong:
        lines.append("Không có.")
    for cat, items in sorted(wrong.items(), key=lambda kv: -len(kv[1])):
        lines += [f"### {cat} ({len(items)})", "", "| Ca | Câu hỏi | Nhãn | Router | Lệnh gọi |", "|---|---|---|---|---|"]
        for r, g in items:
            calls = "<br>".join(fmt_call(c) for c in g.get("calls", [])) or "—"
            lines.append(f"| {r['id']} | {r['question']} | {r['expected_intent']} | {g.get('intent', 'LỖI')} | {calls} |")
        lines.append("")

    lines += ["## 5. Ca sai tool (lần 1, intent đúng)", "", "| Ca | Câu hỏi | Cần / tuỳ chọn | Router gọi |", "|---|---|---|---|"]
    for r in cases:
        g = first[r["id"]]
        if g.get("intent") == r["expected_intent"] and "error" not in g and not tools_ok(r, g):
            calls = "<br>".join(fmt_call(c) for c in g["calls"]) or "—"
            lines.append(f"| {r['id']} | {r['question']} | {r['required_tools'] or '—'} / {r['optional_tools'] or '—'} | {calls} |")

    lines += ["", "## 6. Ngôn ngữ, đoán mã, kiểm sau Router, query T7 (lần 1)", ""]
    for r in cases:
        g = first[r["id"]]
        if g.get("language") != r["language"]:
            lines.append(f"- Ngôn ngữ sai {r['id']} \"{r['question']}\": nhãn {r['language']}, Router {g.get('language')}")
    for i, gs in scores[0]["guess"]:
        lines.append(f"- Đoán mã {i}: {gs}")
    for i, fx in scores[0]["fixes"]:
        lines.append(f"- Kiểm sau Router sửa {i}: " + "; ".join(fx))
    for i, q in scores[0]["t7_not_vi"]:
        lines.append(f"- `query` T7 không phải tiếng Việt {i}: {q}")

    lines += ["", "## 7. Ca đang chờ chọn (lần 1)", "",
              "| Ca | Tin nhắn | Nhãn | Router | picked | intent | Lệnh gọi |", "|---|---|---|---|---|---|---|"]
    for r in picks:
        g = first[r["id"]]
        mark = "" if g.get("pick_status") == r["expected_pick_status"] else " ❌"
        calls = "<br>".join(fmt_call(c) for c in g.get("calls", [])) or "—"
        lines.append(f"| {r['id']} | {r['message']} | {r['expected_pick_status']} {r['expected_picked']} | "
                     f"{g.get('pick_status')}{mark} | {', '.join(g.get('picked') or [])} | {g.get('intent')} | {calls} |")
    return "\n".join(lines) + "\n", scores


async def main_async(args):
    ctx = ToolContext.from_tables(build_db.build_rows())
    known = {compact(c) for c in ctx.program_group} | {compact(r["faculty_code"])
                                                       for r in build_db.build_rows()["faculties"]}
    cases = list(csv.DictReader(open(EVAL / "router_cases.csv", encoding="utf-8-sig")))[: args.limit]
    picks = list(csv.DictReader(open(EVAL / "router_pick_cases.csv", encoding="utf-8")))[: args.limit]
    if args.only_failed:
        bad = failed_ids(json.loads(Path(args.only_failed).read_text(encoding="utf-8"))[0], cases, picks)
        cases, picks = [r for r in cases if r["id"] in bad], [r for r in picks if r["id"] in bad]
        print(f"--only-failed: {len(cases)} ca + {len(picks)} ca chờ chọn")
    today = date.fromisoformat(args.today) if args.today else date.today()
    cache = load_cache(CACHE)
    client = UsageClient(get_llm(), cache, read_cache=not args.no_cache)
    runs = []
    try:
        for i in range(args.runs):
            t = time.perf_counter()
            runs.append(await run_once(cases, picks, ctx, known, client, today))
            print(f"lần {i + 1}: {time.perf_counter() - t:.0f} s")
    finally:                                         # hong giua chung van giu cac lan goi da tra tien
        save_cache(CACHE, cache)
    real = sum(1 for u in client.log if not u["from_cache"])
    print(f"gọi OpenAI thật: {real}, lấy từ cache: {len(client.log) - real}")
    text, scores = report(cases, picks, runs, client.log, args.runs, today, partial=bool(args.only_failed))
    out_path = OUT_PARTIAL if args.only_failed else OUT
    out_path.write_text(text, encoding="utf-8")
    if args.raw:
        Path(args.raw).write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    for i, m in enumerate(scores):
        print(f"lần {i + 1}: AC3 {pct(m['intent'], len(cases))} | tool {pct(m['tools'], len(cases))} | "
              f"pick {pct(m['pick'], len(picks))} | đoán mã {len(m['guess'])} | lỗi {len(m['errors'])}")
    print("->", out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)       # nguoi dung chot 2026-10-18: 3 lan qua ton tien
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N ca đầu mỗi file (thử nhanh)")
    ap.add_argument("--raw", default=None, help="ghi đầu ra thô (JSON) của mọi lần chạy ra file này")
    ap.add_argument("--no-cache", action="store_true", help="không đọc cache, gọi OpenAI thật (vẫn ghi cache mới)")
    ap.add_argument("--only-failed", default=None, metavar="RAW",
                    help="chỉ chạy lại ca sai trong file --raw của lần trước (thử nhanh, không phải số AC3 chính thức)")
    ap.add_argument("--today", default=None, metavar="YYYY-MM-DD",
                    help="ngày đưa vào prompt (mặc định hôm nay); giữ cố định để dùng lại cache qua nhiều ngày")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
