"""Boc TO HOP XET TUYEN THEO TUNG NGANH tu trang danh muc nganh cua ts.hust.edu.vn.

Day la du lieu KHONG suy ra duoc tu bang diem chuan: cot subject_combination o do
chi la "to hop goc" dung quy doi diem (chi co A00 hoac D01), khong phai danh sach
to hop duoc xet. De an 2026 cung chi ghi chung 8 to hop cho toan truong.

Trang https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc co 68 accordion,
moi nganh mot muc, ben trong ghi ro to hop theo TUNG PHUONG THUC.

Sinh 1 dong / (nganh, phuong thuc, to hop) -> tra loi duoc ca 2 chieu:
  "nganh IT1 xet to hop nao?" va "to hop A01 xet duoc nhung nganh nao?"
"""

import csv
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

import aliases

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "de_an" / "nganh_dao_tao.html"
OUT = ROOT / "data" / "processed"
SOURCE_URL = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc"
YEAR = 2026

CODE_RE = re.compile(r"Mã xét tuyển:\s*([A-Z][A-Z0-9 \-]{1,12}?)\s+(?=[A-ZĐ]|$)")
LANG_RE = re.compile(r"Ngôn ngữ đào tạo:\s*([^:]{2,40}?)\s+Mã xét tuyển")
# "Xet tuyen theo KQ Ky thi DGTD ... To hop xet tuyen: K00 K00 : Bai thi..."
# Tach text theo cac moc phuong thuc roi quet ma to hop trong tung doan:
# regex mot phat khong dung vi sau 'TN THPT' co dau ':' chan lai.
METHOD_MARKERS = [
    ("Xét tuyển theo KQ Kỳ thi ĐGTD", "DGTD"),
    ("Xét tuyển theo KQ Kỳ thi TN THPT", "THPT"),
]
COMB_RE = re.compile(r"\b([A-Z]\d{2})\b")

METHOD_MAP = {
    "Xét tuyển theo KQ Kỳ thi ĐGTD": "DGTD",
    "Xét tuyển theo KQ Kỳ thi TN THPT": "THPT",
    "Xét tuyển tài năng": "XTTN",
}


def parse() -> list[dict]:
    soup = BeautifulSoup(SRC.read_text(encoding="utf-8", errors="replace"), "html.parser")
    alias_map = aliases.load(YEAR)
    today = time.strftime("%Y-%m-%d")
    rows, seen = [], set()

    for div in soup.find_all(id=re.compile(r"^collapse\d+")):
        text = re.sub(r"\s+", " ", div.get_text(" ")).strip()
        m_code = CODE_RE.search(text)
        if not m_code:
            continue
        code = aliases.canonical(m_code.group(1).strip(), alias_map)
        lang = (LANG_RE.search(text).group(1).strip() if LANG_RE.search(text) else "")

        # cat text thanh cac doan theo moc phuong thuc
        marks = sorted(
            ((text.find(lbl), lbl, mc) for lbl, mc in METHOD_MARKERS if lbl in text),
        )
        for idx, (pos, lbl, method) in enumerate(marks):
            stop = marks[idx + 1][0] if idx + 1 < len(marks) else len(text)
            seg = text[pos:stop]
            if "Tổ hợp xét tuyển" not in seg:
                continue
            seg = seg[seg.index("Tổ hợp xét tuyển"):]
            for comb in dict.fromkeys(COMB_RE.findall(seg)):
                key = (code, method, comb)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "program_code": code, "year": YEAR, "method_code": method,
                    "combination_code": comb, "language": lang,
                    "source_url": SOURCE_URL, "collection_date": today,
                    "verification_status": "html_parsed",
                })
    return rows


if __name__ == "__main__":
    rows = parse()
    path = OUT / f"subject_combinations_{YEAR}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    progs = {r["program_code"] for r in rows}
    combs = {r["combination_code"] for r in rows}
    print(f"  {path.name}: {len(rows)} dòng | {len(progs)} ngành | {len(combs)} tổ hợp")
    print(f"  tổ hợp gặp: {sorted(combs)}")