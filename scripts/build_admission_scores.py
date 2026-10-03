"""Chuyển bảng điểm chuẩn dạng wide (transcribe từ ảnh) sang long format.

Long format = 1 dòng / (program_code, year, method_code) — đúng schema bảng
`admission_scores` trong PRD mục 15.1, để bước nạp PostgreSQL sau này import thẳng.

Dùng: python scripts/build_admission_scores.py <year>
"""

import csv
import sys
from datetime import date
from pathlib import Path

import aliases

ROOT = Path(__file__).resolve().parent.parent

# Cột điểm trong bảng gốc -> (method_code, scale)
METHOD_COLUMNS = {
    "THPT": ("THPT", 30),
    "XTTN_1.2": ("XTTN_1.2", 100),
    "XTTN_1.3": ("XTTN_1.3", 100),
    "DGTD": ("DGTD", 100),
}

SOURCE_URLS = {
    2024: "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53",
    2025: "https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa",
    2026: "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026",
}

FIELDNAMES = [
    "program_code",
    "program_name",
    "year",
    "method_code",
    "scale",
    "score",
    "combination_group",
    "subject_combinations",
    "score_note",
    "source_url",
    "collection_date",
    "verification_status",
]

# Do lech diem giua 2 nhom to hop (chi ap dung cho phuong thuc THPT).
# Nguon: bai cong bo diem chuan chinh thuc tung nam, muc "Do lech diem giua cac
# to hop xet tuyen". Nganh nao xet to hop thuoc CA HAI nhom thi diem chuan nhom
# ky thuat CAO HON nhom kinh te 0,5 diem -> phai la 2 dong du lieu rieng, khong
# phai mot dong kem chu thich, vi hoc sinh hoi thang "khoi A00 nganh nay bao nhieu".
COMBINATION_GROUPS = {
    2025: {
        "ky_thuat": {"A00", "A01", "A02", "B00", "D07", "D26", "D28", "D29", "K01"},
        "kinh_te_gd_nn": {"D01", "D04"},
    },
    2026: {
        "ky_thuat": {"A00", "A01", "B00", "D07", "K01"},
        "kinh_te_gd_nn": {"D01", "D04", "DD2"},
    },
}
GROUP_GAP = 0.5

# Nam co bang diem chuan da duoc DOC KEP: doc lai doc lap tu anh goc roi so tung o
# voi file wide (2026-09-24). 2024: 128 o, 1 o lech -> phong to anh phan xu, file
# wide dung. 2025: 260/260 khop. 2026: 272/272 khop.
# Khong dung nhan manual_verified vi hai lan doc deu la may; nguoi chua soat.
# SUA FILE WIDE CUA NAM NAO THI PHAI BO NAM DO KHOI DAY, neu khong nhan se sai.
DOUBLE_READ_YEARS = {2024, 2025, 2026}
GROUP_LABEL = {"ky_thuat": "khối ngành kỹ thuật", "kinh_te_gd_nn": "khối ngành kinh tế, giáo dục, ngoại ngữ"}


def load_combinations(year: int) -> dict[str, set[str]]:
    """To hop xet tuyen THPT theo tung nganh. Chi nam 2026 co bang nay."""
    path = ROOT / "data" / "processed" / f"subject_combinations_{year}.csv"
    if not path.exists():
        return {}
    out: dict[str, set[str]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("combination_code") or row.get("subject_combination") or "").strip()
            if code:
                out.setdefault(row["program_code"], set()).add(code)
    return out


# Nam khong co bang to hop theo nganh thi muon danh sach to hop cua nam gan nhat.
# CHI duoc dung de biet nganh do xet NHOM nao; diem chuan van lay cua dung nam do.
# Dong sinh ra theo cach nay danh dau rule_derived de phan biet voi so cong bo truc tiep.
COMBINATION_PROXY_YEAR = {2025: 2026}


def group_of(year: int, code: str) -> str | None:
    for group, codes in COMBINATION_GROUPS.get(year, {}).items():
        if code in codes:
            return group
    return None


def split_by_group(year: int, combos: set[str], base_code: str
                   ) -> list[tuple[str, list[str], float]]:
    """Tra ve [(nhom, cac to hop cua nhom do, chenh lech so voi diem cong bo)].

    Diem cong bo tren bang gan voi TO HOP GOC cua tung nganh (cot "To hop goc"
    trong bang diem chuan: A00 hoac D01). Nhom chua to hop goc lech 0; nhom con
    lai lech +0,5 neu la nhom ky thuat, -0,5 neu la nhom kinh te — vi quy dinh
    la nhom ky thuat luon CAO HON nhom kinh te 0,5 diem.

    Ban dau toi gia dinh diem cong bo luon la cua nhom kinh te. Dung voi 2026 vi
    ca 15 nganh tach nhom deu co to hop goc D01, nhung do la trung hop, khong phai
    quy tac: nganh goc A00 ma xet ca D01 thi D01 phai la goc - 0,5, khong phai + 0,5.
    """
    groups = COMBINATION_GROUPS.get(year)
    base_group = group_of(year, base_code)
    if not groups or not combos or not base_group:
        return []
    out = []
    for group in ("ky_thuat", "kinh_te_gd_nn"):
        codes = sorted(combos & groups[group])
        if not codes:
            continue
        if group == base_group:
            gap = 0.0
        else:
            gap = GROUP_GAP if group == "ky_thuat" else -GROUP_GAP
        out.append((group, codes, gap))
    return out


def build(year: int) -> Path:
    src = ROOT / "data" / "raw" / "admission_scores" / str(year) / f"diem_chuan_{year}_wide.csv"
    dst = ROOT / "data" / "processed" / f"admission_scores_{year}.csv"
    dst.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    collected = date.today().isoformat()
    alias_map = aliases.load(year)
    combos_by_program = load_combinations(year)
    proxy_year = None
    if not combos_by_program and year in COMBINATION_PROXY_YEAR:
        proxy_year = COMBINATION_PROXY_YEAR[year]
        combos_by_program = load_combinations(proxy_year)
    expanded = 0
    with src.open(encoding="utf-8-sig", newline="") as f:
        for wide in csv.DictReader(f):
            code = aliases.canonical(wide["program_code"], alias_map)
            for column, (method_code, scale) in METHOD_COLUMNS.items():
                raw = (wide.get(column) or "").strip()
                if not raw:  # ngành không xét theo phương thức này
                    continue
                base = {
                    "program_code": code,
                    "program_name": wide["program_name"].strip(),
                    "year": year,
                    "method_code": method_code,
                    "scale": scale,
                    "source_url": SOURCE_URLS[year],
                    "collection_date": collected,
                    "verification_status": ("vision_double_read" if year in DOUBLE_READ_YEARS
                                            else "vision_extracted"),
                }
                published = float(raw)
                base_code = wide["subject_combination"].strip()
                splits = (split_by_group(year, combos_by_program.get(code, set()), base_code)
                          if method_code == "THPT" else [])

                if not splits:
                    # Không có bảng tổ hợp cho năm này, hoặc phương thức không dùng
                    # tổ hợp môn (XTTN xét hồ sơ, ĐGTD dùng bài thi TSA).
                    rows.append({**base, "score": f"{published:.2f}",
                                 "combination_group": "", "subject_combinations":
                                 wide["subject_combination"].strip(), "score_note": ""})
                    continue

                for group, codes, gap in splits:
                    note, status = "", base["verification_status"]
                    if len(splits) > 1:
                        other = "kinh_te_gd_nn" if group == "ky_thuat" else "ky_thuat"
                        note = (
                            f"Ngành này xét tổ hợp thuộc cả hai khối. Điểm chuẩn tổ hợp "
                            f"{GROUP_LABEL['ky_thuat']} cao hơn tổ hợp "
                            f"{GROUP_LABEL['kinh_te_gd_nn']} {GROUP_GAP:g} điểm, theo quy định độ "
                            f"lệch điểm giữa các tổ hợp mà Đại học Bách khoa Hà Nội công bố năm "
                            f"{year} (căn cứ phổ điểm thi tốt nghiệp THPT). Điểm trên bảng công bố "
                            f"gắn với tổ hợp gốc {base_code}. Dòng này là mức điểm của "
                            f"{GROUP_LABEL[group]}; {GROUP_LABEL[other]} xem dòng còn lại."
                        )
                        if gap:
                            expanded += 1
                            # Dong lech nhom = so SUY RA tu quy tac, khong phai so in tren bang
                            status = "rule_derived"
                            if proxy_year:
                                note += (f" Năm {year} chưa có bảng tổ hợp theo ngành nên danh "
                                         f"sách tổ hợp lấy theo năm {proxy_year}.")
                    rows.append({**base,
                                 "score": f"{published + gap:.2f}",
                                 "combination_group": group,
                                 "subject_combinations": ";".join(codes),
                                 "score_note": note,
                                 "verification_status": status})

    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    extra = f", trong đó {expanded} dòng tách thêm cho tổ hợp khối kỹ thuật (+{GROUP_GAP:g})" if expanded else ""
    print(f"{dst.relative_to(ROOT)}: {len(rows)} dòng long-format{extra}")
    return dst


if __name__ == "__main__":
    years = [int(a) for a in sys.argv[1:]] or [2024, 2025, 2026]
    for y in years:
        build(y)
