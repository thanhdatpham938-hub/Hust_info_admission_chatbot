"""Boc bang chi tieu + to hop tu trang de an tuyen sinh (HTML that, khong phai anh).

Sinh 3 file:
  data/processed/quotas_<year>.csv            - 1 dong/nganh: chi tieu + nhom chuong trinh
  data/processed/program_methods_<year>.csv   - 1 dong/(nganh, phuong thuc) ap dung
  data/processed/subject_combinations_ref.csv - dinh nghia to hop (A00 = Toan, Ly, Hoa)

Tach program_methods ra long format vi 1 nganh xet nhieu phuong thuc -> de truy van
"nganh nao xet bang DGTD?" bang WHERE method_code='DGTD'.

Dung: python scripts/build_quotas.py
"""

import csv
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

import aliases as alias_mod

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "de_an"
OUT = ROOT / "data" / "processed"

SOURCES = {
    2025: "https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025",
    2026: "https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026",
}
METHODS = ["XTTN", "DGTD", "THPT"]
CHECK = {"Ö", "ü", "X", "x", "✓", "v"}          # ky tu danh dau trong bang goc
GROUP_RE = re.compile(r"^[A-Z]\.\s*(.+)$")       # "A. CHUONG TRINH CHUAN"
CODE_RE = re.compile(r"^[A-Z]{2,6}(-[A-Z0-9]{1,4})?[0-9]{0,2}$")
ALIAS_CSV = OUT / "program_aliases.csv"


def load_aliases(year: int) -> dict[str, str]:
    """Cac nguon chinh thuc cua HUST ghi ma khac nhau (TE-EP vs TEEP, 'CH -E20' thua dau cach).

    Chuan hoa ve ma canonical cua chinh nam do de khop voi programs_<year>.csv.
    """
    if not ALIAS_CSV.exists():
        return {}
    with ALIAS_CSV.open(encoding="utf-8", newline="") as f:
        return {
            r["alias"].replace(" ", ""): r["canonical_code"]
            for r in csv.DictReader(f)
            if int(r["year"]) == year
        }


def rows_of(table) -> list[list[str]]:
    return [
        [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        for tr in table.find_all("tr")
    ]


def find_quota_table(soup) -> object | None:
    for t in soup.find_all("table"):
        head = " ".join(rows_of(t)[0]).lower() if rows_of(t) else ""
        if "chỉ tiêu" in head and "mã xét tuyển" in head:
            return t
    return None


def parse_quotas(year: int) -> tuple[list[dict], list[dict]]:
    html = (RAW / f"de_an_{year}.html").read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    table = find_quota_table(soup)
    if table is None:
        print(f"  [LOI] {year}: khong tim thay bang chi tieu")
        return [], []

    today, src = time.strftime("%Y-%m-%d"), SOURCES[year]
    aliases = alias_mod.load(year)
    quotas, methods, group = [], [], ""

    for cells in rows_of(table):
        cells = [c.strip() for c in cells]
        if not cells or not any(cells):
            continue
        # dong tieu de nhom: 1 o duy nhat dang "A. CHUONG TRINH ..."
        if len([c for c in cells if c]) == 1:
            if m := GROUP_RE.match(cells[0].strip()):
                group = m.group(1).strip()
            continue
        if len(cells) < 4 or not re.fullmatch(r"\d+", cells[0]):
            continue

        name, quota_raw, code = cells[1], cells[2], cells[3].replace(" ", "")
        code = aliases.get(code, code)
        if not CODE_RE.match(code):
            continue
        quota = int(re.sub(r"[^\d]", "", quota_raw)) if re.search(r"\d", quota_raw) else ""

        quotas.append({
            "program_code": code, "program_name": name, "year": year,
            "program_group": group, "quota": quota, "quota_type": "tong_nganh",
            "source_url": src, "collection_date": today,
            "verification_status": "html_parsed",
        })
        for i, method in enumerate(METHODS):
            idx = 4 + i
            if idx < len(cells) and cells[idx] in CHECK:
                methods.append({
                    "program_code": code, "year": year, "method_code": method,
                    "source_url": src, "collection_date": today,
                    "verification_status": "html_parsed",
                })
    return quotas, methods


def parse_combinations() -> list[dict]:
    """Dinh nghia to hop lay tu de an 2025 (bang 'To hop | Cac mon/bai thi')."""
    html = (RAW / "de_an_2025.html").read_text(encoding="utf-8", errors="replace")
    today, out = time.strftime("%Y-%m-%d"), []
    for table in BeautifulSoup(html, "html.parser").find_all("table"):
        rows = rows_of(table)
        head = " ".join(rows[0]).lower().replace(" ", "") if rows else ""
        if "tổhợp" not in head:
            continue
        for cells in rows[1:]:
            if len(cells) < 2:
                continue
            code = cells[0].replace(" ", "").strip()
            if not re.fullmatch(r"[A-Z]\d{2}", code):
                continue
            out.append({
                "combination_code": code,
                "subjects": cells[1].strip(),
                "source_url": SOURCES[2025],
                "collection_date": today,
                "verification_status": "html_parsed",
            })
    return out


def write(rows: list[dict], name: str) -> None:
    if not rows:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} dong")


if __name__ == "__main__":
    for year in SOURCES:
        print(f"De an {year}")
        quotas, methods = parse_quotas(year)
        write(quotas, f"quotas_{year}.csv")
        write(methods, f"program_methods_{year}.csv")
        if quotas:
            total = sum(q["quota"] for q in quotas if isinstance(q["quota"], int))
            groups = sorted({q["program_group"] for q in quotas})
            print(f"  tong chi tieu: {total} | nhom: {groups}")
    print("To hop xet tuyen")
    write(parse_combinations(), "subject_combinations_ref.csv")
