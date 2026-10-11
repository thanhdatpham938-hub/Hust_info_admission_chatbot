"""Do retrieval tren bo 120 cau bang RETRIEVER CUA BACKEND (PLAN - T7 retrieval (v2), buoc 3, ca R-14).

Moi cau goi embedding MOT lan, roi chay ca hai cach tren cung vector:
  cu   dense thuan top-5 (nhu scripts/search_chunks.py --eval — moc so sanh)
  moi  backend/app/rag/retriever.py (nhanh moi ban + ban moi nhat + cum tu, gop RRF)
Muc tai lieu: trung neu top-5 co it nhat 1 chunk thuoc tai lieu ghi o cot "Tai lieu tham chieu".
Ghi them phan bo top_dense_score (cosine top-1) de lam can cu nguong "khong du tin cay" (R6).

Dung: python scripts/eval_retrieval.py      -> docs/ghi_chu/<ngay> - Ket qua retrieval T7.md
"""

import asyncio
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
import search_chunks as sc  # noqa: E402  (doc bo 120 cau, map chunk -> tai lieu; dung chung voi moc cu)
from app.rag.retriever import Retriever, SearchSpec  # noqa: E402
from app.tools.rag_tool import LOW_CONFIDENCE  # noqa: E402

OUT = ROOT / "docs" / "ghi_chu" / f"{date.today()} - Ket qua retrieval T7.md"
OFF_TOPIC = ["Hôm nay thời tiết Hà Nội thế nào?", "Công thức nấu phở bò ngon?", "Giá vàng hôm nay bao nhiêu?",
             "Điểm chuẩn Đại học Quốc gia Hà Nội năm 2025 là bao nhiêu?", "Học phí Đại học Kinh tế Quốc dân?"]


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "—"


def spread(xs: list[float]) -> str:
    if not xs:
        return "—"
    xs = sorted(xs)
    return f"min {xs[0]:.3f} · trung vị {statistics.median(xs):.3f} · max {xs[-1]:.3f}"


async def main() -> int:
    r = Retriever()
    rows = sc.parse_eval_rows()
    known_missing = sc.parse_missing_data_qids()
    results = []
    for row in rows:
        vec = await r.embed(row["question"])
        old = (await r.client.query_points(r.collection, query=vec, using="dense", limit=5)).points
        new = await r.search(SearchSpec(query=row["question"]), vec)
        old_src = [sc.source_of(p.payload["chunk_id"]) for p in old]
        new_src = [sc.source_of(h.payload["chunk_id"]) for h in new.hits]
        results.append({**row, "old": any(s in row["refs"] for s in old_src), "new": any(s in row["refs"] for s in new_src),
                        "top": new.top_dense_score, "known_missing": row["qid"] in known_missing,
                        "new_top1": new_src[0] if new_src else "", "phrases": [p.shown for p in new.phrases]})
    off = []
    for q in OFF_TOPIC:
        off.append((q, (await r.search(SearchSpec(query=q))).top_dense_score))
    await r.close()

    clean = [x for x in results if not x["known_missing"]]
    n = len(clean)
    gained = [x for x in clean if x["new"] and not x["old"]]
    lost = [x for x in clean if x["old"] and not x["new"]]
    still = [x for x in clean if not x["new"]]
    low = [x for x in results if x["top"] < LOW_CONFIDENCE]
    lines = [f"# Kết quả retrieval T7 — {date.today()}", "",
             "Sinh bởi `scripts/eval_retrieval.py`. Mức **tài liệu**, top-5, cùng một vector câu hỏi cho cả hai cách. "
             "Cột tham chiếu đã sửa 2026-10-11 (Q10, Q12, Q20 thêm `trang_tuyen_sinh`; Q18 thêm "
             "`qui-dinh-ve-xttn-nam-2026-ky`). Câu chưa gắn ngành/Trường (Router chưa có) nên T7 chạy nhánh chung.", "",
             "| Cách | Toàn bộ " + str(len(results)) + " câu | Bỏ câu đã biết thiếu dữ liệu (" + str(n) + ") |", "|---|--:|--:|",
             f"| Cũ — dense thuần | {pct(sum(x['old'] for x in results), len(results))} | {pct(sum(x['old'] for x in clean), n)} |",
             f"| **Mới — retriever T7** | {pct(sum(x['new'] for x in results), len(results))} | **{pct(sum(x['new'] for x in clean), n)}** |",
             "", f"- Câu chuyển sang trúng: {', '.join(x['qid'] for x in gained) or '—'}",
             f"- Câu chuyển sang trượt: {', '.join(x['qid'] for x in lost) or '—'}", "",
             "## Phân bố `top_dense_score` (cosine top-1) — căn cứ ngưỡng R6", "",
             f"- Câu có tham chiếu RAG, trúng: {spread([x['top'] for x in results if x['new']])}",
             f"- Câu có tham chiếu RAG, trượt: {spread([x['top'] for x in results if not x['new']])}",
             f"- Câu ngoài phạm vi (tự đặt): {spread([s for _, s in off])}",
             f"- Câu có tham chiếu RAG dưới ngưỡng {LOW_CONFIDENCE}: {', '.join(x['qid'] for x in low) or 'không có'}", "",
             "| Câu ngoài phạm vi | top_dense_score | Dưới ngưỡng? |", "|---|--:|---|"]
    lines += [f"| {q} | {s:.3f} | {'có' if s < LOW_CONFIDENCE else '**không** — Router phải chặn'} |" for q, s in off]
    lines += ["", "## Câu vẫn trượt (không tính câu đã biết thiếu dữ liệu)", "",
              "| ID | Câu hỏi | Nguồn kỳ vọng | Top-1 mới | Cụm từ dùng |", "|---|---|---|---|---|"]
    lines += [f"| {x['qid']} | {x['question'][:90]} | {', '.join(sorted(x['refs']))} | {x['new_top1']} | "
              f"{', '.join(x['phrases']) or '—'} |" for x in still]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cũ {pct(sum(x['old'] for x in clean), n)} -> mới {pct(sum(x['new'] for x in clean), n)} | "
          f"trúng thêm {[x['qid'] for x in gained]} | trượt thêm {[x['qid'] for x in lost]}")
    print(f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop) if sys.platform == "win32"
             else asyncio.run(main()))
