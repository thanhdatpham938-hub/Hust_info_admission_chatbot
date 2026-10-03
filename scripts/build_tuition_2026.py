"""Tach hoc phi 2026 theo tung nganh tu program_overview_2026 -> bang so tra cuu duoc.

Cot `tuition_text` tren trang nganh la chuoi nguoi doc ("28 - 40 trieu dong/nam",
"~ 68 trieu dong/nam", "33 trieu dong/hoc ky"). Chuoi thi hien thi tot nhung khong
so sanh hay loc duoc — bot khong tra loi duoc "nganh nao hoc phi duoi 30 trieu".
Script tach thanh so + don vi, GIU nguyen chuoi goc de citation.

Dac biet chu y don vi: 63 nganh tinh /nam, 5 nganh tinh /HOC KY. Gop hai don vi
vao mot cot se sai so tien vai lan.

Dung: python scripts/build_tuition_2026.py
"""

import csv
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
YEAR = 2026
DATASET_VERSION = "2026.1"

FIELDNAMES = [
    "program_code", "program_name", "program_group", "amount_min", "amount_max",
    "unit", "is_approximate", "terms_per_year", "amount_text", "note",
    "year", "source", "source_url", "collection_date", "verification_status",
    "dataset_version",
]

# So hoc ky/nam chi dien khi co nguon noi ro. De an 2024 ghi TROY hoc 3 hoc ky/nam;
# cac chuong trinh LUH/NUT/GU chua thay nguon nao ghi so hoc ky -> de trong, KHONG doan.
TERMS_PER_YEAR = {"TROY-IT": 3}


def parse_amount(text: str) -> tuple[float | None, float | None, str, bool]:
    """'28 - 40 trieu dong/nam' -> (28, 40, 'trieu_dong/nam', False)."""
    approx = "~" in text
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text)]
    if not nums:
        return None, None, "", approx
    unit = "triệu đồng/học kỳ" if "học kỳ" in text else "triệu đồng/năm"
    lo, hi = (nums[0], nums[-1]) if len(nums) > 1 else (nums[0], nums[0])
    return lo, hi, unit, approx


def main() -> None:
    overview = list(csv.DictReader((PROCESSED / f"program_overview_{YEAR}.csv").open(encoding="utf-8", newline="")))
    groups = {r["program_code"]: r["program_group"]
              for r in csv.DictReader((PROCESSED / f"quotas_{YEAR}.csv").open(encoding="utf-8", newline=""))}
    today = date.today().isoformat()

    rows, missing = [], []
    for r in overview:
        code = r["program_code"]
        text = (r["tuition_text"] or "").strip()
        lo, hi, unit, approx = parse_amount(text)
        if lo is None:
            missing.append(code)
            continue
        terms = TERMS_PER_YEAR.get(code, "")
        note = ""
        if "học kỳ" in unit:
            note = ("Tính theo học kỳ, không phải theo năm. "
                    + (f"Chương trình này có {terms} học kỳ/năm."
                       if terms else "Chưa có nguồn ghi rõ số học kỳ mỗi năm nên không quy ra mức/năm."))
        if approx:
            note = (note + " " if note else "") + "Trang ngành ghi mức xấp xỉ (~)."
        rows.append({
            "program_code": code, "program_name": r["program_name"],
            "program_group": groups.get(code, ""),
            "amount_min": f"{lo:g}", "amount_max": f"{hi:g}", "unit": unit,
            "is_approximate": "1" if approx else "0",
            "terms_per_year": terms, "amount_text": text, "note": note,
            "year": YEAR,
            "source": f"Trang giới thiệu ngành trên ts.hust.edu.vn, mục Thông tin nhanh ({code})",
            "source_url": r["source_url"], "collection_date": today,
            "verification_status": "web_extracted", "dataset_version": DATASET_VERSION,
        })

    out = PROCESSED / f"tuition_{YEAR}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    per_year = sum(1 for r in rows if r["unit"].endswith("/năm"))
    print(f"{out.name}: {len(rows)} ngành ({per_year} tính /năm, {len(rows)-per_year} tính /học kỳ)")
    if missing:
        print(f"  [THIẾU] không đọc được học phí: {', '.join(missing)}")


if __name__ == "__main__":
    main()
