"""Bang 2.1 - quy doi tuong duong chung chi tieng Anh (chuan NGOAI NGU DAU RA).

Nguon: Quy dinh ngoai ngu K71, so 10828/QD-DHBK ngay 07/9/2026, Phu luc II, trang 8.
Doc bang vision tu anh render (data/raw/tuition/ngoaingu_p8_bang21.png) vi bang co
14 cot, lop text cua PDF tra ve cac o LECH COT nen khong dung duoc.

PHAN BIET voi cert_bonus_conversion.csv: bang do la DIEM THUONG KHI XET TUYEN
(thi sinh lop 12). Bang nay la QUY DOI BAC NANG LUC de xet CHUAN DAU RA khi tot
nghiep. Hai bang khac muc dich, khac gia tri, tuyet doi khong dung lan nhau.

Dung: python scripts/build_cert_equivalence_2026.py
"""

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "cert_equivalence_output_2026.csv"
SOURCE = "Quy định ngoại ngữ K71 - 10828/QĐ-ĐHBK ngày 07/9/2026, Phụ lục II, Bảng 2.1 (trang 8)"
SOURCE_URL = "https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=51634"

# Thu tu cot dung nhu tren ban goc. "" = o gach cheo (chung chi do khong co muc nay).
COLUMNS = ["CEFR", "VSTEP", "APTIS ESOL", "IELTS Academic", "PEIC", "PTE Academic",
           "VEPT", "LanguageCert Academic", "Oxford Test of English (OTE)", "Linguaskill",
           "Cambridge Assessment English", "Cambridge English Tests",
           "TOEIC Nghe", "TOEIC Đọc", "TOEIC Nói", "TOEIC Viết", "TOEFL iBT", "TOEFL ITP"]

# (bac_nhom, bac_chi_tiet, [gia tri theo thu tu COLUMNS])
ROWS = [
    ("Bậc 1", "Bậc 1.1", ["A1", "", "A1", "2.0", "Level A1", "10÷19", "10÷19", "10÷14",
                          "21÷35", "100÷110", "", "KET (100÷110)",
                          "60÷80", "60÷80", "50÷60", "30÷40", "12÷14", "338÷350"]),
    ("Bậc 1", "Bậc 1.2", ["A1", "", "A1", "2.5", "Level A1", "20÷29", "20÷29", "15÷19",
                          "36÷50", "111÷119", "", "KET (111÷119)",
                          "85÷105", "85÷110", "70÷80", "50÷60", "15÷16", "351÷360"]),
    ("Bậc 2", "Bậc 2.1", ["A2", "", "A2", "3.0", "Level 1", "30÷33", "30÷33", "20÷29",
                          "51÷60", "120÷126", "A2 KEY", "KET (120÷139)",
                          "110÷165", "115÷170", "90", "70÷80", "17÷21", "361÷399"]),
    ("Bậc 2", "Bậc 2.2", ["A2", "", "A2", "3.5", "Level 1", "34÷38", "34÷38", "30÷35",
                          "61÷70", "127÷133", "A2 KEY", "KET (120÷139)",
                          "170÷215", "175÷215", "100", "90÷100", "22÷25", "400÷429"]),
    ("Bậc 2", "Bậc 2.3", ["A2", "", "A2", "3.5", "Level 1", "39÷42", "39÷42", "36÷39",
                          "71÷80", "134÷139", "A2 KEY", "KET (120÷139)",
                          "220÷270", "220÷270", "110", "110", "26÷29", "430÷449"]),
    ("Bậc 3", "Bậc 3.1", ["B1", "4.0÷4.5", "B1", "4.0÷4.5", "Level 2", "43÷50", "43÷66", "40÷49",
                          "81÷95", "140÷149", "B1 Preliminary/B1 Business Preliminary",
                          "PET (140÷149)",
                          "275÷330", "275÷330", "120÷130", "120÷130", "30÷37", "450÷470"]),
    ("Bậc 3", "Bậc 3.2", ["B1", "5.0÷5.5", "B1", "5.0", "Level 2", "51÷58", "67÷90", "50÷59",
                          "96÷110", "150÷159", "B1 Preliminary/B1 Business Preliminary",
                          "PET (150÷159)",
                          "335÷395", "335÷380", "140÷150", "140", "38÷45", "471÷499"]),
    ("Bậc 4", "Bậc 4", ["B2", "6.0÷8.0", "B2", "5.5÷6.5", "Level 3", "59÷75", "", "60÷74",
                        "111÷140", "160÷179", "B2 First/B2 Business Vantage", "FCE (160÷179)",
                        "400÷485", "385÷450", "160÷170", "150÷170", "46÷93", "500÷626"]),
    ("Bậc 5", "Bậc 5", ["C1", "8.5÷10", "C1", "7.0÷8.0", "Level 4", "76÷84", "", "75÷89",
                        "141÷170 (OTE Advanced)", "180÷199",
                        "C1 Advanced/C1 Business Higher", "CAE (180÷199)",
                        "490÷495", "455÷495", "180÷200", "180÷200", "94÷114", "627÷677"]),
]

# O gop tren ban goc -> ghi chu de nguoi doc biet gia tri nay dung chung cho nhieu bac
MERGED_NOTE = {
    ("Bậc 2.2", "IELTS Academic"): "Ô gộp: mức 3.5 áp dụng chung cho Bậc 2.2 và Bậc 2.3",
    ("Bậc 2.3", "IELTS Academic"): "Ô gộp: mức 3.5 áp dụng chung cho Bậc 2.2 và Bậc 2.3",
    ("Bậc 2.1", "Cambridge English Tests"): "Ô gộp: KET (120÷139) áp dụng cho cả Bậc 2.1–2.3",
    ("Bậc 2.2", "Cambridge English Tests"): "Ô gộp: KET (120÷139) áp dụng cho cả Bậc 2.1–2.3",
    ("Bậc 2.3", "Cambridge English Tests"): "Ô gộp: KET (120÷139) áp dụng cho cả Bậc 2.1–2.3",
}

FIELDNAMES = ["level_group", "level", "certificate", "cert_value", "note", "year",
              "source", "source_url", "collection_date", "verification_status", "dataset_version"]


def main() -> None:
    today = date.today().isoformat()
    rows = []
    for group, level, values in ROWS:
        assert len(values) == len(COLUMNS), f"{level}: {len(values)} giá trị / {len(COLUMNS)} cột"
        for col, val in zip(COLUMNS, values):
            if not val:
                continue  # ô gạch chéo: chứng chỉ này không có mức tương đương ở bậc đó
            rows.append({
                "level_group": group, "level": level, "certificate": col, "cert_value": val,
                "note": MERGED_NOTE.get((level, col), ""), "year": 2026,
                "source": SOURCE, "source_url": SOURCE_URL, "collection_date": today,
                "verification_status": "vision_extracted", "dataset_version": "2026.1",
            })
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"{OUT.name}: {len(rows)} dòng / {len(ROWS)} bậc × {len(COLUMNS)} loại chứng chỉ")
    b3 = [r for r in rows if r["level_group"] == "Bậc 3"]
    print(f"\nBậc 3 (= chuẩn đầu ra CTĐT chuẩn), {len(b3)} dòng — vài mức hay được hỏi:")
    for r in b3:
        if r["certificate"] in ("IELTS Academic", "TOEIC Nghe", "TOEIC Đọc", "VSTEP", "TOEFL iBT"):
            print(f"   {r['level']:9s} {r['certificate']:14s} {r['cert_value']}")


if __name__ == "__main__":
    main()
