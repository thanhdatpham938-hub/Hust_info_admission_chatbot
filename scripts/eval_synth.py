"""Do Synthesizer: chay CA graph voi Router that, tool that, Synthesizer that (PLAN - Synthesizer (v1), muc 9; S5).

Ton phi THAT (goi OpenAI): ~0,05-0,09 USD cho 30 cau. BAO TRUOC va HOI nguoi dung truoc khi chay.
Can: docker compose up -d (Postgres + Qdrant), OPENAI_API_KEY trong .env.

Dung: python scripts/eval_synth.py [--limit N]
      -> docs/ghi_chu/<ngay> - Do Synthesizer.md : chi so + tung cau tra loi de nguoi dung cham (dung / sai / thieu)
"""

import argparse
import asyncio
import csv
import json
import statistics
import sys
import time
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from app.core.llm import get_llm  # noqa: E402
from app.db.pool import close_pool, open_pool  # noqa: E402
from app.graph.build import build_graph, chat  # noqa: E402
from app.graph.guardrails.numbers import strange_numbers  # noqa: E402
from app.graph.nodes import GraphDeps  # noqa: E402
from app.graph.router import route  # noqa: E402
from app.graph.synthesizer import generate  # noqa: E402
from app.tools.context import ToolContext  # noqa: E402

CASES = ROOT / "backend" / "tests" / "eval" / "synth_cases.csv"
OUT = ROOT / "docs" / "ghi_chu" / f"{date.today()} - Do Synthesizer.md"
CONCURRENCY = 4
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.15, 0.075, 0.60          # USD / 1M token, gpt-4o-mini


class Usage:
    """Boc client OpenAI: dem token cua Router (parse) va Synthesizer (create)."""

    def __init__(self, inner):
        self.inner, self.log = inner, []
        self.chat = self
        self.completions = self

    def _rec(self, kind, r):
        u = r.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        self.log.append({"kind": kind, "in": u.prompt_tokens, "out": u.completion_tokens, "cached": cached})

    async def parse(self, **kw):
        r = await self.inner.chat.completions.parse(**kw)
        self._rec("router", r)
        return r

    async def create(self, **kw):
        r = await self.inner.chat.completions.create(**kw)
        self._rec("synth", r)
        return r


def cost(log) -> float:
    tin = sum(x["in"] for x in log)
    cached = sum(x["cached"] for x in log)
    return (PRICE_IN * (tin - cached) + PRICE_CACHED * cached + PRICE_OUT * sum(x["out"] for x in log)) / 1e6


async def run(limit: int | None):
    await open_pool()
    try:
        ctx = await ToolContext.load()
        client = Usage(get_llm())

        async def router(q, c, history, today, **kw):          # kw: tctx (bo quet + kiem sau Router, buoc 3)
            return await route(q, c, history, today, client=client, **kw)

        async def synth(payload, issues, on_token=None):         # do chat luong: khong stream (Usage can r.usage)
            return await generate(payload, issues, client=client)

        async def tool_ctx():
            return ctx

        graph = build_graph(GraphDeps(route=router, tool_ctx=tool_ctx, program_group=ctx.program_group,
                                      program_names=ctx.program_names, synthesize=synth))
        cases = list(csv.DictReader(CASES.open(encoding="utf-8-sig")))[:limit]
        sem = asyncio.Semaphore(CONCURRENCY)

        async def one(case):
            async with sem:
                t = time.perf_counter()
                try:
                    r = await chat(graph, str(uuid.uuid4()), case["question"])
                except Exception as e:                       # noqa: BLE001 — ghi lai, khong dung ca dot do
                    return {**case, "error": f"{type(e).__name__}: {e}", "s": time.perf_counter() - t}
                turn = r["_state"]["turn"]
                ev = turn.get("evidence") or {}
                final_text = (turn.get("draft_text") or "") if not r["metadata"]["used_template"] else ""
                strange = strange_numbers(final_text, set(ev.get("allowed") or [])) if final_text and ev else []
                return {**case, "s": time.perf_counter() - t, "answer": r["answer"], "meta": r["metadata"],
                        "citations": r["citations"], "calls": turn.get("calls") or [],
                        "statuses": [x.get("status") for x in turn.get("results") or []],
                        "verify_log": turn.get("verify_log") or [], "strange": strange,
                        "fixes": (turn.get("router") or {}).get("fixes") or [],
                        "rag_used": ev.get("rag_used", False), "tuition_used": ev.get("tuition_used", False)}

        t0 = time.perf_counter()
        res = await asyncio.gather(*(one(c) for c in cases))
        return res, client.log, time.perf_counter() - t0
    finally:
        await close_pool()


def fmt_call(c):
    a = {k: v for k, v in c["args"].items() if v not in ([], None, "") and not (k == "top_k" and v == 5)
         and not (k == "limit" and v == 10) and not (k == "order" and v == "desc")}
    return f"`{c['tool']} {json.dumps(a, ensure_ascii=False)}`"


def report(res, log, wall) -> str:
    ok = [r for r in res if "error" not in r]
    answered = [r for r in ok if r["meta"]["intent"] not in ("CLARIFICATION_NEEDED",) and not r["meta"]["fallback_reason"]]
    rag = [r for r in answered if r["rag_used"]]
    rag_cited = [r for r in rag if any(c.get("location") for c in r["citations"])]
    tuition = [r for r in answered if r["tuition_used"]]
    rewrites = [r["meta"]["rewrites"] for r in answered]
    times = sorted(r["s"] for r in ok)
    p95 = times[max(0, -(-95 * len(times) // 100) - 1)] if times else 0
    synth_calls = sum(1 for x in log if x["kind"] == "synth")
    lines = [f"# Đo Synthesizer — {date.today()}", "",
             f"Sinh bởi `scripts/eval_synth.py` (PLAN - Synthesizer (v1), mục 9). Graph thật: Router thật + 7 tool thật "
             f"(Postgres, Qdrant) + Synthesizer thật (gpt-4o-mini). {len(res)} câu từ `synth_cases.csv`, chạy **1 lần**.",
             "", "## 1. Chỉ số", "", "| Chỉ số | Kết quả |", "|---|---|",
             f"| Câu chạy xong / lỗi | {len(ok)} / {len(res) - len(ok)} |",
             f"| Câu có câu trả lời từ Synthesizer (không phải hỏi lại / từ chối / không có dữ liệu) | {len(answered)} |",
             f"| **Số lạ còn trong câu trả lời cuối** (AC5, ngưỡng 0) | {sum(len(r['strange']) for r in ok)} |",
             f"| **Câu dùng văn bản có trích dẫn đủ vị trí** (AC4, ngưỡng 100%) | {len(rag_cited)}/{len(rag)} |",
             f"| Câu có học phí | {len(tuition)} |",
             f"| Viết đạt ngay lần đầu | {sum(1 for x in rewrites if x == 0)}/{len(answered)} |",
             f"| Phải viết lại 1 / 2 lần | {sum(1 for x in rewrites if x == 1)} / {sum(1 for x in rewrites if x == 2)} |",
             f"| Phải dùng bản dựng từ dữ liệu (sai 3 lần hoặc lỗi OpenAI) | {sum(1 for r in answered if r['meta']['used_template'])} |",
             f"| Thời gian một câu (cả graph) | P50 {statistics.median(times):.1f} s, P95 {p95:.1f} s, max {max(times):.1f} s |",
             f"| Lần gọi LLM: Router / Synthesizer | {sum(1 for x in log if x['kind'] == 'router')} / {synth_calls} |",
             f"| Token Synthesizer vào / ra trung bình | "
             f"{statistics.mean([x['in'] for x in log if x['kind'] == 'synth'] or [0]):.0f} / "
             f"{statistics.mean([x['out'] for x in log if x['kind'] == 'synth'] or [0]):.0f} |",
             f"| **Chi phí ước tính đợt đo** (chưa tính embedding T7, không đáng kể) | **{cost(log):.3f} USD** |",
             f"| Tổng thời gian chạy | {wall:.0f} s ({CONCURRENCY} câu song song) |",
             "", "Thời gian một câu đo khi chạy song song nên cao hơn khi chạy một mình; chưa phải thời gian đến chữ đầu "
             "tiên (chưa có stream).",
             "", "## 2. Từng câu trả lời — anh chấm cột \"Chấm\" (Đúng / Sai / Thiếu + ghi chú)", ""]
    for r in res:
        lines += [f"### {r['id']} · {r['group']} · {r['source']}", "", f"**Câu hỏi:** {r['question']}", ""]
        if "error" in r:
            lines += [f"**LỖI:** {r['error']}", ""]
            continue
        m = r["meta"]
        status = "bản dựng từ dữ liệu" if m["used_template"] else (f"viết lại {m['rewrites']} lần" if m["rewrites"] else "đạt ngay")
        lines += [f"- Intent: `{m['intent']}` · ngôn ngữ `{m['language']}` · "
                  + (f"nhánh `{m['fallback_reason']}`" if m["fallback_reason"] else f"Synthesizer: {status}")
                  + f" · {r['s']:.1f} s",
                  "- Tool: " + (", ".join(f"{fmt_call(c)} → {s}" for c, s in zip(r["calls"], r["statuses"])) or "—")]
        if r["fixes"]:
            lines.append("- Kiểm sau Router đã sửa: " + "; ".join(r["fixes"]))
        issues = [i for step in r["verify_log"] for i in step]
        if issues:
            lines.append("- Lỗi `verify` bắt được trước khi gửi: " + " | ".join(issues))
        if r["strange"]:
            lines.append(f"- ⚠️ Số lạ còn lại: {r['strange']}")
        lines += ["", "**Câu trả lời:**", "", "> " + r["answer"].replace("\n", "\n> "), "",
                  "**Chấm:** ☐ Đúng ☐ Sai ☐ Thiếu — ghi chú: ", "", "---", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    runner = asyncio.run(run(args.limit), loop_factory=asyncio.SelectorEventLoop) if sys.platform == "win32" \
        else asyncio.run(run(args.limit))
    res, log, wall = runner
    OUT.write_text(report(res, log, wall), encoding="utf-8")
    print(f"{len(res)} câu, chi phí ước tính {cost(log):.3f} USD -> {OUT}")


if __name__ == "__main__":
    main()
