"""Them cot MON CHINH vao subject_combinations_2026.csv + tao bang cong thuc tinh diem.

Van de: de an 2026 chi ghi "8 to hop xet tuyen va mon chinh" va bai diem chuan 2026 cho
cong thuc "to hop co mon chinh la Toan", nhung KHONG nguon chinh thuc nao noi nganh nao ap
dung mon chinh (de an 2024 dan sang Phu luc 1 nhung file PDF khong kem phu luc).

Nguon mon chinh: bang "Danh sach nganh dao tao BKA theo phuong thuc diem thi tot nghiep THPT
2026" tren tuyensinh247.com (BEN THU BA, luu tai data/raw/mon_chinh/tuyensinh247_BKA.html).
Theo yeu cau, link nay KHONG dua vao danh sach nguon (docs/nguon_du_lieu.md) va chatbot
khong trich dan no; cot main_subject_status = "third_party" de phan biet voi du lieu chinh thuc.

Doi chieu truoc khi dung (2026-09-26):
- Danh sach to hop THPT khop voi 68 trang nganh chinh thuc o 67/68 nganh (chi TROY-IT lech:
  trang chinh thuc co them D01, bang ben thu ba khong co -> de "chua_ro").
- Bang ben thu ba co them B03, C01, C02, X02 — KHONG thuoc 8 to hop cua de an 2026 -> bo qua.
- Bang ben thu ba khong co K01 — K01 co cong thuc rieng nen khong can mon chinh.

Neu chay lai verify_subject_combinations.py --write thi phai chay lai script nay.

Dung: python scripts/add_main_subject.py
"""

import csv
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "mon_chinh" / "tuyensinh247_BKA.html"
COMBOS = PROCESSED / "subject_combinations_2026.csv"
FORMULAS = PROCESSED / "scoring_formulas_2026.csv"

OFFICIAL_2026 = {"K01", "A00", "A01", "B00", "D01", "D04", "D07", "DD2"}
THIRD_PARTY_NOTE = "tuyensinh247.com (bên thứ ba), bảng ngành theo phương thức THPT 2026"
NEW_COLS = ["main_subject", "formula_type", "main_subject_source", "main_subject_status"]

# Nguyen van muc "Huong dan cach xac dinh Diem Xet Tuyen (DX)" trong bai diem chuan 2026
SCORE_URL = "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026"
FORMULA_ROWS = [
    ("khong_mon_chinh", "THPT", 30, "ĐX = (Môn 1 + Môn 2 + Môn 3) + Điểm ưu tiên",
     "Tổ hợp không có môn chính"),
    ("mon_chinh_toan", "THPT", 30, "ĐX = [(Môn 1 + Môn 2 + Môn 3 + Môn chính) x 3/4] + Điểm ưu tiên",
     "Tổ hợp có môn chính là Toán (Toán được tính 2 lần)"),
    ("K01", "THPT", 30, "ĐX = [(Toán x 3 + Ngữ Văn x 1 + Lý/Hóa/Sinh/Tin x 2) x 1/2] + Điểm ưu tiên",
     "Tổ hợp K01"),
    ("DGTD", "DGTD", 100, "ĐX = (Điểm thi ĐGTD + Điểm thưởng) + Điểm ưu tiên",
     "Điểm ĐGTD là điểm cao nhất các lần thi 2025 và 2026; điểm thưởng cho chứng chỉ IELTS (Academic) "
     "hoặc tương đương theo QĐ 4740/QĐ-ĐHBK; điểm ưu tiên quy về thang 100"),
    ("XTTN", "XTTN", 100, "ĐX = Điểm XTTN + Điểm ưu tiên",
     "Xét tuyển tài năng diện 1.2 và 1.3; điểm ưu tiên quy về thang 100"),
    ("chua_ro", "THPT", 30, "",
     "Nguồn không cho biết tổ hợp này có môn chính hay không — chatbot phải nói rõ là chưa xác định"),
]


def third_party_table() -> dict[str, dict[str, str]]:
    """{program_code: {combination_code: 'Toán' | ''}} chi voi 8 to hop chinh thuc."""
    soup = BeautifulSoup(RAW.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    head = soup.find(string=lambda s: s and "phương thức điểm thi tốt nghiệp THPT 2026" in s)
    table = head.find_next("table")
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        code = cells[0].replace(" ", "")          # "BF - E12" -> "BF-E12"
        main = "Toán" if "Toán là môn chính" in cells[3] else ""
        for combo in (c.strip() for c in cells[2].split(";")):
            if combo in OFFICIAL_2026:
                out[code][combo] = main
    return out


def formula_type(method: str, combo: str, known: dict[str, str]) -> tuple[str, str, str]:
    """-> (main_subject, formula_type, status)"""
    if method == "DGTD":
        return "", "DGTD", ""
    if combo == "K01":
        return "", "K01", ""
    if combo not in known:
        return "", "chua_ro", "not_found"
    main = known[combo]
    return main, ("mon_chinh_toan" if main else "khong_mon_chinh"), "third_party"


def main() -> None:
    tp = third_party_table()
    rows = list(csv.DictReader(COMBOS.open(encoding="utf-8-sig", newline="")))
    base_cols = [c for c in rows[0].keys() if c not in NEW_COLS]
    stats = defaultdict(int)
    for r in rows:
        main_subj, ftype, status = formula_type(r["method_code"], r["combination_code"],
                                                tp.get(r["program_code"], {}))
        r["main_subject"], r["formula_type"], r["main_subject_status"] = main_subj, ftype, status
        r["main_subject_source"] = THIRD_PARTY_NOTE if status == "third_party" else ""
        stats[ftype] += 1
    with COMBOS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=base_cols + NEW_COLS)
        w.writeheader()
        w.writerows(rows)

    with FORMULAS.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["formula_type", "method_code", "scale", "formula", "note", "year",
                    "source_url", "verification_status"])
        for ftype, method, scale, formula, note in FORMULA_ROWS:
            src = SCORE_URL if ftype != "chua_ro" else ""
            status = "html_parsed" if ftype != "chua_ro" else "rule_derived"
            w.writerow([ftype, method, scale, formula, note, 2026, src, status])

    print(f"{COMBOS.name}: {len(rows)} dòng | " + ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    unknown = [(r["program_code"], r["combination_code"]) for r in rows if r["formula_type"] == "chua_ro"]
    print(f"  chưa rõ môn chính: {unknown}")
    print(f"{FORMULAS.name}: {len(FORMULA_ROWS)} dòng")


if __name__ == "__main__":
    main()
