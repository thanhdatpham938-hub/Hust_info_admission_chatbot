"""Boc danh sach bo mon/don vi tu trang can bo da tai -> field departments trong info.json.

PRD muc 3.D yeu cau bang faculties co "bo mon truc thuoc". Danh sach CAN BO
(ten tung nguoi) KHONG nam trong pham vi PRD va cung khong lay du duoc: mot
nua so site render danh sach bang JavaScript nen curl chi thay bo loc bo mon.

Khong crawl lai - dung HTML da tai o data/raw/faculty/<code>/can_bo.html.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "faculty"
OUT = ROOT / "data" / "faculty"

UNIT_RE = re.compile(
    r"^(Khoa|Bộ môn|Trung tâm|Viện|Văn phòng|Phòng thí nghiệm|Ban)\s+[A-ZĐÀ-ỹ][^|]{2,70}$"
)
# Dong khong phai don vi thuc su (nhan bo loc, muc dieu huong)
SKIP_RE = re.compile(r"^(Tất cả|Xem thêm|Danh sách)", re.I)


def extract(code: str) -> list[str]:
    f = RAW / code / "can_bo.html"
    if not f.exists():
        return []
    soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    found = []
    for raw in soup.get_text("\n").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if UNIT_RE.match(line) and not SKIP_RE.match(line):
            found.append(line)

    # bo trung do khac dau/hoa-thuong (vd "Khoa Dệt May - Da Giày" vs "Da giầy")
    seen, out = set(), []
    for name in found:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key not in seen:
            seen.add(key)
            out.append(name)
    return sorted(out)


if __name__ == "__main__":
    total = 0
    for info_path in sorted(OUT.glob("*/info.json")):
        code = info_path.parent.name
        depts = extract(code)
        info = json.loads(info_path.read_text(encoding="utf-8"))
        info["departments"] = depts
        info["departments_note"] = (
            "" if depts else
            "Trang cán bộ không liệt kê bộ môn trong HTML (link trỏ thẳng vào 1 bộ môn "
            "hoặc danh sách render bằng JavaScript)"
        )
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {code:6s} {len(depts):2d} bộ môn/đơn vị")
        total += len(depts)
    print(f"\nTổng: {total} đơn vị trên 10 Trường/Khoa")
