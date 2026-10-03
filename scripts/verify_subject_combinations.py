"""Boc to hop xet tuyen tu 68 trang nganh va DOI CHIEU voi bang dang co.

Bang subject_combinations_2026.csv truoc day boc tu trang accordion tong hop.
Trang tung nganh la nguon thu hai, doc lap — dung de kiem chinh bang cu va bo
sung cho du. Da phat hien bang cu thieu ma DD2 (Toan, Ngu van, Tieng Han) cua
nganh FL4, trong khi de an 2026 ghi ro nam 2026 co 8 to hop gom DD2.

Trang nganh ghi to hop trong div.meta, moi dong mot phuong thuc:
    "Xet tuyen theo KQ Ky thi TN THPT: | To hop xet tuyen: D01 D01 : Toan, Anh van,
     Ngu van K01 K01 : Toan, Ly/Hoa/Sinh/Tin, Ngu van | Diem chuan:"
Ma to hop bi lap 2 lan lien tiep (mot lan la nhan, mot lan la tooltip).

Dung: python scripts/verify_subject_combinations.py [--write]
"""

import csv
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "program_pages"
PROCESSED = ROOT / "data" / "processed"
YEAR = 2026
SOURCE_TMPL = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/"

METHOD_BY_LABEL = {"ĐGTD": "DGTD", "TN THPT": "THPT"}
# "D01 D01 : Toan, Anh van, Ngu van" -> ma lap 2 lan roi moi den ten mon
PAIR = re.compile(r"([A-Z]{1,3}\d{1,2})\s+\1\s*:\s*(.+?)(?=[A-Z]{1,3}\d{1,2}\s+[A-Z]{1,3}\d{1,2}\s*:|$)")


def parse_page(path: Path) -> dict[str, dict[str, str]]:
    """{method_code: {combination_code: ten cac mon}}"""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    meta = soup.find(class_="meta")
    out: dict[str, dict[str, str]] = {}
    if not meta:
        return out
    for row in meta.find_all(class_="row", recursive=False):
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True))
                 for c in row.find_all("div", recursive=False)]
        if not cells:
            continue
        method = next((m for lab, m in METHOD_BY_LABEL.items() if lab in cells[0]), None)
        if not method:
            continue
        body = " ".join(cells[1:])
        # Cell cuoi cua dong la "Diem chuan:" -> dinh vao ten mon cua ma cuoi cung
        found = {code: re.split(r"Điểm chuẩn", subjects)[0].strip(" ,;:")
                 for code, subjects in PAIR.findall(body)}
        if found:
            out[method] = found
    return out


def main() -> int:
    write = "--write" in sys.argv
    pages = sorted(RAW.glob("*.html"))
    fresh: dict[tuple[str, str], dict[str, str]] = {}
    subjects_of: dict[str, str] = {}
    for p in pages:
        code = p.stem
        for method, combos in parse_page(p).items():
            for comb, subj in combos.items():
                fresh[(code, method)] = fresh.get((code, method), {})
                fresh[(code, method)][comb] = subj
                subjects_of.setdefault(comb, subj)

    old = defaultdict(set)
    old_path = PROCESSED / f"subject_combinations_{YEAR}.csv"
    for r in csv.DictReader(old_path.open(encoding="utf-8", newline="")):
        old[(r["program_code"], r["method_code"])].add(r["combination_code"])

    new = {k: set(v) for k, v in fresh.items()}
    print(f"Boc tu {len(pages)} trang nganh: {sum(len(v) for v in new.values())} dong "
          f"(bang cu: {sum(len(v) for v in old.values())} dong)")
    print(f"Ma to hop tim thay: {', '.join(sorted(subjects_of))}")

    only_new, only_old = [], []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key, set()), new.get(key, set())
        if b - a:
            only_new.append((key, sorted(b - a)))
        if a - b:
            only_old.append((key, sorted(a - b)))

    print(f"\nTrang nganh CO ma bang cu THIEU: {len(only_new)} truong hop")
    for (code, method), diff in only_new:
        print(f"    {code:9s} {method:6s} thieu {diff}")
    print(f"\nBang cu CO ma trang nganh KHONG co: {len(only_old)} truong hop")
    for (code, method), diff in only_old:
        print(f"    {code:9s} {method:6s} thua  {diff}")

    if not write:
        print("\n(chay lai voi --write de ghi bang moi)")
        return 0

    rows = []
    today = date.today().isoformat()
    for (code, method), combos in sorted(fresh.items()):
        for comb in sorted(combos):
            rows.append({"program_code": code, "year": YEAR, "method_code": method,
                         "combination_code": comb, "language": "",
                         "source_url": f"{SOURCE_TMPL}", "collection_date": today,
                         "verification_status": "web_extracted"})
    with old_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nDa ghi {old_path.name}: {len(rows)} dong")

    ref_path = PROCESSED / "subject_combinations_ref.csv"
    ref = list(csv.DictReader(ref_path.open(encoding="utf-8", newline="")))
    have = {r["combination_code"] for r in ref}
    added = 0
    for comb, subj in sorted(subjects_of.items()):
        if comb not in have:
            ref.append({"combination_code": comb, "subjects": subj,
                        "source_url": SOURCE_TMPL, "collection_date": today,
                        "verification_status": "web_extracted"})
            added += 1
    if added:
        with ref_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ref[0].keys()))
            w.writeheader()
            w.writerows(ref)
        print(f"Da bo sung {added} ma vao {ref_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
