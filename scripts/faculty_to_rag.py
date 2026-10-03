"""Chunk phan gioi thieu 10 Truong/Khoa thanh nguon RAG.

Day la van ban gioi thieu/truyen thong, KHONG phai van ban phap quy:
  - document_type rieng ("gioi_thieu_truong") de retrieval phan biet do tin cay
  - citation chi co ten trang + URL, khong co Dieu/trang nhu van ban quy che
Cac field co cau truc (dia chi, lien he, official_channel_url) van nam o
info.json -> PostgreSQL, dung theo PRD muc 3.D. Chunk la bo sung, khong thay the.
"""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACULTY = ROOT / "data" / "faculty"
OUT = ROOT / "data" / "rag" / "raw_chunks"

TARGET = 1200   # ky tu moi chunk
MIN_CHUNK = 200


def chunk_text(paras: list[str]) -> list[str]:
    """Gom doan van lien tiep cho toi khi dat ~TARGET ky tu, khong cat giua doan."""
    chunks, buf = [], []
    for para in paras:
        buf.append(para)
        if sum(len(p) for p in buf) >= TARGET:
            chunks.append("\n\n".join(buf))
            buf = []
    if buf:
        tail = "\n\n".join(buf)
        if chunks and len(tail) < MIN_CHUNK:
            chunks[-1] += "\n\n" + tail
        else:
            chunks.append(tail)
    return chunks


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    all_chunks = []

    for md in sorted(FACULTY.glob("*/gioi_thieu.md")):
        code = md.parent.name
        info = json.loads((md.parent / "info.json").read_text(encoding="utf-8"))
        # Trang goc co doan chu dang to hop (NFD) -> chuan hoa NFC de khop voi cau hoi go thuong
        lines = unicodedata.normalize("NFC", md.read_text(encoding="utf-8")).splitlines()

        title = lines[0].lstrip("# ").strip() if lines else code.upper()
        source_url = info.get("sources", {}).get("gioi_thieu", "")
        body = [l.strip() for l in lines[1:] if l.strip() and not l.startswith(">")]

        for i, text in enumerate(chunk_text(body), start=1):
            all_chunks.append({
                "document_title": title,
                "document_no": "",
                "document_type": "gioi_thieu_truong",
                "faculty_code": info.get("faculty_code", code.upper()),
                "year": "",
                "source_url": source_url,
                "chuong": "", "dieu_no": "", "khoan_no": "",
                "heading": f"{title} (phần {i})",
                "page_no": "",
                "text": text,
            })
        print(f"  {code:6s} {len(chunk_text(body)):3d} chunk")

    path = OUT / "gioi_thieu_truong_khoa.chunks.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n{path.name}: {len(all_chunks)} chunk")
