"""Crawl 68 trang gioi thieu nganh tren ts.hust.edu.vn -> RAG + bang thong tin nhanh.

Nguon: data/link_dao_tao_nganh.md (anh tu dien link cho tung ma nganh).
Moi trang dung chung mot template:

    div.contrain
      section > h2.sec-title "Tong quan"      -> div.sec-con.overview
          div.row.accordion-item  -> to hop / diem chuan / chi tieu (DA CO trong CSV)
          div.wrap_view           -> Tot nghiep / Thoi gian dao tao / Hoc phi + van ban
      section.desc-cont "Chuong trinh dao tao" / "Hoc bong" / "Co hoi viec lam"
      section.contact_tv "Don vi quan ly"

Nguyen tac tach du lieu:
  - So lieu bang (to hop, diem chuan, chi tieu) -> BO, vi da co trong data/processed/*.csv,
    de tranh bot tra loi hai kieu khac nhau cho cung mot cau hoi.
  - Van ban mo ta + 4 fact nhanh (bang, thoi gian, hoc phi, ngon ngu) -> RAG, lay chinh
    link cua trang lam source_url.

Dung: python scripts/crawl_program_pages.py
"""

import csv
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crawl_pages import fetch  # dung lai fallback curl khi thieu chung chi trung gian

ROOT = Path(__file__).resolve().parent.parent
LINK_MD = ROOT / "data" / "link_dao_tao_nganh.md"
RAW = ROOT / "data" / "raw" / "program_pages"
# Link CTDT lay tu trang ts.hust (nguon chinh thuc). Ngoai le: trang ED5 tro toi mot BAI BAO
# ("Tam ly hoc To chuc va Cong nghiep trong Ky nguyen moi"), con trang CTDT that nam o
# web Khoa KH&CN Giao duc (da kiem tra ton tai 2026-09-26).
CURRICULUM_OVERRIDE = {
    "ED5": "https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/chuong-trinh-dao-tao-tam-ly-hoc-cong-nghiep-va-to-chuc-214989.html",
}
RAG = ROOT / "data" / "rag" / "raw_chunks"
PROCESSED = ROOT / "data" / "processed"
PROGRAMS_DIR = ROOT / "data" / "programs"
# faculty_name -> ma Khoa, tu bang danh muc (PLAN - Data Linking L1, 2026-10-04). Truoc day file
# JSON tao moi o day de faculty_code rong (TROY-IT).
FACULTY_CODE = {
    r["faculty_name"]: r["faculty_code"]
    for r in csv.DictReader((ROOT / "data" / "processed" / "linking" / "faculties.csv").open(encoding="utf-8"))
}
YEAR = 2026

# Cac muc trong div.wrap_view: nhan -> ten cot trong CSV thong tin nhanh
FACT_LABELS = {
    "tốt nghiệp": "degree",
    "thời gian tuyển sinh": "admission_time",
    "thời gian đào tạo": "duration",
    "học phí": "tuition_text",
}
# Tieu de muc bo qua khi dung van ban RAG (so lieu da nam trong CSV rieng)
SKIP_SECTIONS = {"ngành đào tạo khác thuộc"}
# Tieu de khoi rong tren trang (carousel anh sinh vien) -> khong co noi dung de RAG
NOISE = {"sinh viên tiêu biểu", "xem thêm", "hình ảnh"}
TARGET, MIN_CHUNK = 1200, 250


def parse_link_md() -> list[dict]:
    """Doc file link cua anh: '# Ten nganh (MA):' roi dong ke tiep la URL."""
    entries, pending = [], None
    for raw in LINK_MD.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        header = re.match(r"^#\s*(.+?)\s*\(([A-Z0-9][A-Z0-9 \-]*)\)\s*:?\s*$", line)
        if header:
            pending = {"program_name": header.group(1).strip(),
                       "program_code": header.group(2).replace(" ", "").strip(),
                       "url": ""}
            entries.append(pending)
        elif pending is not None and line.startswith("http"):
            if not pending["url"]:
                pending["url"] = line
            pending = None
    return entries


def text_of(tag) -> str:
    text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
    # Trang ME-GU, MI2, ED3 tach dau thanh ra khoi chu bang the HTML ("â<span>̣</span>n") ->
    # get_text chen dau cach vao giua. Bo dau cach truoc dau to hop roi ghep lai (NFC).
    return unicodedata.normalize("NFC", re.sub(r"\s+(?=[̀-ͯ])", "", text))


def parse_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    main = soup.find(class_="contrain")
    if main is None:
        return {}

    # Neo tren trang chi ghi "XEM TAI DAY" -> tach khoi HTML thi mat dia chi.
    # Nhet URL vao ngay trong text de bot con trich dan duoc link CTDT.
    for a in main.find_all("a", href=True):
        label = text_of(a)
        href = a["href"].strip()
        if label and href.startswith("http") and href not in label:
            a.string = f"{label}: {href}"

    out = {"page_code": "", "facts": {}, "language": "", "sections": [], "curriculum_url": ""}

    overview = main.find(class_="overview")
    if overview:
        for p in overview.find_all("p"):
            label = text_of(p)
            if label.lower().startswith("ngôn ngữ đào tạo"):
                out["language"] = label.split(":", 1)[-1].strip()
            elif label.lower().startswith("mã xét tuyển"):
                out["page_code"] = label.split(":", 1)[-1].replace(" ", "").strip()

        wrap = overview.find(class_="wrap_view")
        if wrap:
            for li in wrap.find_all("li"):
                item = text_of(li)
                if ":" not in item:
                    continue
                label, value = item.split(":", 1)
                key = FACT_LABELS.get(label.strip().lower())
                if key and value.strip():
                    out["facts"][key] = value.strip()
            # Van ban gioi thieu: cac the <p>/<ul> sau danh sach fact.
            # <p><strong>Gioi thieu</strong></p> la tieu de con, gop vao mot muc.
            # Quet o MOI do sau: vai trang (CH1, ED2) boc doan van trong <center>,
            # neu chi lay con truc tiep cua wrap_view se mat sach phan gioi thieu.
            body = []
            for el in wrap.find_all(["p", "ul"]):
                if el.find_parent("li"):
                    continue  # tranh dem lai noi dung da nam trong mot <ul>
                if el.name == "ul" and not body:
                    if all(":" in text_of(li) for li in el.find_all("li")):
                        continue  # chinh la danh sach fact o tren
                content = text_of(el)
                if not content:
                    continue
                if el.name == "ul":
                    content = "\n".join(f"- {text_of(li)}" for li in el.find_all("li"))
                # tieu de con: ca the <p> chi gom mot <strong>/<u>
                bold = el.find(["strong", "u"]) if el.name == "p" else None
                if bold and len(text_of(bold)) >= len(content) - 2:
                    body.append(f"**{content}**")
                else:
                    body.append(content)
            if body:
                out["sections"].append(("Giới thiệu chung", "\n\n".join(body)))

    for sec in main.find_all("section"):
        title_tag = sec.find(["h2", "h4"], class_="sec-title")
        if not title_tag:
            continue
        title = text_of(title_tag)
        if title.lower() in SKIP_SECTIONS or title.lower() == "tổng quan":
            continue
        con = sec.find(class_="sec-con") or sec
        parts = []
        for el in con.find_all(["p", "ul", "h3", "h4", "strong"], recursive=True):
            if el.find_parent("li") or el.find_parent("ul") and el.name != "ul":
                continue
            if el.name == "ul":
                parts.append("\n".join(f"- {text_of(li)}" for li in el.find_all("li")))
            else:
                content = text_of(el)
                if content:
                    parts.append(content)
        if sec.get("class") and "contact_tv" in sec.get("class"):
            h4 = sec.find("h4")
            lead = text_of(h4) if h4 else ""
            items = "\n".join(f"- {text_of(li)}" for li in sec.find_all("li"))
            parts = [p for p in (lead, items) if p]
        body = "\n\n".join(dict.fromkeys(
            p for p in parts if p and p.strip().lower() not in NOISE))
        if body:
            out["sections"].append((title, body))
        # Neo CTDT co 2 kieu nhan: "... chuong trinh dao tao: XEM TAI DAY" va (nganh moi
        # CH-E20, ED5, FL4) "Thong tin chuong trinh dao tao - XEM CHI TIET". Lay neo DAU TIEN:
        # TROY-IT co them neo thu 2 "XEM CHI TIET" tro sang troy.edu, khong phai CTDT.
        for a in con.find_all("a", href=True):
            label = (text_of(a) + " " + text_of(a.parent)).lower()
            if not out["curriculum_url"] and (
                    "xem tại đây" in label or "chương trình đào tạo" in label):
                out["curriculum_url"] = a["href"]
    return out


def looks_glued(text: str) -> bool:
    """Van ban bi ep phang tu bang: mat khoang trang giua cac o.

    Dau hieu: chu thuong dinh thang chu hoa ("...pham Food..." -> "...phamFood")
    hoac dau hai cham dinh ngay chu tiep theo ("Ten chuong trinh:Name of program").
    KHONG dung dai ky tu kieu [a-z][A-Z] vi trong Unicode dai 'À-Ỹ' trum ca chu
    thuong co dau tieng Viet, se bao nham gan nhu moi cau.
    """
    glued = sum(1 for a, b in zip(text, text[1:]) if a.islower() and b.isupper())
    return glued >= 3 or len(re.findall(r":[^\s]", text)) >= 2


def intro_text(page: dict) -> str:
    """Doan gioi thieu nganh, dung lam short_description trong data/programs/<code>.json."""
    for title, body in page["sections"]:
        if title != "Giới thiệu chung":
            continue
        paras = [p.strip() for p in body.split("\n\n")]

        def usable(p: str) -> bool:
            # Loai tieu de con, gach dau dong, va cac dong lien he/lien ket:
            # trang TROY-IT co dong "Xep hang DH Troy: https://..." dai 92 ky tu,
            # du dai de bi nham la doan mo ta.
            return (not p.startswith(("**", "-")) and len(p) >= 80
                    and "http" not in p
                    and not re.match(r"^(Địa chỉ|Điện thoại|Website|Email|Hotline|Xếp hạng|Fax)\b", p))

        # Uu tien doan nam ngay sau tieu de noi ve CHUONG TRINH (vd TROY-IT co han
        # muc "GIOI THIEU VE CHUONG TRINH TROY-IT"), vi doan dau trang cac CT quoc te
        # thuong dang gioi thieu truong doi tac chu khong phai nganh hoc.
        for i, p in enumerate(paras):
            label = p.strip("*: ").lower()
            if not p.startswith("**"):
                continue
            if not (label == "giới thiệu" or ("giới thiệu" in label and "chương trình" in label)):
                continue  # "GIOI THIEU DAI HOC GRIFFITH" la gioi thieu doi tac, khong phai nganh
            nxt = next((q for q in paras[i + 1:] if usable(q)), "")
            if nxt:
                return nxt[:800]
        for clean in paras:
            if not usable(clean):
                continue
            return clean[:800]
        # Vai nganh (vd MS5) viet phan gioi thieu hoan toan bang gach dau dong
        for clean in paras:
            first = clean.lstrip("- ").split("\n")[0].strip()
            if len(first) >= 80:
                return first[:800]
    return ""


def update_program_json(entry: dict, page: dict, faculty_name: str) -> None:
    """Bo sung thong tin moi vao data/programs/<code>.json, GIU nguyen field cu.

    File cu chi co mo ta 1-2 cau lay tu web Truong/Khoa, 5 nganh con rong han.
    Trang ts.hust.edu.vn co doan gioi thieu chuan cho ca 68 nganh nen dung de lap.
    """
    path = PROGRAMS_DIR / f"{entry['program_code']}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "program_code": entry["program_code"],
        "program_name": entry["program_name"],
        "faculty_code": FACULTY_CODE.get(faculty_name, ""),
        "faculty_name": faculty_name,
        "curriculum_url": "",
        "source_title": "",
    }
    # Luon uu tien doan gioi thieu tren ts.hust.edu.vn, KHONG so sanh do dai.
    # Ban cu lay tu web tung Truong co cho la bang bi ep phang, dinh lien khong co
    # khoang trang ("...ELITECHTen chuong trinh:Name of program:...") va bi cat cut
    # o 600 ky tu — dai hon nhung khong dung duoc.
    intro = intro_text(page)
    if intro:
        data["short_description"] = intro
        data["description_source_url"] = entry["url"]
    data["program_page_url"] = entry["url"]
    # Ghi de link cu lay tu web Truong/Khoa (16 nganh lech, vai link sai: TE1 tro sang
    # bo mon su pham, MS1 tro CTDT tien si) -> JSON va program_overview CSV luon trung nhau.
    if page.get("curriculum_url"):
        data["curriculum_url"] = page["curriculum_url"]
    for key in ("language", "degree", "duration", "tuition_text", "admission_time"):
        value = page["facts"].get(key) if key != "language" else page.get("language")
        if value:
            data[key] = value
    data["collection_date"] = os.environ.get("COLLECTION_DATE") or time.strftime("%Y-%m-%d")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_markdown(entry: dict, page: dict) -> str:
    facts = page["facts"]
    head = [f"# {entry['program_name']} ({entry['program_code']})"]
    quick = []
    if page.get("language"):
        quick.append(f"- Ngôn ngữ đào tạo: {page['language']}")
    for key, label in (("degree", "Bằng tốt nghiệp"), ("duration", "Thời gian đào tạo"),
                       ("tuition_text", "Học phí"), ("admission_time", "Thời gian tuyển sinh")):
        if facts.get(key):
            quick.append(f"- {label}: {facts[key]}")
    if quick:
        head.append("## Thông tin nhanh\n" + "\n".join(quick))
    for title, body in page["sections"]:
        head.append(f"## {title}\n{body}")
    return "\n\n".join(head)


def chunk_sections(entry: dict, page: dict) -> list[dict]:
    """Chia theo muc, gop muc ngan lai cho du ~1200 ky tu.

    Moi chunk deu mang tien to '[Ten nganh (MA)]' vi cau van trong trang hay dung
    dai tu ("Nganh nay dao tao...") — tach ra khoi trang thi mat ngu canh.
    """
    prefix = f"[{entry['program_name']} ({entry['program_code']})]"
    facts = page["facts"]
    quick = [f"Ngôn ngữ đào tạo: {page['language']}"] if page.get("language") else []
    for key, label in (("degree", "Bằng tốt nghiệp"), ("duration", "Thời gian đào tạo"),
                       ("tuition_text", "Học phí"), ("admission_time", "Thời gian tuyển sinh")):
        if facts.get(key):
            quick.append(f"{label}: {facts[key]}")

    blocks = []
    if quick:
        blocks.append(("Thông tin nhanh", " · ".join(quick)))
    blocks += page["sections"]

    # Muc qua dai (thuong la "Gioi thieu chung" cua cac CT quoc te, co ca phan
    # gioi thieu truong doi tac) -> cat theo doan van cho chunk khong vuot ~2x TARGET.
    split_blocks = []
    for title, body in blocks:
        if len(body) <= TARGET * 1.6:
            split_blocks.append((title, body))
            continue
        buf_p, part = [], 1
        for para in body.split("\n\n"):
            buf_p.append(para)
            if sum(len(p) for p in buf_p) >= TARGET:
                split_blocks.append((f"{title} ({part})", "\n\n".join(buf_p)))
                buf_p, part = [], part + 1
        if buf_p:
            tail = "\n\n".join(buf_p)
            if len(tail) < MIN_CHUNK and split_blocks:
                split_blocks[-1] = (split_blocks[-1][0], split_blocks[-1][1] + "\n\n" + tail)
            else:
                split_blocks.append((f"{title} ({part})", tail))

    chunks, buf, titles = [], [], []
    for title, body in split_blocks:
        buf.append(f"{title}: {body}" if len(body) < 400 else f"{title}\n{body}")
        titles.append(title)
        if sum(len(b) for b in buf) >= TARGET:
            chunks.append((titles[:], "\n\n".join(buf)))
            buf, titles = [], []
    if buf:
        tail = "\n\n".join(buf)
        if chunks and len(tail) < MIN_CHUNK:
            chunks[-1] = (chunks[-1][0] + titles, chunks[-1][1] + "\n\n" + tail)
        else:
            chunks.append((titles, tail))

    return [{
        "document_title": f"Ngành {entry['program_name']} ({entry['program_code']})",
        "document_no": "",
        "document_type": "gioi_thieu_nganh",
        "year": YEAR,
        "source_url": entry["url"],
        "program_code": entry["program_code"],
        "program_name": entry["program_name"],
        "chuong": "", "dieu_no": "", "khoan_no": "",
        "heading": f"{entry['program_code']} — {' / '.join(dict.fromkeys(t))}",
        "page_no": "",
        "text": f"{prefix}\n{body}",
    } for t, body in chunks]


if __name__ == "__main__":
    OFFLINE = "--offline" in sys.argv
    entries = parse_link_md()
    print(f"Doc duoc {len(entries)} muc tu {LINK_MD.name}")
    missing_url = [e["program_code"] for e in entries if not e["url"]]
    if missing_url:
        print(f"  [BO QUA] chua co link: {', '.join(missing_url)}")

    seen_url: dict[str, str] = {}
    for e in entries:
        if e["url"] and e["url"] in seen_url:
            print(f"  [CANH BAO] {e['program_code']} dung trung link voi {seen_url[e['url']]}")
        seen_url.setdefault(e["url"], e["program_code"])

    with (PROCESSED / f"programs_{YEAR}.csv").open(encoding="utf-8", newline="") as f:
        faculty_of = {r["program_code"]: r["faculty_name"] for r in csv.DictReader(f)}

    RAW.mkdir(parents=True, exist_ok=True)
    RAG.mkdir(parents=True, exist_ok=True)
    PROGRAMS_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks, facts_rows, md_parts, problems = [], [], [], []
    for e in entries:
        code = e["program_code"]
        if not e["url"]:
            continue
        # Server ts.hust.edu.vn thi thoang rot ket noi giua chung -> thu lai 2 lan
        html = None
        cached = RAW / f"{code}.html"
        if OFFLINE and cached.exists():
            # --offline: phan tich lai HTML da tai, giu ngay thu thap = ngay tai file
            html = cached.read_text(encoding="utf-8")
            os.environ["COLLECTION_DATE"] = time.strftime("%Y-%m-%d", time.localtime(cached.stat().st_mtime))
        for attempt in range(0 if html else 3):
            html = fetch(e["url"])
            if html:
                break
            time.sleep(2 * (attempt + 1))
        if not html:
            problems.append(f"{code}: khong tai duoc trang")
            continue
        if not (OFFLINE and cached.exists()):
            (RAW / f"{code}.html").write_text(html, encoding="utf-8")
        page = parse_page(unicodedata.normalize("NFC", html))
        if page and code in CURRICULUM_OVERRIDE:
            page["curriculum_url"] = CURRICULUM_OVERRIDE[code]
        if not page or not page["sections"]:
            problems.append(f"{code}: khong boc duoc noi dung")
            continue
        if page["page_code"] and page["page_code"].upper() != code.upper():
            problems.append(f"{code}: trang ghi ma '{page['page_code']}' -> link co the sai nganh")

        chunks = chunk_sections(e, page)
        all_chunks += chunks
        md_parts.append(build_markdown(e, page))
        update_program_json(e, page, faculty_of.get(code, ""))
        desc = json.loads((PROGRAMS_DIR / f"{code}.json").read_text(encoding="utf-8"))
        if not desc.get("short_description"):
            problems.append(f"{code}: short_description rong")
        elif looks_glued(desc["short_description"]):
            problems.append(f"{code}: short_description con dinh chu (bang bi ep phang)")
        facts_rows.append({
            "program_code": code,
            "program_name": e["program_name"],
            "language": page.get("language", ""),
            "degree": page["facts"].get("degree", ""),
            "duration": page["facts"].get("duration", ""),
            "tuition_text": page["facts"].get("tuition_text", ""),
            "admission_time": page["facts"].get("admission_time", ""),
            "curriculum_url": page.get("curriculum_url", ""),
            "year": YEAR,
            "source_url": e["url"],
            "collection_date": os.environ.get("COLLECTION_DATE") or time.strftime("%Y-%m-%d"),
            "verification_status": "web_extracted",
        })
        chars = sum(len(c["text"]) for c in chunks)
        print(f"  {code:10s} {len(chunks)} chunk | {chars:5d} ky tu | {len(page['sections'])} muc")
        time.sleep(0.4)

    out_jsonl = RAG / "nganh_dao_tao.chunks.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (RAG / "nganh_dao_tao.md").write_text("\n\n---\n\n".join(md_parts), encoding="utf-8")

    out_csv = PROCESSED / f"program_overview_{YEAR}.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(facts_rows[0].keys()))
        w.writeheader()
        w.writerows(facts_rows)

    print(f"\n{out_jsonl.name}: {len(all_chunks)} chunk / "
          f"{sum(len(c['text']) for c in all_chunks)} ky tu, {len(facts_rows)} nganh")
    print(f"{out_csv.name}: {len(facts_rows)} dong")
    for p in problems:
        print(f"  [VAN DE] {p}")
