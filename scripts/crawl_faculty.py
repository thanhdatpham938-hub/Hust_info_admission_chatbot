"""Crawl thông tin 10 Trường/Khoa từ các link đã chốt trong data/link.md.

Với mỗi đơn vị:
  data/raw/faculty/<code>/*.html   <- bản HTML gốc (truy vết nguồn)
  data/faculty/<code>/gioi_thieu.md <- nội dung giới thiệu đã làm sạch (nguồn RAG)
  data/faculty/<code>/info.json     <- official_channel_url, các link nguồn, program_links

Link được PARSE TRỰC TIẾP từ data/link.md để file link.md luôn là nguồn sự thật duy nhất.

Dùng: python scripts/crawl_faculty.py [ma_truong ...]
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
LINK_MD = ROOT / "data" / "link.md"
RAW_DIR = ROOT / "data" / "raw" / "faculty"
OUT_DIR = ROOT / "data" / "faculty"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HUST-chatbot-data-collector/1.0)"}
TIMEOUT = 25

# Link rác quảng cáo cờ bạc bị chèn vào một số trang hust -> loại bỏ khỏi dữ liệu
SPAM_PATTERN = re.compile(
    r"789win|98win|99ok|b52|kubet|nohu|sunwin|go88|bk8|sv388|sv66|m88|mb66|okvip|"
    r"tk88|w88|ko66|hb88|ga6789|xocdia|68gamebai|tai xiu|game bai",
    re.IGNORECASE,
)

LABELS = {
    "gioi_thieu": "link giới thiệu về trường",
    "can_bo": "link cán bộ của trường",
    "nganh": "link danh sách ngành đào tạo đại học",
    "web": "link web trường",
}


def parse_link_md() -> dict[str, dict]:
    """Đọc data/link.md -> {ma_truong: {ten, web, gioi_thieu, can_bo, nganh}}."""
    units, current = {}, None
    for line in LINK_MD.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*\(([A-Za-z]+)\)\s*:?\s*$", line.strip())
        if heading:
            name, code = heading.group(1).strip(), heading.group(2).lower()
            current = code
            units[code] = {"faculty_code": code, "faculty_name": name}
            continue
        if not current or ":" not in line:
            continue
        url_match = re.search(r"https?://[^\s\)\]]+", line)
        if not url_match:
            continue
        low = line.lower()
        for key, label in LABELS.items():
            if low.startswith(label.lower()):
                units[current].setdefault(key, url_match.group(0).rstrip(".,"))
                break
    return units


def fetch(url: str, attempts: int = 3) -> str | None:
    """Site của một số trường hay timeout lần đầu -> thử lại trước khi bỏ."""
    for attempt in range(1, attempts + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or r.encoding
            return r.text
        except Exception as exc:  # nguồn ngoài -> không để 1 site hỏng chặn cả mẻ
            if attempt == attempts:
                print(f"    [LỖI] {url}: {type(exc).__name__} (sau {attempts} lần thử)")
                return None
            time.sleep(2 * attempt)
    return None


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()

    # Chọn vùng nội dung có NHIỀU CHỮ NHẤT thay vì phần tử đầu tiên khớp:
    # nhiều site hust có <div class="modal-content"> rỗng đứng trước vùng nội dung thật.
    candidates = soup.find_all(["article", "main"]) + soup.find_all(
        class_=re.compile(r"content|entry|post|detail", re.I)
    )
    candidates = [c for c in candidates if c is not None]
    main = max(candidates, key=lambda c: len(c.get_text(strip=True)), default=None)
    if main is None or len(main.get_text(strip=True)) < 200:
        main = soup.body or soup

    lines = []
    for raw in main.get_text("\n").splitlines():
        text = re.sub(r"\s+", " ", raw).strip()
        if len(text) < 2 or SPAM_PATTERN.search(text):
            continue
        if lines and lines[-1] == text:  # bỏ dòng lặp liền nhau
            continue
        lines.append(text)

    # Bỏ khối menu điều hướng đứng đầu: các dòng ngắn liên tiếp trước đoạn văn thực sự đầu tiên.
    first_prose = next((i for i, l in enumerate(lines) if len(l) >= 100), None)
    if first_prose is not None:
        start = first_prose
        while start > 0 and len(lines[start - 1]) >= 40:
            start -= 1  # giữ lại dòng dài vừa đứng ngay trước đoạn văn
        lines = lines[start:]
    return "\n\n".join(lines)


def extract_program_links(html: str, base_url: str) -> list[dict]:
    """Lấy các link trỏ tới trang chương trình đào tạo cụ thể."""
    soup = BeautifulSoup(html, "html.parser")
    keep = re.compile(r"chuong-trinh|nganh|ctdt|dao-tao/.+", re.I)
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        text = re.sub(r"\s+", " ", a.get_text()).strip()
        url = urljoin(base_url, a["href"])
        if not text or len(text) < 6 or SPAM_PATTERN.search(text) or not keep.search(url):
            continue
        if url in seen or url.rstrip("/") == base_url.rstrip("/"):
            continue
        seen.add(url)
        out.append({"title": text, "url": url})
    return out


def crawl(code: str, unit: dict) -> None:
    print(f"  {code.upper()} — {unit.get('faculty_name', '')}")
    raw_dir, out_dir = RAW_DIR / code, OUT_DIR / code
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    info = {
        "faculty_code": code.upper(),
        "faculty_name": unit.get("faculty_name", ""),
        "official_channel_url": unit.get("web", ""),
        "sources": {k: unit[k] for k in ("gioi_thieu", "can_bo", "nganh") if k in unit},
        "program_links": [],
        "collection_date": time.strftime("%Y-%m-%d"),
    }

    if url := unit.get("gioi_thieu"):
        if html := fetch(url):
            (raw_dir / "gioi_thieu.html").write_text(html, encoding="utf-8")
            text = extract_text(html)
            (out_dir / "gioi_thieu.md").write_text(
                f"# Giới thiệu {unit.get('faculty_name', code.upper())}\n\n"
                f"> Nguồn: {url}\n> Thu thập: {info['collection_date']}\n\n{text}\n",
                encoding="utf-8",
            )
            print(f"    gioi_thieu.md ({len(text)} ký tự)")

    if url := unit.get("nganh"):
        if html := fetch(url):
            (raw_dir / "nganh.html").write_text(html, encoding="utf-8")
            info["program_links"] = extract_program_links(html, url)
            print(f"    {len(info['program_links'])} link ngành")

    if url := unit.get("can_bo"):
        if html := fetch(url):
            (raw_dir / "can_bo.html").write_text(html, encoding="utf-8")
            print("    can_bo.html")

    (out_dir / "info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    units = parse_link_md()
    wanted = [c.lower() for c in sys.argv[1:]] or list(units)
    print(f"Đơn vị đọc được từ link.md: {', '.join(u.upper() for u in units)}\n")
    for code in wanted:
        if code in units:
            crawl(code, units[code])
            time.sleep(1)  # lịch sự với server
        else:
            print(f"  [BỎ QUA] không có '{code}' trong link.md")
