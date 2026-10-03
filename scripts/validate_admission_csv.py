"""Validate file điểm chuẩn long-format trước khi coi là dữ liệu dùng được.

Bắt các lỗi transcribe từ ảnh: sai mã ngành, trùng dòng, điểm ngoài thang,
thiếu dòng, và điểm lệch bất thường giữa các năm.

Dùng: python scripts/validate_admission_csv.py [file.csv ...]
Không truyền tham số -> validate toàn bộ data/processed/admission_scores_*.csv
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

VALID_METHODS = {"THPT", "XTTN_1.2", "XTTN_1.3", "DGTD"}
# Ngưỡng cảnh báo lệch điểm giữa 2 năm, tính theo TỈ LỆ của thang điểm:
# 5/30 điểm (~17%) là biến động lớn thật, nhưng 5/100 điểm chỉ là 5% — rất bình thường.
MAX_DIFF_RATIO = 1 / 6


def load_program_codes(year: int) -> set[str]:
    """Mã ngành hợp lệ CỦA ĐÚNG NĂM ĐÓ (bảng ngành tách riêng theo năm).

    Danh sách ngành thay đổi theo năm (ngành mở mới, ngành ngừng tuyển, mã đổi
    cách viết), nên không dùng chung một master list cho mọi năm.
    """
    path = PROCESSED / f"programs_{year}.csv"
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as f:
        return {row["program_code"] for row in csv.DictReader(f)}


def validate(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))

    if not rows:
        return [f"{path.name}: file rỗng"], []

    year = int(rows[0]["year"])
    known_codes = load_program_codes(year)
    if not known_codes:
        return [f"{path.name}: thiếu bảng ngành data/processed/programs_{year}.csv"], []

    seen = set()
    programs = set()
    for i, row in enumerate(rows, start=2):  # dòng 1 là header
        code, method = row["program_code"], row["method_code"]
        programs.add(code)

        if code not in known_codes:
            errors.append(f"{path.name}:{i} mã ngành '{code}' không có trong programs_{year}.csv")

        if method not in VALID_METHODS:
            errors.append(f"{path.name}:{i} phương thức '{method}' không hợp lệ")

        # Tu 2026 mot nganh co the co 2 muc diem THPT khac nhau theo NHOM TO HOP
        # (nhom ky thuat cao hon nhom kinh te 0,5 diem), nen nhom to hop la mot
        # phan cua khoa — thieu no se bao trung dong oan.
        key = (code, row["year"], method, row.get("combination_group", ""))
        if key in seen:
            errors.append(f"{path.name}:{i} trùng dòng {key}")
        seen.add(key)

        try:
            score, scale = float(row["score"]), float(row["scale"])
        except ValueError:
            errors.append(f"{path.name}:{i} score/scale không phải số")
            continue
        if scale not in (30, 100):
            errors.append(f"{path.name}:{i} scale phải là 30 hoặc 100, nhận '{scale}'")
        elif not 0 <= score <= scale:
            errors.append(f"{path.name}:{i} điểm {score} ngoài thang {scale:g} ({code}/{method})")

    # mỗi ngành phải đủ số phương thức như nhau -> lệch nghĩa là transcribe thiếu
    per_program = defaultdict(set)
    for row in rows:
        per_program[row["program_code"]].add(row["method_code"])
    method_counts = {len(m) for m in per_program.values()}
    if len(method_counts) > 1:
        odd = {p: sorted(m) for p, m in per_program.items() if len(m) != max(method_counts)}
        warnings.append(f"{path.name}: ngành thiếu phương thức so với số đông: {odd}")

    print(f"{path.name}: {len(rows)} dòng, {len(programs)} ngành, {len(seen)} tổ hợp duy nhất "
          f"(đối chiếu programs_{year}.csv: {len(known_codes)} mã)")
    return errors, warnings


def cross_year_check(paths: list[Path]) -> list[str]:
    """Cảnh báo khi điểm cùng ngành/phương thức lệch bất thường giữa 2 năm."""
    by_key = defaultdict(dict)
    scales = {}
    for path in paths:
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            key = (row["program_code"], row["method_code"])
            year, score = int(row["year"]), float(row["score"])
            # Nganh tach 2 nhom to hop co 2 muc diem; lay muc THAP hon vi do dung
            # la con so cong bo tren bang (nhom ky thuat = muc nay + 0,5). So sanh
            # muc cao voi nam truoc se tao lech gia 0,5 diem.
            by_key[key][year] = min(by_key[key].get(year, score), score)
            scales[key] = float(row["scale"])

    warnings = []
    for (code, method), by_year in by_key.items():
        threshold = scales[(code, method)] * MAX_DIFF_RATIO
        years = sorted(by_year)
        for a, b in zip(years, years[1:]):
            diff = abs(by_year[b] - by_year[a])
            if diff > threshold:
                warnings.append(
                    f"{code}/{method}: {a}={by_year[a]} -> {b}={by_year[b]} "
                    f"(lệch {diff:.2f}, ngưỡng {threshold:.1f}), soát lại"
                )
    return warnings


def main() -> int:
    args = sys.argv[1:]
    paths = [Path(a) for a in args] if args else sorted(
        (ROOT / "data" / "processed").glob("admission_scores_*.csv")
    )
    if not paths:
        print("Không tìm thấy file nào để validate")
        return 1


    all_errors, all_warnings = [], []
    for path in paths:
        errors, warnings = validate(path)
        all_errors += errors
        all_warnings += warnings
    all_warnings += cross_year_check(paths)

    for w in all_warnings:
        print(f"  [CẢNH BÁO] {w}")
    for e in all_errors:
        print(f"  [LỖI] {e}")

    print(f"\n{len(all_errors)} lỗi, {len(all_warnings)} cảnh báo")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
