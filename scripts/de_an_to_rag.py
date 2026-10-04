"""Chunk phan VAN BAN cua de an tuyen sinh -> nguon RAG.

Nguon:
  2024: PDF co text layer (pdftotext -layout)
  2025, 2026: HTML da tai ve o data/raw/de_an/

Nguyen tac quan trong: LOAI BO cac vung bang so lieu da boc sang CSV o
Giai doan 2 (chi tieu, to hop, quy doi chung chi, hoc phi). Neu de cung mot
bang vua nam trong Postgres vua nam trong vector DB, bot se tra loi 2 dang
khac nhau cho cung mot cau hoi.
"""

import json
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rag" / "raw_chunks"
RAW_DE_AN = ROOT / "data" / "raw" / "de_an"
PDF_2024 = ROOT / "data" / "raw" / "admission" / "Đề án tuyển sinh 2024 -FINAL.pdf"

SOURCES = {
    # Trang dang de an 2024 nhung file Google Drive; da doi chieu: file tren Drive trung tung byte
    # voi data/raw/admission/Đề án tuyển sinh 2024 -FINAL.pdf (2026-09-26)
    2024: "https://ts.hust.edu.vn/tin-tuc/de-an-tuyen-sinh-dai-hoc-nam-2024",
    2025: "https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025",
    2026: "https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026",
}

# Tieu de muc: "I. ...", "1. ...", "1.4. ..." co chu tieng Viet theo sau
HEADING_RE = re.compile(r"^\s*((?:[IVX]+|\d+(?:\.\d+)?)\.)\s+([A-ZĐÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĨŨƠƯẠ-ỹ].{4,110})$")
# Phuong thuc (2) TSA va (3) THPT: ca 3 nam deu danh so kieu "(2) Xet tuyen..." / "(3) Xet
# tuyen..." (ngoac don) thay vi "2." / "3." (dau cham) nhu (1.1)/(1.2)/(1.3) - HEADING_RE o tren
# KHONG bat duoc -> hai muc nay bi gop lam duoi cua muc "1.3" truoc do (phat hien 2026-10-04,
# vd dean2026::m1.3-2 chua nguyen van cong thuc K01/8 to hop nhung heading van ghi "1.3 Ho so
# nang luc"). Loc theo tu khoa (khong loc theo so thu tu) de KHONG bat nham cac dong liet ke
# khac cung dang "(N) Xet tuyen..." (vd "(3) Xet tuyen va xac nhan nhap hoc" trong de an 2024).
TOP_METHOD_RE = re.compile(
    r"^\((\d)\)\s+(Xét tuyển.{10,110}(?:Đánh giá tư duy|tốt nghiệp THPT).{0,40})$"
)
TABLE_START_RE = re.compile(r"^\s*Bảng\s+\d+\s*[-–.]")
MIN_CHUNK = 200
TARGET = 1400


def is_table_line(raw: str, text: str) -> bool:
    """Dong bang le: nhieu cum so VA co khoang trang can cot.

    Sau khi thoat che do bo-qua-bang, van con vai dong bang sot lai (vd dong
    cuoi cua bang chi tieu). Bo TUNG DONG thay vi bat lai che do bo ca vung,
    de khong lam mat doan van ngay sau do.
    """
    return (len(re.findall(r"[0-9][0-9.,]*", text)) >= 4
            and re.search(r"[ 	]{3,}", raw) is not None)


def is_prose(raw: str, text: str) -> bool:
    """Cau van that: dai, khong can cot (khong co run >=3 space), it so, co tu tieng Viet.

    Dung de THOAT che do bo-qua-bang: truoc day chi thoat khi gap tieu de muc ke tiep,
    nen doan van nam ngay sau bang bi bo nham cung voi bang.
    """
    return (len(text) > 80 and "   " not in raw.strip()
            and len(re.findall(r"[0-9][0-9.,]*", text)) <= 2
            and bool(re.search(r"[a-zà-ỹ]{4,}[ ]+[a-zà-ỹ]{4,}", text)))


def looks_like_table_row(text: str) -> bool:
    """Dong bang thuong co nhieu cum so -> khong phai tieu de muc."""
    return len(re.findall(r"\b\d[\d.,]*\b", text)) >= 3


def pdf_lines_2024() -> list[str]:
    out = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", "-layout", str(PDF_2024), "-"],
        capture_output=True, check=True,
    )
    return out.stdout.decode("utf-8", "replace").splitlines()


def html_lines(year: int) -> list[str]:
    html = (RAW_DE_AN / f"de_an_{year}.html").read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "table"]):
        tag.decompose()  # bo luon <table>: da boc sang CSV
    main = max(
        soup.find_all(class_=re.compile(r"content|entry|post|detail", re.I)) or [soup],
        key=lambda c: len(c.get_text(strip=True)),
    )
    lines = []
    for raw in main.get_text("\n").splitlines():
        text = re.sub(r"\s+", " ", raw).strip()
        # Het bai viet: sau "Luu tin / Binh luan / Chia se" la khung "Co the ban se thich" (tin
        # lien quan, vd "Vu Van Binh - Ban tre ... Viettel") -> truoc day lot vao chunk cuoi.
        if text == "Lưu tin":
            break
        if text and (not lines or lines[-1] != text):
            lines.append(text)
    return lines


def build_chunks(lines: list[str], year: int) -> list[dict]:
    meta = {
        "document_title": f"Đề án tuyển sinh {year}",
        "document_no": "",
        "document_type": "de_an_tuyen_sinh",
        "year": year,
        "source_url": SOURCES[year],
    }
    sections, current, in_table = [], None, False

    for line in lines:
        text = line.strip()
        if not text:
            continue
        if TABLE_START_RE.match(text):
            in_table = True          # bo qua toan bo vung bang (da co trong CSV)
            continue

        m = HEADING_RE.match(text)
        if m and not looks_like_table_row(m.group(2)):
            in_table = False
            if current:
                sections.append(current)
            current = {**meta, "chuong": "", "dieu_no": "", "khoan_no": "",
                       "heading": f"{m.group(1)} {m.group(2)}".strip(), "page_no": "",
                       "lines": []}
            continue
        m2 = TOP_METHOD_RE.match(text)
        if m2 and not looks_like_table_row(m2.group(2)):
            in_table = False
            if current:
                sections.append(current)
            current = {**meta, "chuong": "", "dieu_no": "", "khoan_no": "",
                       "heading": f"({m2.group(1)}) {m2.group(2)}".strip(), "page_no": "",
                       "lines": []}
            continue
        if in_table and is_prose(line, text):
            in_table = False   # het bang, tro lai lay van ban
        if in_table or current is None:
            continue
        if is_table_line(line, text):
            continue
        current["lines"].append(text)

    if current:
        sections.append(current)

    # Muc ngan (vd "1.2. Pham vi tuyen sinh: Toan quoc.") KHONG bo di - gop vao
    # muc ke tiep, vi van chua du kien co gia tri (tong chi tieu, pham vi, doi tuong).
    chunks, carry = [], ""
    for sec in sections:
        body = "\n".join(sec.pop("lines")).strip()
        body = re.sub(r"\.{4,}\s*\d*", "", body).strip()
        if carry:
            body = carry + "\n" + body
            carry = ""
        if len(body) < MIN_CHUNK:
            carry = f"[{sec['heading']}]\n{body}"
            continue
        if len(body) <= TARGET * 2:
            chunks.append({**sec, "text": f"[{sec['heading']}]\n{body}"})
            continue
        buf, part = [], 1
        for para in body.split("\n"):
            buf.append(para)
            if sum(len(x) for x in buf) >= TARGET:
                chunks.append({**sec, "heading": f"{sec['heading']} (phan {part})",
                               "text": f"[{sec['heading']}]\n" + "\n".join(buf)})
                buf, part = [], part + 1
        if buf:
            chunks.append({**sec, "heading": f"{sec['heading']} (phan {part})",
                           "text": f"[{sec['heading']}]\n" + "\n".join(buf)})
    if carry and chunks:
        chunks[-1]["text"] += "\n" + carry
    return chunks


def write(chunks: list[dict], year: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"de_an_tuyen_sinh_{year}"
    with (OUT / f"{stem}.chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    md = [f"# Đề án tuyển sinh {year}", "", f"> Nguồn: {SOURCES[year]}", ""]
    for c in chunks:
        md += [f"## {c['heading']}", "", c["text"].split("\n", 1)[1], ""]
    (OUT / f"{stem}.md").write_text("\n".join(md), encoding="utf-8")
    chars = sum(len(c["text"]) for c in chunks)
    print(f"  {stem}: {len(chunks)} chunk | {chars} ký tự")


if __name__ == "__main__":
    print("Đề án 2024 (PDF)")
    write(build_chunks(pdf_lines_2024(), 2024), 2024)
    for year in (2025, 2026):
        print(f"Đề án {year} (web)")
        write(build_chunks(html_lines(year), year), year)
