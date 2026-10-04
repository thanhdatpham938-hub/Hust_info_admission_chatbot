"""Tim thu va do chat luong retrieval tren collection Qdrant da nhung (embed_chunks.py).

Thuc hien PLAN - Embedding (v1), muc 7. Dung lai cach doc .env nhu check_setup.py va
cach dung chuoi embed / vector "dense" nhu embed_chunks.py (import truc tiep).

Dung:
    python scripts/search_chunks.py "điều kiện cảnh báo học tập"
    python scripts/search_chunks.py "học phí IT1" --program IT1
    python scripts/search_chunks.py "mã tổ hợp K01" --text-filter K01
    python scripts/search_chunks.py --eval
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parent.parent
NORMALIZED = ROOT / "data" / "rag" / "normalized"

EVAL_FILE = ROOT / "backend" / "tests" / "eval" / "120_question_check_data.md"
NOTE_FILE = ROOT / "docs" / "ghi_chu" / "2026-09-26 - Kiem tra 120 cau hoi.md"
GHI_CHU_DIR = ROOT / "docs" / "ghi_chu"
EXT_RE = re.compile(r"\.(pdf|csv|jsonl|html?)$", re.IGNORECASE)


def build_slug_to_source() -> dict[str, str]:
    """<slug-cua-chunk_id> -> <ten file nguon goc> (vd 'dean2026' -> 'de_an_tuyen_sinh_2026'),
    doc truc tiep tu data/rag/normalized/ (moi file = 1 nguon, dung ten nguon do) - KHONG import
    normalize_chunks.py vi module do keo theo pymupdf, khong co trong image 'ingest' nhe
    (xem PLAN - Embedding (v1) muc 10: scripts/requirements-ingest.txt chi 3 thu vien)."""
    out = {}
    for f in NORMALIZED.glob("*.chunks.jsonl"):
        name = f.name.removesuffix(".chunks.jsonl")
        first = json.loads(f.open(encoding="utf-8").readline())
        out[first["chunk_id"].split("::", 1)[0]] = name
    return out


SLUG_TO_SOURCE = build_slug_to_source()


def env():
    load_dotenv(ROOT / ".env")
    return (os.getenv("QDRANT_URL", "http://localhost:6333"),
            os.getenv("QDRANT_COLLECTION", "hust_rag_2026_1"),
            os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
            os.getenv("OPENAI_API_KEY", "").strip())


def source_of(chunk_id: str) -> str:
    """chunk_id 'dean2026::m1.2' -> ten file nguon 'de_an_tuyen_sinh_2026' (nhu trong SOURCES /
    nhu cach bo 120 cau hoi ghi o cot 'File:')."""
    slug = chunk_id.split("::", 1)[0]
    return SLUG_TO_SOURCE.get(slug, slug)


def build_filter(args) -> models.Filter | None:
    must = []
    if args.program:
        must.append(models.FieldCondition(key="program_code", match=models.MatchValue(value=args.program)))
    if args.year:
        must.append(models.FieldCondition(key="year", match=models.MatchValue(value=args.year)))
    if args.cohort:
        must.append(models.FieldCondition(key="cohort", match=models.MatchValue(value=args.cohort)))
    if args.text_filter:
        must.append(models.FieldCondition(key="text", match=models.MatchText(text=args.text_filter)))
    return models.Filter(must=must) if must else None


def search(client, oa, model, collection, query, flt=None, top=5):
    vec = oa.embeddings.create(model=model, input=query).data[0].embedding
    return client.query_points(collection, query=vec, using="dense", query_filter=flt, limit=top).points


def cmd_search(args):
    url, collection, model, key = env()
    if not key:
        sys.exit("OPENAI_API_KEY trống trong .env — xem scripts/check_setup.py")
    client = QdrantClient(url=url, timeout=10)
    oa = OpenAI(api_key=key)
    flt = build_filter(args)
    hits = search(client, oa, model, collection, args.query, flt, args.top)
    if not hits:
        print("Không có kết quả (kiểm tra lại bộ lọc).")
        return
    for i, h in enumerate(hits, 1):
        p = h.payload
        print(f"{i}. [{h.score:.4f}] {p['chunk_id']:28s} {p['document_title']} ({p['year']}) — {p['heading']}")


# --------------------------------------------------------------------------- eval ------------
def parse_eval_rows() -> list[dict]:
    rows = []
    for line in EVAL_FILE.open(encoding="utf-8"):
        if not line.startswith("| **Q"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        qid = cells[0].strip("* ")
        question, ref = cells[2], cells[4]
        refs = {EXT_RE.sub("", m) for m in re.findall(r"`([^`]+)`", ref)}
        rag_refs = refs & set(SLUG_TO_SOURCE.values())
        if rag_refs:
            rows.append(dict(qid=qid, question=question, refs=rag_refs))
    return rows


def parse_missing_data_qids() -> set[str]:
    """Doc ghi chu 2026-09-26: cau nao da xac nhan nguon KHONG co thong tin (⛔) — de tach
    rieng khoi loi retrieval that khi doc bao cao (PLAN muc 7)."""
    if not NOTE_FILE.exists():
        return set()
    out = set()
    for line in NOTE_FILE.open(encoding="utf-8"):
        m = re.match(r"\|\s*(Q\d+)\s*\|[^|]*\|\s*⛔", line)
        if m:
            out.add(m.group(1))
    return out


def cmd_eval(args):
    url, collection, model, key = env()
    if not key:
        sys.exit("OPENAI_API_KEY trống trong .env — xem scripts/check_setup.py")
    client = QdrantClient(url=url, timeout=10)
    oa = OpenAI(api_key=key)

    rows = parse_eval_rows()
    missing = parse_missing_data_qids()
    print(f"{len(rows)} câu có tham chiếu RAG (/{sum(1 for _ in EVAL_FILE.open(encoding='utf-8') if _.startswith('| **Q'))} câu tổng)")

    results = []
    for r in rows:
        hits = search(client, oa, model, collection, r["question"], top=5)
        got_sources = [source_of(h.payload["chunk_id"]) for h in hits]
        hit = any(s in r["refs"] for s in got_sources)
        results.append(dict(**r, hit=hit, top1=got_sources[0] if got_sources else "",
                             known_missing=r["qid"] in missing))

    n = len(results)
    n_hit = sum(r["hit"] for r in results)
    clean = [r for r in results if not r["known_missing"]]
    n_clean_hit = sum(r["hit"] for r in clean)
    print(f"\nHit@5 (đúng tài liệu nguồn trong top-5): {n_hit}/{n} ({100*n_hit/n:.0f}%)")
    print(f"  Bỏ {n - len(clean)} câu đã biết thiếu dữ liệu nguồn (⛔, ghi chú 2026-09-26): "
          f"{n_clean_hit}/{len(clean)} ({100*n_clean_hit/len(clean):.0f}%)")

    misses = [r for r in results if not r["hit"] and not r["known_missing"]]
    print(f"\n{len(misses)} câu trượt (không phải do thiếu dữ liệu đã biết):")
    for r in misses:
        print(f"  {r['qid']}: kỳ vọng {sorted(r['refs'])} — top-1 trả về {r['top1']!r}")

    out = GHI_CHU_DIR / f"{date.today()} - Ket qua retrieval.md"
    lines = [
        f"# Kết quả retrieval — {date.today()} (dense, text-embedding-3-large, top-5)",
        "",
        f"Đo mức tài liệu (chưa có `chunk_id` mong đợi trong bộ 120 câu — xem PLAN - Embedding (v1) mục 7).",
        f"Đáp án mong đợi trong bộ 120 câu KHÔNG dùng để chấm — chỉ so cột \"Tài liệu tham chiếu\".",
        "",
        f"| | Số câu | Hit@5 |",
        f"|---|--:|--:|",
        f"| Toàn bộ {n} câu có tham chiếu RAG | {n} | {n_hit} ({100*n_hit/n:.0f}%) |",
        f"| Bỏ câu đã biết thiếu dữ liệu nguồn (⛔) | {len(clean)} | {n_clean_hit} ({100*n_clean_hit/len(clean):.0f}%) |",
        "",
        "## Câu trượt (không phải do thiếu dữ liệu đã biết)",
        "",
        "| ID | Câu hỏi | Nguồn kỳ vọng | Top-1 trả về |",
        "|---|---|---|---|",
    ]
    for r in misses:
        lines.append(f"| {r['qid']} | {r['question']} | {', '.join(sorted(r['refs']))} | {r['top1']} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nĐã ghi {out.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="?", help="câu hỏi cần tìm thử")
    ap.add_argument("--program", help="lọc program_code")
    ap.add_argument("--year", type=int, help="lọc year")
    ap.add_argument("--cohort", help="lọc cohort (K71+ / <=K70)")
    ap.add_argument("--text-filter", help="lọc payload text chứa đúng chuỗi (MatchText)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--eval", action="store_true", help="đo hit@5 trên bộ 120 câu hỏi")
    args = ap.parse_args()
    if args.eval:
        cmd_eval(args)
    elif args.query:
        cmd_search(args)
    else:
        ap.error("cần 1 câu hỏi hoặc --eval")


if __name__ == "__main__":
    main()
