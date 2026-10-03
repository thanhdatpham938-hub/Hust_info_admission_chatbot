"""Crawl cac trang tuyen sinh le (ngoai nhom 10 Truong/Khoa) -> RAG.

Hien tai: trang gioi thieu ky thi TSA (ban TIENG VIET) va Cam nang thi TSA.
Uu tien ban tieng Viet theo pham vi ngon ngu PRD muc 4.6; ban EN chi dung
khi khong co ban VI.
"""

import json
import re
import subprocess
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pages"
OUT = ROOT / "data" / "rag" / "raw_chunks"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HUST-chatbot-data-collector/1.0)"}
SPAM = re.compile(r"789win|98win|99ok|b52|kubet|nohu|sunwin|go88|bk8|sv388|m88|okvip|tk88|w88", re.I)
TARGET, MIN_CHUNK = 1200, 200

PAGES = [
    # LUU Y: duong dan "/en/" tren ts.hust.edu.vn KHONG co nghia la ban tieng Anh.
    # Bai o /index.php/en/...gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa la mot BAI KHAC
    # (noi dung tieng Viet, 4.676 ky tu), khong phai ban dich cua bai VI cung slug.
    {"slug": "tsa_gioi_thieu", "title": "Giới thiệu về Kỳ thi Đánh giá tư duy (TSA)",
     "type": "tsa_gioi_thieu",
     "url": "https://ts.hust.edu.vn/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa"},
    {"slug": "tsa_phuong_thuc_xet_tuyen", "title": "Kỳ thi Đánh giá tư duy của ĐH Bách khoa Hà Nội",
     "type": "tsa_gioi_thieu",
     "url": "https://ts.hust.edu.vn/index.php/en/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa"},
    {"slug": "tsa_cam_nang_2026", "title": "Cẩm nang thi Đánh giá tư duy TSA 2026",
     "type": "tsa_cam_nang", "year": 2026,
     "url": "https://ts.hust.edu.vn/tin-tuc/cam-nang-thi-danh-gia-tu-duy-tsa-2026-xuat-ban-lan-thu-2"},
    # Trang cong bo diem chuan: BANG da boc sang CSV, nhung phan VAN BAN
    # (giai thich cong thuc tinh diem xet tuyen, diem uu tien, nhan xet pho diem)
    # cung la thong tin bot can -> phai lay ca hai, khong chi lay bang roi bo.
    {"slug": "diem_chuan_2024_bai_viet", "title": "Công bố điểm chuẩn đại học 2024",
     "type": "cong_bo_diem_chuan", "year": 2024,
     "url": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53"},
    {"slug": "diem_chuan_2025_bai_viet", "title": "Công bố điểm chuẩn đại học 2025",
     "type": "cong_bo_diem_chuan", "year": 2025,
     "url": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa"},
    {"slug": "diem_chuan_2026_bai_viet", "title": "Công bố điểm chuẩn đại học 2026",
     "type": "cong_bo_diem_chuan", "year": 2026,
     "url": "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026"},
]


def fetch(url: str) -> str | None:
    """Lay HTML; neu Python khong verify duoc chuoi chung chi thi lui ve curl.

    Server ts.hust.edu.vn khong gui du chung chi trung gian nen requests bao
    CERTIFICATE_VERIFY_FAILED, trong khi curl van verify duoc va tra 200.
    Dung curl thay vi tat verify de KHONG ha thap bao mat.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        return r.text
    except requests.exceptions.SSLError:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", "25", "-A", HEADERS["User-Agent"], url],
            capture_output=True,
        )
        if out.returncode == 0 and out.stdout:
            print("       (dung curl do chuoi chung chi thieu)")
            return out.stdout.decode("utf-8", "replace")
        return None
    except Exception as exc:
        print(f"  [LOI] {url}: {type(exc).__name__}")
        return None


def extract(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    # Uu tien container BAI VIET cu the truoc (vd <div class="description" > cua
    # ts.hust.edu.vn). Neu lay container to nhat se dinh ca sidebar tin lien quan.
    main = None
    for pattern in (r"^description$", r"article-content|entry-content|post-content",
                    r"content|entry|post|detail"):
        cands = soup.find_all(class_=re.compile(pattern, re.I))
        cands = [c for c in cands if len(c.get_text(strip=True)) >= 500]
        if cands:
            main = min(cands, key=lambda c: len(c.get_text(strip=True)))
            break
    if main is None:
        main = soup.body or soup
    lines = []
    for raw in main.get_text("\n").splitlines():
        text = re.sub(r"\s+", " ", raw).strip()
        if len(text) < 2 or SPAM.search(text) or (lines and lines[-1] == text):
            continue
        lines.append(text)
    first = next((i for i, l in enumerate(lines) if len(l) >= 100), None)
    return lines[first:] if first is not None else lines


def chunk(paras: list[str]) -> list[str]:
    out, buf = [], []
    for para in paras:
        buf.append(para)
        if sum(len(p) for p in buf) >= TARGET:
            out.append("\n\n".join(buf)); buf = []
    if buf:
        tail = "\n\n".join(buf)
        if out and len(tail) < MIN_CHUNK:
            out[-1] += "\n\n" + tail
        else:
            out.append(tail)
    return out


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    all_chunks = []

    for page in PAGES:
        html = fetch(page["url"])
        if html is None:
            print(f"  [LOI] {page['slug']}: khong tai duoc")
            continue
        (RAW / f"{page['slug']}.html").write_text(html, encoding="utf-8")
        parts = chunk(extract(html))
        for i, text in enumerate(parts, 1):
            all_chunks.append({
                "document_title": page["title"], "document_no": "",
                "document_type": page["type"], "year": page.get("year", ""),
                "source_url": page["url"], "chuong": "", "dieu_no": "", "khoan_no": "",
                "heading": f"{page['title']} (phần {i})", "page_no": "", "text": text,
            })
        print(f"  {page['slug']:20s} {len(parts):3d} chunk | {sum(len(p) for p in parts)} ký tự")
        time.sleep(1)

    path = OUT / "trang_tuyen_sinh.chunks.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n{path.name}: {len(all_chunks)} chunk")
