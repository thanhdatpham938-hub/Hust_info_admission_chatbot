"""Lay mo ta ngan + curriculum_url cho tung nganh -> data/programs/<code>.json.

Nguon: cac link nganh da crawl o buoc truoc (data/faculty/<code>/info.json).
Ghep link voi ma nganh bang 2 cach:
  1) ma nganh xuat hien ngay trong tieu de/URL (vd "... (ma tuyen sinh: IT1)")
  2) khop ten nganh da chuan hoa voi bang programs_2026.csv

PRD muc 4.7: MVP chi can mo ta ngan 1-2 cau; hoi sau hon thi tra curriculum_url.

Dung: python scripts/crawl_programs.py
"""

import csv
import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FACULTY_DIR = ROOT / "data" / "faculty"
OUT_DIR = ROOT / "data" / "programs"
PROGRAMS_CSV = ROOT / "data" / "processed" / "programs_2026.csv"
# Ma Khoa lay theo faculty_name cua danh muc nganh, KHONG theo trang Khoa nao co link toi nganh:
# cach cu gan TE1 -> FED (trang FED co link trung ten) va bo trong TROY-IT (khong trang Khoa nao
# link toi). Sua 2026-10-04, PLAN - Data Linking L1.
FACULTY_CODE = {
    r["faculty_name"]: r["faculty_code"]
    for r in csv.DictReader((ROOT / "data" / "processed" / "linking" / "faculties.csv").open(encoding="utf-8"))
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HUST-chatbot-data-collector/1.0)"}
SPAM = re.compile(r"789win|98win|99ok|b52|kubet|nohu|sunwin|go88|bk8|sv388|m88|okvip", re.I)


# Website cac truong goi chuong trinh tien tien bang nhieu ten khac nhau:
# "ELITECH", "CTTT", "CT tien tien" -> quy ve mot tu de khop duoc voi nhau.
# Website cac truong goi chuong trinh tien tien bang nhieu ten khac nhau:
# "ELITECH", "CTTT", "CT tien tien" -> quy ve mot token de khop duoc voi nhau.
# Khop tren chuoi da dem khoang trang, KHONG dung \b (tung bi bien thanh ky tu
# backspace vo hinh khi ghi file, lam regex im lang khong khop gi).
SYNONYMS = [
    (["elitech", "cttt", "ct tien tien", "chuong trinh tien tien"], "tientien"),
    (["ctdt", "chuong trinh dao tao"], "ctdt"),
]


def normalize(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower().replace("đ", "d"))  # "đ" khong phai to hop
    #  dau nen NFD khong tach ra; khong doi thanh "d" truoc thi buoc loc [^a-z0-9]
    #  se XOA han no: "dang ky" -> "ang ky", "diem" -> "iem". Hau qua: nguoi dung go
    #  khong dau ("dien tu vien thong") se khong khop voi ten nganh da chuan hoa.
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    padded = f" {t} "
    for variants, rep in SYNONYMS:
        for v in variants:
            padded = padded.replace(f" {v} ", f" {rep} ")
    return padded.strip()


def load_programs() -> list[dict]:
    with PROGRAMS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def match_code(title: str, url: str, programs: list[dict]) -> tuple[str | None, float]:
    """Tim ma nganh cho mot link CTDT, tra ve (ma, diem tin cay).

    Nhieu nganh trung phan ten goc ("Cong nghe thong tin (Viet - Nhat)" vs
    "(Global ICT)" vs "(Viet - Phap)"), nen phai cham diem tren TOAN BO ten
    thay vi lay ket qua khop dau tien.
    """
    haystack = f"{title} {url}".upper()
    # 1) ma nganh xuat hien nguyen ven -> chac chan nhat (uu tien ma dai truoc)
    for p in sorted(programs, key=lambda x: -len(x["program_code"])):
        code = p["program_code"].upper()
        if re.search(rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9-])", haystack):
            return p["program_code"], 1.0

    # 2) Cham diem theo ten nganh. Uu tien SO TOKEN KHOP TUYET DOI truoc, roi moi
    # den ti le: ten ngan nhu "Ky thuat O to" sau chuan hoa chi con 1 token co
    # nghia ("thuat"), neu chi xet ti le thi moi tieu de chua "thuat" deu khop 1.0.
    text_tokens = set(normalize(f"{title} {url}").split())
    best, best_key = None, (0, 0.0)
    for p in programs:
        tokens = {t for t in normalize(p["program_name"]).split() if len(t) > 2}
        if len(tokens) < 2:
            continue  # ten qua ngan -> khong du dac trung de khop an toan
        hit = tokens & text_tokens
        key = (len(hit), len(hit) / len(tokens))
        if key > best_key:
            best, best_key = p["program_code"], key
    return (best, best_key[1]) if best_key[1] >= 0.6 else (None, best_key[1])


def short_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    for para in soup.find_all("p"):
        text = re.sub(r"\s+", " ", para.get_text()).strip()
        if len(text) >= 120 and not SPAM.search(text):
            sentences = re.split(r"(?<=[.!?])\s+", text)
            return " ".join(sentences[:2]).strip()[:600]
    return ""


if __name__ == "__main__":
    programs = load_programs()
    by_code = {p["program_code"]: p for p in programs}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    resolved: dict[str, dict] = {}
    for info_path in sorted(FACULTY_DIR.glob("*/info.json")):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        for link in info.get("program_links", []):
            code, score = match_code(link["title"], link["url"], programs)
            if code and score > resolved.get(code, {}).get("score", 0):
                resolved[code] = {
                    "faculty_code": info["faculty_code"],
                    "title": link["title"],
                    "url": link["url"],
                    "score": score,
                }

    print(f"Ghep duoc {len(resolved)}/{len(programs)} ma nganh voi trang CTDT\n")

    for code, link in sorted(resolved.items()):
        desc = ""
        try:
            r = requests.get(link["url"], headers=HEADERS, timeout=25)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding
            desc = short_description(r.text)
        except Exception as exc:
            print(f"  [LOI] {code}: {type(exc).__name__}")

        (OUT_DIR / f"{code}.json").write_text(
            json.dumps(
                {
                    "program_code": code,
                    "program_name": by_code[code]["program_name"],
                    "faculty_code": FACULTY_CODE[by_code[code]["faculty_name"]],
                    "faculty_name": by_code[code]["faculty_name"],
                    "short_description": desc,
                    "curriculum_url": link["url"],
                    "source_title": link["title"],
                    "collection_date": time.strftime("%Y-%m-%d"),
                },
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"  {code:10s} {'OK ' if desc else 'trong'} {len(desc):4d} ky tu")
        time.sleep(0.5)

    missing = [p["program_code"] for p in programs if p["program_code"] not in resolved]
    if missing:
        print(f"\nChua ghep duoc ({len(missing)}): {', '.join(missing)}")
