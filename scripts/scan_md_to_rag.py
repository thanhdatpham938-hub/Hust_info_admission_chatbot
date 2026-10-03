"""Chunk ban transcript (doc bang vision tu PDF scan) -> nguon RAG.

Dung cho cac van ban chi co ban scan, phai doc tay tung trang:
  data/raw/<slug>/transcript/*.md  ->  data/rag/raw_chunks/<slug>.chunks.jsonl

Chunk theo Dieu giong pdf_to_rag_md.py, nhung nguon la Markdown da go lai
nen khong can loc muc luc/bang.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rag" / "raw_chunks"

DOCS = {
    "tsa_quyche": {
        "document_title": "Quy chế thi Đánh giá tư duy (TSA)",
        "document_no": "10461/QĐ-ĐHBK",
        "document_type": "quy_che_thi_tsa",
        "year": 2024,
        "source_url": "https://drive.google.com/file/d/1SJ1VnlXIXQHshZvqmu6KC6iN66l_RCxA/view",
        "verification_status": "vision_extracted",
    },
    "kkht_2022": {
        "document_title": "Quy định xét cấp học bổng khuyến khích học tập",
        "document_no": "3258/QĐ-ĐHBK-CTSV",
        "document_type": "quy_dinh_hoc_bong_kkht",
        "year": 2022,
        "source_url": "https://ctt.hust.edu.vn/Upload/Nguyen%20Viet%20Tien/files/Quy%20%C4%91%E1%BB%8Bnh%20HB%20KKHT%20n%C4%83m%202022.pdf",
        "verification_status": "vision_extracted",
    },
    "tuition": {
        "document_title": "Quy định học phí 2024-2025 - các mức học phí khác",
        "document_no": "",
        "document_type": "quy_dinh_hoc_phi",
        "year": 2024,
        "source_url": "https://ctt.hust.edu.vn/Upload/Nguyen%20Quoc%20Dat/files/DTDH_QDQC/Hocphi/2024-2025/2024_2_%20Q%C4%90%20h%E1%BB%8Dc%20ph%C3%AD%20-%202024-2025.pdf",
        "verification_status": "vision_extracted",
    },
}

DIEU_RE = re.compile(r"^###\s+(Điều\s+(\d+)\.?\s*(.*))$")
CHUONG_RE = re.compile(r"^##\s+(Chương\s+[IVXLC]+.*)$")


def build(slug: str, meta: dict) -> list[dict]:
    src = ROOT / "data" / "raw" / slug / "transcript"
    text = "\n".join(
        f.read_text(encoding="utf-8") for f in sorted(src.glob("*.md"))
    )

    chunks, current, chuong = [], None, ""
    for line in text.splitlines():
        if m := CHUONG_RE.match(line):
            chuong = m.group(1).strip()
            continue
        if m := DIEU_RE.match(line):
            if current:
                chunks.append(current)
            current = {**meta, "chuong": chuong, "dieu_no": m.group(2),
                       "khoan_no": "", "heading": m.group(1).strip(),
                       "page_no": "", "lines": []}
            continue
        if current is not None and line.strip():
            current["lines"].append(line.strip())
    if current:
        chunks.append(current)

    # Gop cac phan "(tiep)" (do noi dung Dieu trai dai qua nhieu trang scan)
    # ve dung Dieu goc, tranh 1 Dieu bi tach thanh nhieu chunk roi rac.
    merged = {}
    for c in chunks:
        key = c["dieu_no"]
        if key in merged:
            merged[key]["lines"] += c["lines"]
        else:
            if "(tiếp)" in c["heading"]:
                c["heading"] = c["heading"].replace(" (tiếp)", "")
            merged[key] = c
    chunks = list(merged.values())

    out = []
    for c in chunks:
        body = "\n".join(c.pop("lines")).strip()
        if len(body) < 60:
            continue
        # gop phan "(tiep)" vao Dieu chinh neu trung so
        out.append({**c, "text": f"[{c['heading']}]\n{body}"})
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, meta in DOCS.items():
        chunks = build(slug, meta)
        path = OUT / f"{slug}.chunks.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        chars = sum(len(c["text"]) for c in chunks)
        print(f"  {path.name}: {len(chunks)} chunk | {chars} ký tự")
