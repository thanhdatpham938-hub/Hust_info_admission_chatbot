"""Sinh bảng mã ngành RIÊNG cho từng năm (quyết định: tách theo năm, không gộp master list).

Danh sách ngành đổi theo năm: ngành mở mới, ngành ngừng tuyển (EM4, TROY-BA có ở
2024-2025 nhưng không còn ở 2026), và cách viết mã cũng đổi (TE-EP/TE-E2 ở 2024-2025
-> TEEP/TEE2 ở 2026). Vì vậy mỗi năm một bảng riêng.

Nguồn:
  - 2026: data/raw/admission/ma_nganh_truong.md (có sẵn cột Trường/Khoa)
  - 2024, 2025: bảng điểm chuẩn đã transcribe; Trường/Khoa suy ra bằng đối chiếu
    mã/tên với bảng 2026, phần còn lại dùng bảng ánh xạ thủ công có ghi căn cứ.

Dùng: python scripts/build_programs.py
"""

import csv
import re
import unicodedata
from pathlib import Path

import aliases

ROOT = Path(__file__).resolve().parent.parent
MA_NGANH = ROOT / "data" / "raw" / "admission" / "ma_nganh_truong.md"
RAW = ROOT / "data" / "raw" / "admission_scores"
OUT_DIR = ROOT / "data" / "processed"

FIELDNAMES = ["program_code", "program_name", "faculty_name", "year", "source"]

# Ngành chỉ có ở 2024-2025, không còn trong bảng 2026 -> gán Trường/Khoa thủ công.
# Ghi rõ căn cứ để sau này truy vết được.
FACULTY_OVERRIDES = {
    "TE-EP": ("Trường Cơ khí", "trùng tên ngành với TEEP trong bảng 2026"),
    "TE-E2": ("Trường Cơ khí", "trùng tên ngành với TEE2 trong bảng 2026"),
    "EM4": ("Trường Kinh tế", "sem.hust.edu.vn/dao-tao-dai-hoc liệt kê 'Chương trình cử nhân Kế toán'"),
    "TROY-BA": ("Trường Kinh tế", "sem.hust.edu.vn/dao-tao-dai-hoc liệt kê 'Chương trình quốc tế Quản trị kinh doanh - Troy'"),
}

SOURCE_LABELS = {
    2024: "ts.hust.edu.vn bảng điểm chuẩn 2024 (ảnh image002-bk/image004-bk)",
    2025: "ts.hust.edu.vn bảng điểm chuẩn 2025 (ảnh bka1/bka2)",
}


def normalize(text: str) -> str:
    """Bỏ dấu, hạ chữ thường, gộp khoảng trắng -> để so khớp tên ngành."""
    # "đ" khong phai to hop dau nen NFD khong tach; khong doi sang "d" truoc thi
    # buoc loc [^a-z0-9] se XOA han: "diem" -> "iem", "dang ky" -> "ang ky".
    # Nguoi dung go khong dau se khong khop duoc ten nganh — dung pham vi PRD 3.B.
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_ma_nganh_2026() -> list[dict]:
    alias_map = aliases.load(2026)
    rows = []
    for line in MA_NGANH.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 5 and re.fullmatch(r"\d+", cells[1] or ""):
            rows.append(
                {
                    "program_code": aliases.canonical(cells[2], alias_map),
                    "program_name": cells[3],
                    "faculty_name": cells[4],
                    "year": 2026,
                    "source": "data/raw/admission/ma_nganh_truong.md",
                }
            )
    return rows


def build_from_scores(year: int, programs_2026: list[dict]) -> list[dict]:
    by_code = {p["program_code"]: p for p in programs_2026}
    by_name = {normalize(p["program_name"]): p for p in programs_2026}

    wide = RAW / str(year) / f"diem_chuan_{year}_wide.csv"
    alias_map = aliases.load(year)
    rows, unresolved = [], []
    for r in csv.DictReader(wide.open(encoding="utf-8-sig", newline="")):
        code = aliases.canonical(r["program_code"], alias_map)
        name = r["program_name"].strip()

        match = by_code.get(code) or by_name.get(normalize(name))
        if match:
            faculty = match["faculty_name"]
        elif code in FACULTY_OVERRIDES:
            faculty = FACULTY_OVERRIDES[code][0]
        else:
            faculty = ""
            unresolved.append(code)

        rows.append(
            {
                "program_code": code,
                "program_name": name,
                "faculty_name": faculty,
                "year": year,
                "source": SOURCE_LABELS[year],
            }
        )

    if unresolved:
        print(f"  [CẢNH BÁO] {year}: chưa xác định được Trường/Khoa cho {unresolved}")
    return rows


def write(rows: list[dict], year: int) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"programs_{year}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.relative_to(ROOT)}: {len(rows)} ngành")


if __name__ == "__main__":
    p2026 = parse_ma_nganh_2026()
    write(p2026, 2026)
    for y in (2025, 2024):
        write(build_from_scores(y, p2026), y)
