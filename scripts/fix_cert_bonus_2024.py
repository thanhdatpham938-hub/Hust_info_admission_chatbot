"""Tach dung 2 bang chung chi nam 2024 trong cert_bonus_conversion.csv.

De an 2024 co HAI bang rieng, ranh gioi muc KHAC NHAU:
  - Bang 5, 6 (trang 24): DIEM THUONG cong vao diem ĐGTD
  - Bang 7, 8 (trang 25-26): DIEM QUY DOI thay diem mon tieng Anh khi xet THPT
Ban cu gop 2 bang vao mot dong, nen co dong "VSTEP 7,5 - 8,0" lay tu Bang 5 nhung
Bang 7 lai chia 7,0-7,5 (9,50) va >=8,0 (10,00) — khoang do VAT QUA hai muc quy doi,
khong the co mot gia tri duy nhat. O trong khong phai thieu du lieu ma la gop sai bang.

Nam 2025, 2026 chi co MOT bang ghi ca hai cot cung ranh gioi nen giu nguyen.

Dung: python scripts/fix_cert_bonus_2024.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "processed" / "cert_bonus_conversion.csv"
SRC = "Đề án tuyển sinh 2024 -FINAL.pdf"

# (certificate, cert_value, bonus_point, converted_score_10, table_purpose, source)
ROWS_2024 = [
    # Bang 5 - Diem thuong VSTEP (trang 24)
    ("VSTEP", "5,0 - 5,5", "1", "", "diem_thuong", f"{SRC} - Bảng 5 (trang 24)"),
    ("VSTEP", "6,0 - 6,5", "2", "", "diem_thuong", f"{SRC} - Bảng 5 (trang 24)"),
    ("VSTEP", "7,0", "3", "", "diem_thuong", f"{SRC} - Bảng 5 (trang 24)"),
    ("VSTEP", "7,5 - 8,0", "4", "", "diem_thuong", f"{SRC} - Bảng 5 (trang 24)"),
    ("VSTEP", "≥ 8,5", "5", "", "diem_thuong", f"{SRC} - Bảng 5 (trang 24)"),
    # Bang 6 - Diem thuong IELTS (trang 24)
    ("IELTS Academic", "5.0", "1", "", "diem_thuong", f"{SRC} - Bảng 6 (trang 24)"),
    ("IELTS Academic", "5.5", "2", "", "diem_thuong", f"{SRC} - Bảng 6 (trang 24)"),
    ("IELTS Academic", "6.0", "3", "", "diem_thuong", f"{SRC} - Bảng 6 (trang 24)"),
    ("IELTS Academic", "6.5", "4", "", "diem_thuong", f"{SRC} - Bảng 6 (trang 24)"),
    ("IELTS Academic", "≥ 7.0", "5", "", "diem_thuong", f"{SRC} - Bảng 6 (trang 24)"),
    # Bang 7 - Quy doi VSTEP thay mon tieng Anh (trang 25)
    ("VSTEP", "5,0 - 5,5", "", "8.50", "quy_doi", f"{SRC} - Bảng 7 (trang 25)"),
    ("VSTEP", "6,0 - 6,5", "", "9.00", "quy_doi", f"{SRC} - Bảng 7 (trang 25)"),
    ("VSTEP", "7,0 - 7,5", "", "9.50", "quy_doi", f"{SRC} - Bảng 7 (trang 25)"),
    ("VSTEP", "≥ 8,0", "", "10.00", "quy_doi", f"{SRC} - Bảng 7 (trang 25)"),
    # Bang 8 - Quy doi IELTS thay mon tieng Anh (trang 25-26)
    ("IELTS Academic", "5.0", "", "8.50", "quy_doi", f"{SRC} - Bảng 8 (trang 25-26)"),
    ("IELTS Academic", "5.5", "", "9.00", "quy_doi", f"{SRC} - Bảng 8 (trang 25-26)"),
    ("IELTS Academic", "6.0", "", "9.50", "quy_doi", f"{SRC} - Bảng 8 (trang 25-26)"),
    ("IELTS Academic", "≥ 6.5", "", "10.00", "quy_doi", f"{SRC} - Bảng 8 (trang 25-26)"),
]

NOTE = {
    "diem_thuong": "Điểm thưởng cộng vào điểm xét ĐGTD (thang 100). Ranh giới mức KHÁC bảng quy đổi.",
    "quy_doi": "Điểm quy đổi thay cho điểm thi môn tiếng Anh khi xét THPT theo tổ hợp A01, D07, D01.",
}


def main() -> None:
    rows = list(csv.DictReader(PATH.open(encoding="utf-8", newline="")))
    cols = list(rows[0].keys())
    if "table_purpose" not in cols:
        cols.insert(cols.index("note"), "table_purpose")

    kept = [r for r in rows if r["year"] != "2024"]
    for r in kept:
        # 2025, 2026: mot bang duy nhat ghi ca diem thuong va diem quy doi cung ranh gioi
        r.setdefault("table_purpose", "")
        r["table_purpose"] = r["table_purpose"] or "ca_hai"

    new = [{
        "year": "2024", "certificate": cert, "cert_value": val, "bonus_point": bonus,
        "converted_score_10": conv, "table_purpose": purpose, "note": NOTE[purpose],
        "source": src, "verification_status": "vision_extracted",
    } for cert, val, bonus, conv, purpose, src in ROWS_2024]

    out = new + kept
    out.sort(key=lambda r: (r["year"], r["table_purpose"], r["certificate"], r["cert_value"]))
    with PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    old_2024 = sum(1 for r in rows if r["year"] == "2024")
    print(f"2024: {old_2024} dòng gộp lẫn -> {len(new)} dòng tách theo đúng 4 bảng gốc")
    print(f"Tổng: {len(out)} dòng")


if __name__ == "__main__":
    main()
