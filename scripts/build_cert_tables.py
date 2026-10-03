"""Sinh bang quy doi chung chi ngoai ngu tu 3 nguon (2024 PDF, 2025 anh, 2026 anh).

2 bang RIENG vi tra loi 2 cau hoi khac nhau:
  cert_bonus_conversion.csv - IELTS 6.5 duoc cong may diem thuong? (2024, 2026)
  cert_cefr_equivalence.csv - Chung chi nao tuong duong B2 / Bac 4? (2025)
"""

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "processed"

SRC_2024 = "Đề án tuyển sinh 2024 -FINAL.pdf (Bảng 5-8)"
SRC_2025 = "ts.hust.edu.vn de an 2025 (anh image_2b.png)"
SRC_2026 = "ts.hust.edu.vn de an 2026 (anh quydoi-cccnn-2026.png)"

BONUS_2024 = [
    ("VSTEP", "5,0 - 5,5", 1, "8.50"), ("VSTEP", "6,0 - 6,5", 2, "9.00"),
    ("VSTEP", "7,0", 3, "9.50"), ("VSTEP", "7,5 - 8,0", 4, ""), ("VSTEP", "8,5", 5, ""),
    ("IELTS Academic", "5.0", 1, "8.50"), ("IELTS Academic", "5.5", 2, "9.00"),
    ("IELTS Academic", "6.0", 3, "9.50"), ("IELTS Academic", "6.5", 4, "10.00"),
    ("IELTS Academic", "7.0", 5, ""),
]
EXTRA_2024 = [("VSTEP", "7,0 - 7,5", "", "9.50"), ("VSTEP", "8,0", "", "10.00")]

LEVELS_2026 = [(1, "8.0"), (2, "8.5"), (3, "9.0"), (4, "9.5"), (5, "10")]
CERTS_2026 = {
    "IELTS Academic": ["5.0", "5.5", "6.0", "6.5", "7.0-9.0"],
    "VSTEP": ["5.5", "6.0-6.5", "7.0-7.5", "8.0", "8.5-10"],
    "Aptis Esol": ["80-120", "121-134", "135-148", "149-160", "161-180"],
    "PEIC": ["Level 2", "Level 3 (Pass)", "Level 3 (Pass with Merit)",
             "Level 3 (Pass with Distinction)", "Level 4 - Level 5 (Pass)"],
    "PTE Academic": ["31-38", "39-46", "47-54", "55-62", "63-90"],
    "Linguaskill": ["140-159", "160-166", "167-173", "174-179", "180-210"],
    "Cambridge Assessment English": [
        "B1 Preliminary/B1 Business Preliminary",
        "B2 First/B2 Business Vantage (160-172/Pass at Grade C)",
        "B2 First/B2 Business Vantage (173-179/Pass at Grade B)",
        "B2 First/B2 Business Vantage (180-190/Pass at Grade A)",
        "C1 Advanced/C1 Business Higher (180-210) hoặc C2 Proficiency (200-230)"],
    "Cambridge English Tests": ["PET (140-159)", "FCE (160-166)", "FCE (167-173)",
                                "FCE (174-179)", "CAE (180-199) hoặc CPE (200-230)"],
    "TOEIC Nghe": ["275-395", "400-428", "429-457", "458-485", "490-495"],
    "TOEIC Nói": ["120-150", "160-163", "164-167", "168-170", "180-200"],
    "TOEIC Đọc": ["275-380", "385-406", "407-428", "429-450", "455-495"],
    "TOEIC Viết": ["120-140", "150-156", "157-163", "164-170", "180-200"],
    "TOEFL iBT": ["30-45", "46-61", "62-77", "78-93", "94-120"],
    "TOEFL ITP": ["450-499", "500-541", "542-583", "584-626", "627-677"],
    "DELF/DALF": ["DELF A2 (50-70)", "DELF A2 (71-100)", "DELF B1 (50-70)",
                  "DELF B1 (71-100)", "DELF B2 (50-100) / DALF C1 (50-100) hoặc DALF C2 (50-100)"],
    "TCF": ["200-249", "250-299", "300-349", "350-399", "400-699"],
    "TestDaF": ["", "", "", "TDN3", "TDN4/TDN5"],
    "Goethe/OSD/telc/ECL": ["", "A2", "B1", "B2", "C1/C2"],
    "DSH": ["", "", "", "DSH1", "DSH2/DSH3"],
    "DSD": ["", "", "DSD1", "", "DSD2"],
    "JLPT": ["N4 (145-180)", "N3 (95-120)", "N3 (121-149)", "N3 (150-180)",
             "N2 (90-180) / N1 (100-180)"],
    "HSK": ["HSK3 (241-300)", "HSK4 (180-210)", "HSK4 (211-240)", "HSK4 (241-300)",
            "HSK5 (180-300) / HSK6 (180-300)"],
    "HSKK": ["HSKK Sơ cấp (60-100)", "HSKK Trung cấp (60-100)", "HSKK Trung cấp (60-100)",
             "HSKK Trung cấp (60-100)", "HSKK Cao cấp (60-100)"],
    "TOPIK": ["TOPIK 3 (135-149)", "TOPIK 4 (150-162)", "TOPIK 4 (163-175)",
              "TOPIK 4 (176-189)", "TOPIK 5 (190-229) / TOPIK 6 (230-300)"],
}
NOTE_2026 = "Voi TOEIC, diem thuong va diem quy doi la trung binh cong cua 4 ky nang Nghe, Noi, Doc, Viet"

CEFR_2025 = [
    ("Bậc 3", "B1", {
        "IELTS Academic": "5,0", "VSTEP": "5.5", "Aptis ESOL": "B1", "PEIC": "Level 2",
        "PTE Academic": "43-58", "Linguaskill": "140-159",
        "Cambridge Assessment English": "B1 Preliminary/B1 Business Preliminary",
        "Cambridge English Tests": "PET (140-159)", "TOEIC Nghe": "275-395",
        "TOEIC Đọc": "275-380", "TOEIC Nói": "120-150", "TOEIC Viết": "120-140",
        "TOEFL iBT": "30-45", "TOEFL ITP": "450-499"}),
    ("Bậc 4", "B2", {
        "IELTS Academic": "5,5 - 6,5", "VSTEP": "6.0-6.5 / 7.0-7.5 / 8.0",
        "Aptis ESOL": "B2", "PEIC": "Level 3", "PTE Academic": "59-75",
        "Linguaskill": "160-179",
        "Cambridge Assessment English": "B2 First/B2 Business Vantage",
        "Cambridge English Tests": "FCE (160-179)", "TOEIC Nghe": "400-485",
        "TOEIC Đọc": "385-450", "TOEIC Nói": "160-170", "TOEIC Viết": "150-170",
        "TOEFL iBT": "46-93"}),
    ("Bậc 5", "C1", {
        "IELTS Academic": "7,0 - 8,0", "VSTEP": "8.5 / 9.0 / 9.5-10",
        "Aptis ESOL": "C1", "PEIC": "Level 4", "PTE Academic": "76-84",
        "Linguaskill": ">180",
        "Cambridge Assessment English": "C1 Advanced/C1 Business Higher",
        "Cambridge English Tests": "CAE (180-199)", "TOEIC Nghe": "490",
        "TOEIC Đọc": "455", "TOEIC Nói": "180-200", "TOEIC Viết": "180-200",
        "TOEFL iBT": "94-114"}),
    ("Bậc 6", "C2", {
        "IELTS Academic": "8,5 - 9,0", "Aptis ESOL": "C2", "PEIC": "Level 5",
        "PTE Academic": "85-90",
        "Cambridge Assessment English": "C2 Proficiency",
        "Cambridge English Tests": "CPE (200-230)", "TOEFL iBT": "115-120"}),
]


def write(rows, name):
    path = OUT / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  {path.name}: {len(rows)} dong")


if __name__ == "__main__":
    bonus = []
    for cert, value, point, conv in BONUS_2024 + EXTRA_2024:
        bonus.append({"year": 2024, "certificate": cert, "cert_value": value,
                      "bonus_point": point, "converted_score_10": conv, "note": "",
                      "source": SRC_2024, "verification_status": "text_extracted"})
    for cert, values in CERTS_2026.items():
        for (point, conv), value in zip(LEVELS_2026, values):
            if not value:
                continue
            bonus.append({"year": 2026, "certificate": cert, "cert_value": value,
                          "bonus_point": point, "converted_score_10": conv,
                          "note": NOTE_2026 if cert.startswith("TOEIC") else "",
                          "source": SRC_2026, "verification_status": "vision_extracted"})
    write(bonus, "cert_bonus_conversion.csv")

    cefr = []
    for vn_level, cefr_level, certs in CEFR_2025:
        for cert, value in certs.items():
            cefr.append({"year": 2025, "certificate": cert, "cert_value": value,
                         "cefr_level": cefr_level, "knlnn_vn_level": vn_level,
                         "source": SRC_2025, "verification_status": "vision_extracted"})
    write(cefr, "cert_cefr_equivalence.csv")
