"""Chuan hoa metadata cho 14 file data/rag/raw_chunks/*.chunks.jsonl -> data/rag/normalized/.

Thuc hien PLAN - Metadata Design (v2), muc 3-7. KHONG ghi de file goc: 14 file goc do 8 script
khac nhau sinh ra; neu ghi de thi lan chay lai script goc se xoa metadata, va khi nghi ngo
khong con ban de doi chieu.

Viec lam theo thu tu (moi buoc co ly do o PLAN v2):
  1. bo khoa cau hinh lot vao metadata (stop_at, layout)          -> loi N1
  2. gan page_no cho 80 chunk PDF thieu trang                     -> PLAN muc 7
  3. tach chunk > 2.500 ky tu                                     -> loi N2
  4. sinh chunk_id <doc>::<locator>                               -> PLAN muc 3
  5. gan source_kind, verification_status, collection_date, dataset_version, cohort
  6. gop document_type 13 -> 9                                    -> PLAN muc 5
  7. bu year (50 chunk), faculty_code (151 chunk trang nganh), tach muc_no (de an)
  8. chuan NFC lan cuoi, xep thu tu truong

Dung: python scripts/normalize_chunks.py
"""

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
RAG = ROOT / "data" / "rag" / "raw_chunks"
OUT = ROOT / "data" / "rag" / "normalized"
ADMISSION = ROOT / "data" / "raw" / "admission"
DATASET_VERSION = "2026.1"
MAX_CHARS = 2500      # PRD muc 11.2
TARGET_CHARS = 1800   # co gang cat quanh muc nay khi tach

# ---------------------------------------------------------------------------------------------
# Cau hinh tung nguon. collection_date = ngay luu file goc (PDF / HTML) — ngay thu thap that,
# khong phai ngay chay script.
# ---------------------------------------------------------------------------------------------
SOURCES = {
    "QCDT_2025_5445_QD-DHBK": dict(slug="qcdt2025", kind="pdf_text", status="pdf_text",
                                   collected="2026-09-21", locator="dieu"),
    "Quy_dinh_ngoai_ngu_K70": dict(slug="nnk70", kind="pdf_text", status="pdf_text",
                                   collected="2026-09-24", locator="dieu", cohort="<=K70"),
    "Quy_dinh_ngoai_ngu_K71_2026": dict(slug="nnk71", kind="pdf_text", status="pdf_text",
                                        collected="2026-09-24", locator="dieu", cohort="K71+"),
    "So_tay_sinh_vien_2026": dict(slug="sotay2026", kind="pdf_text", status="pdf_text",
                                  collected="2026-09-21", locator="page"),
    "de_an_tuyen_sinh_2024": dict(slug="dean2024", kind="pdf_text", status="pdf_text",
                                  collected="2026-09-19", locator="muc",
                                  pdf="Đề án tuyển sinh 2024 -FINAL.pdf"),
    "de_an_tuyen_sinh_2025": dict(slug="dean2025", kind="web", status="html_parsed",
                                  collected="2026-09-21", locator="muc"),
    "de_an_tuyen_sinh_2026": dict(slug="dean2026", kind="web", status="html_parsed",
                                  collected="2026-09-21", locator="muc"),
    "gioi_thieu_truong_khoa": dict(slug="donvi", kind="web", status="html_parsed",
                                   collected="2026-09-21", locator="faculty", year_default="2026"),
    "kkht_2022": dict(slug="kkht2022", kind="pdf_scan", status="vision_extracted",
                      collected="2026-09-21", locator="dieu"),
    "nganh_dao_tao": dict(slug="nganh", kind="web", status="html_parsed",
                          collected="2026-09-23", locator="program"),
    "qui-dinh-ve-xttn-nam-2026-ky": dict(slug="xttn2026", kind="pdf_text", status="pdf_text",
                                         collected="2026-09-21", locator="dieu"),
    "trang_tuyen_sinh": dict(slug="ts", kind="web", status="html_parsed",
                             collected="2026-09-22", locator="article", year_default="2026"),
    "tsa_quyche": dict(slug="tsa2024", kind="pdf_scan", status="vision_extracted",
                       collected="2026-09-21", locator="dieu"),
    # PDF co lop chu, nhung chunk nay duoc chep bang vision tu Phu luc I (bang) -> giu vision_extracted
    "tuition": dict(slug="hocphi2024", kind="pdf_text", status="vision_extracted",
                    collected="2026-09-20", locator="dieu"),
}

# Trang (so trang cua FILE PDF, cung quy uoc voi QCDT/XTTN/ngoai ngu) cua tung Dieu trong 2 ban
# scan, gan TAY 2026-09-27 bang cach xem anh data/raw/tsa_quyche/p*.png va
# data/raw/kkht_2022/pages/p*.png. Trang 1 cua quy che TSA la quyet dinh ban hanh nen trang in
# "2" = trang PDF 3. Khong suy tu noi dung vi ban scan khong co lop chu.
PAGE_BY_DIEU = {
    "tsa_quyche": {
        1: "2", 2: "2", 3: "2-3", 4: "3", 5: "3", 6: "3-4", 7: "4", 8: "4", 9: "4-6",
        10: "6", 11: "6", 12: "6-7", 13: "7", 14: "7-8", 15: "8-9", 16: "9", 17: "10",
        18: "10", 19: "10-11", 20: "11", 21: "11", 22: "11-12", 23: "12", 24: "13-14",
        25: "15", 26: "15", 27: "15", 28: "15-16", 29: "16", 30: "16", 31: "16-18",
        32: "18", 33: "18", 34: "19", 35: "19",
    },
    "kkht_2022": {1: "1", 2: "1", 3: "1", 4: "1-2", 5: "2", 6: "2", 7: "2"},
    # "Cac muc hoc phi khac" nam o Phu luc I, trang 4 (tim thay 4/5 dong trong lop chu trang 4)
    "tuition": {5: "4"},
}

# Bai dang tren ts.hust.edu.vn -> slug ngan cho chunk_id
ARTICLE_SLUG = {
    "https://ts.hust.edu.vn/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa": "tsa-gioi-thieu",
    "https://ts.hust.edu.vn/index.php/en/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa": "tsa-gioi-thieu-en",
    "https://ts.hust.edu.vn/tin-tuc/cam-nang-thi-danh-gia-tu-duy-tsa-2026-xuat-ban-lan-thu-2": "tsa-cam-nang-2026",
    "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53": "diem-chuan-2024",
    "https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa": "diem-chuan-2025",
    "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026": "diem-chuan-2026",
}

# PLAN v2 muc 5: 13 -> 9 gia tri
DOCUMENT_TYPE = {
    "quy_dinh_xttn": "quy_dinh",
    "quy_dinh_hoc_phi": "quy_dinh",
    "quy_dinh_hoc_bong_kkht": "quy_dinh",
    "gioi_thieu_truong": "gioi_thieu_don_vi",
    "cong_bo_diem_chuan": "tin_tuyen_sinh",
    "tsa_gioi_thieu": "tin_tuyen_sinh",
    "tsa_cam_nang": "tin_tuyen_sinh",
}
DOCUMENT_TYPES = {"quy_che_dao_tao", "so_tay_sinh_vien", "de_an_tuyen_sinh", "quy_dinh",
                  "quy_dinh_ngoai_ngu", "quy_che_thi_tsa", "gioi_thieu_nganh",
                  "gioi_thieu_don_vi", "tin_tuyen_sinh"}

# Ten Truong/Khoa trong danh muc nganh -> ma Khoa: doc tu bang danh muc
# data/processed/linking/faculties.csv (PLAN - Data Linking buoc 1, 2026-10-04) — mot nguon duy
# nhat cho ca build_db.py va crawl_programs.py. faculty_name o do = dung chuoi trong programs_*.csv.
FACULTY_CODE = {
    r["faculty_name"]: r["faculty_code"]
    for r in csv.DictReader((ROOT / "data" / "processed" / "linking" / "faculties.csv").open(encoding="utf-8"))
}

DROP_KEYS = {"stop_at", "layout", "program_name"}   # program_name: ten nganh chi song o bang danh muc
FIELD_ORDER = ["chunk_id", "document_title", "document_type", "source_kind", "source_url",
               "document_no", "year", "cohort", "program_code", "faculty_code", "chuong",
               "dieu_no", "khoan_no", "muc_no", "heading", "page_no", "verification_status",
               "collection_date", "dataset_version", "text"]

MUC_RE = re.compile(r"^\s*((?:[IVX]+|\d+(?:\.\d+)*[a-z]?))\.\s")
# Muc "(2) Xet tuyen..."/"(3) Xet tuyen..." (de an 2024/25/26, sua trong de_an_to_rag.py
# 2026-10-04): danh so kieu ngoac don, khong co dau cham sau so nen MUC_RE tren khong khop.
MUC_PAREN_RE = re.compile(r"^\((\d+)\)\s")
BREAK_RE = re.compile(r"^\s*(\d+\.|[a-zđ]\)|[-+•]\s|\|)")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s) if isinstance(s, str) else s


# --------------------------------------------------------------------------- page_no --------
def norm_key(t: str) -> str:
    return re.sub(r"[^\w]", "", t.lower())


def pdf_page_ranges(chunks: list[dict], pdf: Path) -> list[str]:
    """Trang cua moi chunk trong PDF co lop chu: tim tung dong cua chunk trong text cac trang.

    Chi tin dong xuat hien o DUY NHAT mot trang; lay trang xuat hien nhieu nhat roi bo cac
    trang lac xa (> 2 trang) — cau pho bien ("Thi sinh...") hay trung o trang khac.
    """
    pages = [norm_key(p.get_text()) for p in pymupdf.open(pdf)]
    out = []
    for c in chunks:
        body = c["text"].split("\n", 1)[-1]
        keys = [norm_key(x)[:40] for x in body.split("\n") if len(norm_key(x)) >= 25]
        hits = []
        for k in keys:
            found = [i + 1 for i, t in enumerate(pages) if k in t]
            if len(found) == 1:
                hits.append(found[0])
        if not hits:
            for k in keys:
                found = [i + 1 for i, t in enumerate(pages) if k in t]
                if found:
                    hits.append(found[0])
        if not hits:
            out.append("")
            continue
        mode = Counter(hits).most_common(1)[0][0]
        kept = [h for h in hits if abs(h - mode) <= 2]
        out.append(str(mode) if min(kept) == max(kept) else f"{min(kept)}-{max(kept)}")
    return out


# --------------------------------------------------------------------------- split ----------
def split_text(text: str) -> list[str]:
    """Tach chunk qua dai theo khoan/diem/dong bang; moi manh giu dong [tieu de] dau chunk
    va lap lai dong tieu de cot neu cat giua bang markdown."""
    if len(text) <= MAX_CHARS:
        return [text]
    lines = text.split("\n")
    prefix = [lines[0]] if lines[0].startswith("[") else []
    body = lines[len(prefix):]
    pieces, cur, table_head = [], [], []
    for i, ln in enumerate(body):
        if ln.startswith("|") and not table_head and i + 1 < len(body) and body[i + 1].startswith("|---"):
            table_head = [ln, body[i + 1]]
        size = sum(len(x) + 1 for x in cur)
        if cur and size + len(ln) > TARGET_CHARS and (BREAK_RE.match(ln) or size + len(ln) > MAX_CHARS - 200):
            pieces.append(cur)
            cur = list(table_head) if ln.startswith("|") and table_head and not ln.startswith("|---") else []
        cur.append(ln)
    if cur:
        pieces.append(cur)
    return ["\n".join(prefix + p).strip() for p in pieces]


# --------------------------------------------------------------------------- locator --------
def slugify(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9.]+", "-", s).strip("-")


def base_locator(name: str, cfg: dict, c: dict) -> str:
    kind = cfg["locator"]
    if kind == "dieu":
        loc = f"d{c.get('dieu_no') or '0'}"
        if c.get("khoan_no"):
            loc += f"k{c['khoan_no']}"
        return loc
    if kind == "page":
        return f"p{str(c.get('page_no') or '0').split('-')[0]}"
    if kind == "muc":
        return f"m{c.get('muc_no') or '0'}"
    if kind == "program":
        return c["program_code"]
    if kind == "faculty":
        return c["faculty_code"]
    if kind == "article":
        return ARTICLE_SLUG[c["source_url"]]
    raise ValueError(kind)


def assign_ids(name: str, cfg: dict, chunks: list[dict]) -> None:
    """chunk_id = <slug>::<locator>[-n]. Nguon dang danh sach (so tay, nganh, don vi, bai viet)
    luon co -n; nguon Dieu/muc chi them -n khi trung khoa. Deterministic theo thu tu goc."""
    keys = [base_locator(name, cfg, c) for c in chunks]
    counts = Counter(keys)
    always_n = cfg["locator"] in ("page", "program", "faculty", "article")
    seen = defaultdict(int)
    for c, k in zip(chunks, keys):
        seen[k] += 1
        loc = f"{k}-{seen[k]}" if (always_n or counts[k] > 1) else k
        c["chunk_id"] = f"{cfg['slug']}::{loc}".lower()


# --------------------------------------------------------------------------- main -----------
def load_faculty_by_program() -> dict[str, str]:
    rows = csv.DictReader((ROOT / "data" / "processed" / "programs_2026.csv").open(encoding="utf-8-sig"))
    return {r["program_code"]: FACULTY_CODE[r["faculty_name"]] for r in rows}


def sotay_override_pages() -> set[int]:
    return {int(p.stem[1:]) for p in (ROOT / "data" / "raw" / "sotay_overrides").glob("p*.md")}


def normalize_source(name: str, cfg: dict, fac_by_prog: dict, overrides: set[int]) -> tuple[list[dict], dict]:
    raw = [json.loads(l) for l in (RAG / f"{name}.chunks.jsonl").open(encoding="utf-8")]
    stats = Counter()

    # 1-2. bo khoa rac, gan trang
    for c in raw:
        for k in DROP_KEYS & c.keys():
            stats[f"bỏ khoá {k}"] += 1
            del c[k]
    if name in PAGE_BY_DIEU:
        for c in raw:
            if not c.get("page_no"):
                c["page_no"] = PAGE_BY_DIEU[name][int(c["dieu_no"])]
                stats["gắn page_no (tra tay)"] += 1
    if cfg.get("pdf"):
        for c, pg in zip(raw, pdf_page_ranges(raw, ADMISSION / cfg["pdf"])):
            if not c.get("page_no") and pg:
                c["page_no"] = pg
                stats["gắn page_no (tự động từ lớp chữ PDF)"] += 1

    # 7a. muc_no cho de an (truoc khi tach, vi heading dung chung)
    if cfg["locator"] == "muc":
        for c in raw:
            c["heading"] = re.sub(r"\(phan (\d+)\)", r"(phần \1)", c["heading"])
            m = MUC_RE.match(c["heading"]) or MUC_PAREN_RE.match(c["heading"])
            c["muc_no"] = m.group(1) if m else ""

    # 4a. chunk_id sinh TRUOC khi tach: manh tach chi them -<n> sau ID goc (neu sinh sau thi
    # cac manh bi coi la trung khoa va nhan hai lan hau to, vd "d24-1-1")
    assign_ids(name, cfg, raw)

    # 3. tach chunk dai
    chunks = []
    for c in raw:
        parts = split_text(c["text"])
        if len(parts) > 1:
            stats["chunk tách"] += 1
        for i, t in enumerate(parts, 1):
            d = dict(c, text=t)
            if len(parts) > 1:
                d["heading"] = f"{c['heading']} (đoạn {i}/{len(parts)})"
                d["_part"] = i
            chunks.append(d)

    # 4b. manh tach: them -<n> sau locator goc
    for c in chunks:
        if "_part" in c:
            c["chunk_id"] += f"-{c.pop('_part')}"

    # 5-7. metadata
    for c in chunks:
        c["document_type"] = DOCUMENT_TYPE.get(c["document_type"], c["document_type"])
        c["source_kind"] = cfg["kind"]
        c["collection_date"] = cfg["collected"]
        c["dataset_version"] = DATASET_VERSION
        c["cohort"] = cfg.get("cohort", "")
        status = cfg["status"]
        if name == "So_tay_sinh_vien_2026":
            pages = [int(x) for x in str(c["page_no"]).split("-")]
            if any(p in overrides for p in range(pages[0], pages[-1] + 1)):
                status = "manual_override"
        c["verification_status"] = status
        if not c.get("year") and cfg.get("year_default"):
            c["year"] = cfg["year_default"]
            stats["bù year"] += 1
        if name == "nganh_dao_tao":
            c["faculty_code"] = fac_by_prog[c["program_code"]]
            stats["bù faculty_code"] += 1
        # year: so nguyen o moi chunk (de an sinh int, cac nguon khac sinh chuoi)
        c["year"] = int(c["year"]) if str(c.get("year", "")).strip() else ""
        # page_no: thong nhat kieu chuoi (mot so nguon sinh int, PAGE_BY_DIEU/pdf_page_ranges
        # sinh chuoi vd "3-4") -> validator va embed_chunks.py chi can xu ly mot kieu
        if c.get("page_no") not in ("", None):
            c["page_no"] = str(c["page_no"])
        for k in list(c):
            c[k] = nfc(c[k])

    ordered = [{k: c.get(k, "") for k in FIELD_ORDER} for c in chunks]
    extra = {k for c in chunks for k in c} - set(FIELD_ORDER)
    if extra:
        raise SystemExit(f"{name}: truong la {extra} — them vao FIELD_ORDER hoac DROP_KEYS")
    stats["chunk"] = len(ordered)
    return ordered, stats


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fac_by_prog = load_faculty_by_program()
    overrides = sotay_override_pages()
    total, all_ids = 0, []
    for name, cfg in SOURCES.items():
        chunks, stats = normalize_source(name, cfg, fac_by_prog, overrides)
        with (OUT / f"{name}.chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        total += len(chunks)
        all_ids += [c["chunk_id"] for c in chunks]
        extra = ", ".join(f"{k}={v}" for k, v in stats.items() if k != "chunk")
        print(f"  {name:32s} {stats['chunk']:4d} chunk  {extra}")
    dup = [k for k, v in Counter(all_ids).items() if v > 1]
    print(f"Tổng: {total} chunk -> {OUT.relative_to(ROOT)} | chunk_id trùng: {len(dup)} {dup[:5]}")


if __name__ == "__main__":
    main()
