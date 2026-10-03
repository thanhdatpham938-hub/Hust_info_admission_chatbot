"""Bo sung 6 cot metadata chuan cho moi bang trong data/processed/ (PLAN - Metadata Design v2, muc 6).

Cot chuan (dat cuoi bang, thu tu co dinh): year, source, source_url, collection_date,
verification_status, dataset_version.

Nguyen tac:
- CHI DIEN O TRONG, khong ghi de gia tri da co — tru mot truong hop duoc ghi ro ben duoi
  (source_url cua bang to hop dang tro trang danh muc chung thay vi trang tung nganh).
- `source` = nhan nguoi doc ("De an tuyen sinh 2024 - Bang 9"), `source_url` = link bam duoc.
  Truoc day hai cot dung thay nhau; nay ca 3 PDF noi bo da co link nen moi bang deu dien du.
- Bang tra cuu tu lap (entity_aliases, program_aliases) khong phai du lieu nguon -> chi them
  dataset_version.

Chay LAI script nay sau moi lan chay lai mot script bong du lieu (chung ghi de CSV va lam mat
cac cot bo sung). Idempotent: chay nhieu lan cho cung ket qua.

Dung: python scripts/normalize_csv_meta.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
DATASET_VERSION = "2026.1"
STD = ["year", "source", "source_url", "collection_date", "verification_status", "dataset_version"]
LOOKUP_TABLES = {"entity_aliases", "program_aliases"}

URL = {
    "dean2024": "https://ts.hust.edu.vn/tin-tuc/de-an-tuyen-sinh-dai-hoc-nam-2024",
    "dean2025": "https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025",
    "dean2026": "https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026",
    "dc2024": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53",
    "dc2025": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa",
    "dc2026": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026",
    "hocphi2024": "https://ctt.hust.edu.vn/Upload/Nguyen%20Quoc%20Dat/files/DTDH_QDQC/Hocphi/2024-2025/2024_2_%20Q%C4%90%20h%E1%BB%8Dc%20ph%C3%AD%20-%202024-2025.pdf",
}
PROGRAM_INDEX = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/"
DEAN = {2024: "dean2024", 2025: "dean2025", 2026: "dean2026"}
# ngay luu file goc cua tung nguon (giong normalize_chunks.py)
COLLECTED = {"dean2024": "2026-09-19", "dean2025": "2026-09-21", "dean2026": "2026-09-21",
             "dc": "2026-09-22", "hocphi2024": "2026-09-20", "program_pages": "2026-09-23"}


def program_page_url() -> dict[str, str]:
    rows = csv.DictReader((PROCESSED / "program_overview_2026.csv").open(encoding="utf-8-sig"))
    return {r["program_code"]: r["source_url"] for r in rows}


def defaults(table: str, row: dict, pages: dict) -> dict:
    """Gia tri mac dinh cho cot con trong cua mot dong. Moi nhanh ghi can cu nguon."""
    y = int(row["year"]) if str(row.get("year", "")).strip() else None
    t = table
    if t.startswith("admission_scores_"):
        return {"source": f"Bài công bố điểm chuẩn {y} (ts.hust.edu.vn)"}
    if t.startswith("program_methods_") or t.startswith("quotas_"):
        return {"source": f"Đề án tuyển sinh {y} — bảng danh mục chương trình"}
    if t.startswith("programs_"):
        key = {2024: "dc2024", 2025: "dc2025", 2026: "dean2026"}[y]
        return {"source_url": URL[key],
                "collection_date": COLLECTED["dean2026" if y == 2026 else "dc"],
                # 2024/2025: doc tu anh bang diem chuan; 2026: doi chieu voi bang HTML de an 2026
                "verification_status": "html_parsed" if y == 2026 else "vision_extracted"}
    if t == "program_overview_2026":
        return {"source": "Trang giới thiệu ngành trên ts.hust.edu.vn — mục Thông tin nhanh"}
    if t == "subject_combinations_2026":
        return {"source": "Trang giới thiệu ngành trên ts.hust.edu.vn — mục Tổ hợp xét tuyển"}
    if t == "subject_combinations_ref":
        return {"source": "Đề án tuyển sinh 2025/2026 — danh sách tổ hợp"}
    if t == "scoring_formulas_2026":
        return {"source": "Bài công bố điểm chuẩn 2026 — Hướng dẫn cách xác định Điểm Xét",
                "collection_date": COLLECTED["dc"]}
    if t in ("admission_fees", "tuition_by_year"):
        return {"source_url": URL["dean2024"], "collection_date": COLLECTED["dean2024"]}
    if t == "tuition_credit":
        return {"source_url": URL["hocphi2024"], "collection_date": COLLECTED["hocphi2024"]}
    if t in ("cert_bonus_conversion", "cert_cefr_equivalence"):
        key = DEAN[y]
        return {"source_url": URL[key], "collection_date": COLLECTED[key]}
    return {}


def fix_existing(table: str, row: dict, pages: dict) -> None:
    """Ngoai le duy nhat duoc ghi de: bang to hop ghi source_url la trang DANH MUC chung ->
    doi sang trang cua dung nganh (to hop duoc boc tu trang tung nganh, co trong
    program_overview_2026.csv) de citation dan dung trang."""
    if table == "subject_combinations_2026" and row.get("source_url") == PROGRAM_INDEX:
        row["source_url"] = pages[row["program_code"]]


def main() -> None:
    pages = program_page_url()
    for path in sorted(PROCESSED.glob("*.csv")):
        table = path.stem
        rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
        cols = list(rows[0].keys())
        std = ["dataset_version"] if table in LOOKUP_TABLES else STD
        filled = {c: 0 for c in std}
        for r in rows:
            fix_existing(table, r, pages)
            d = defaults(table, r, pages)
            for c in std:
                if not str(r.get(c) or "").strip():
                    v = DATASET_VERSION if c == "dataset_version" else d.get(c, "")
                    if v:
                        r[c] = v
                        filled[c] += 1
                    else:
                        r.setdefault(c, "")
        base = [c for c in cols if c not in std]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=base + std)
            w.writeheader()
            w.writerows(rows)
        missing = {c: sum(1 for r in rows if not str(r.get(c) or "").strip()) for c in std}
        miss = {c: n for c, n in missing.items() if n}
        print(f"  {table:34s} {len(rows):4d} dòng | điền: "
              + ", ".join(f"{c}={n}" for c, n in filled.items() if n)
              + (f" | CÒN TRỐNG: {miss}" if miss else ""))


if __name__ == "__main__":
    main()
