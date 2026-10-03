"""Kiem tra metadata cua chunk da chuan hoa (data/rag/normalized/) va bang CSV (data/processed/).

Luat theo PLAN - Metadata Design (v2), muc 6. Moi luat co ma (E = loi, W = canh bao).

--selftest: CAI LOI CO Y vao ban sao du lieu (moi luat mot loi) va xac nhan validator bat
duoc. Ly do: lan lam tu dien alias, validator chay sach ma van bo lot 5 loi that — chay sach
chi co nghia khi da chung minh no bat duoc loi.

Chay binh thuong khong co loi -> ghi danh sach chunk_id vao data/rag/normalized/_chunk_ids.txt
de lan sau canh bao khi chunk_id doi (bo test ghim ket qua mong doi theo chunk_id).

Dung: python scripts/validate_metadata.py [--selftest]
"""

import copy
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NORM = ROOT / "data" / "rag" / "normalized"
PROCESSED = ROOT / "data" / "processed"
MANIFEST = NORM / "_chunk_ids.txt"
DATASET_VERSION = "2026.1"

FIELDS = ["chunk_id", "document_title", "document_type", "source_kind", "source_url",
          "document_no", "year", "cohort", "program_code", "faculty_code", "chuong",
          "dieu_no", "khoan_no", "muc_no", "heading", "page_no", "verification_status",
          "collection_date", "dataset_version", "text"]
GROUP_A = ["chunk_id", "document_title", "document_type", "source_kind", "source_url",
           "dataset_version", "collection_date", "verification_status"]
DOCUMENT_TYPES = {"quy_che_dao_tao", "so_tay_sinh_vien", "de_an_tuyen_sinh", "quy_dinh",
                  "quy_dinh_ngoai_ngu", "quy_che_thi_tsa", "gioi_thieu_nganh",
                  "gioi_thieu_don_vi", "tin_tuyen_sinh"}
SOURCE_KINDS = {"pdf_text", "pdf_scan", "web"}
STATUSES = {"vision_extracted", "vision_double_read", "pdf_text", "html_parsed", "web_extracted",
            "manual_verified", "manual_override", "rule_derived", "third_party"}
COHORTS = {"", "K71+", "<=K70"}
FACULTIES = {"SOICT", "SEEE", "SME", "SCLS", "SMSE", "SEM", "FAMI", "SEP", "SOFL", "FED"}
CSV_STD = ["year", "source", "source_url", "collection_date", "verification_status", "dataset_version"]
LOOKUP_TABLES = {"entity_aliases", "program_aliases"}

ID_RE = re.compile(r"^[a-z0-9]+::[a-z0-9.\-]+$")
PAGE_RE = re.compile(r"^\d+(-\d+)?$")
DATE_RE = re.compile(r"^2026-\d{2}-\d{2}$")
URL_RE = re.compile(r"^https?://\S+$")


def load():
    chunks = [json.loads(l) for f in sorted(NORM.glob("*.chunks.jsonl")) for l in f.open(encoding="utf-8")]
    tables = {p.stem: list(csv.DictReader(p.open(encoding="utf-8-sig"))) for p in sorted(PROCESSED.glob("*.csv"))}
    return chunks, tables


def programs(tables) -> set[str]:
    return {r["program_code"] for y in (2024, 2025, 2026) for r in tables[f"programs_{y}"]}


def check(chunks, tables) -> list[tuple[str, str, str]]:
    out = []
    add = lambda lvl, rule, msg: out.append((lvl, rule, msg))
    progs = programs(tables)

    # ------------------------------------------------------------------ chunk
    seen = {}
    for c in chunks:
        cid = c.get("chunk_id", "")
        if cid in seen:
            add("E", "E1 chunk_id trùng", cid)
        seen[cid] = True
        if not ID_RE.match(cid):
            add("E", "E1 chunk_id sai định dạng", repr(cid))
        if set(c) != set(FIELDS):
            add("E", "E7 trường ngoài từ điển / thiếu trường",
                f"{cid}: thừa {sorted(set(c) - set(FIELDS))} thiếu {sorted(set(FIELDS) - set(c))}")
        for k in GROUP_A:
            if not str(c.get(k, "")).strip():
                add("E", "E2 thiếu trường Nhóm A", f"{cid}: {k}")
        kind = c.get("source_kind")
        if kind in ("pdf_text", "pdf_scan"):
            pg = str(c.get("page_no", ""))
            if not pg:
                add("E", "E3 nguồn PDF thiếu page_no", cid)
            elif not PAGE_RE.match(pg):
                add("E", "E3 page_no sai định dạng", f"{cid}: {pg!r}")
            elif "-" in pg and int(pg.split("-")[0]) > int(pg.split("-")[1]):
                add("E", "E3 page_no ngược", f"{cid}: {pg}")
        if c.get("document_type") not in DOCUMENT_TYPES:
            add("E", "E4 document_type ngoài từ vựng", f"{cid}: {c.get('document_type')}")
        if kind not in SOURCE_KINDS:
            add("E", "E4 source_kind ngoài từ vựng", f"{cid}: {kind}")
        if c.get("verification_status") not in STATUSES:
            add("E", "E4 verification_status ngoài từ vựng", f"{cid}: {c.get('verification_status')}")
        if c.get("cohort", "") not in COHORTS:
            add("E", "E4 cohort ngoài từ vựng", f"{cid}: {c.get('cohort')}")
        if not URL_RE.match(str(c.get("source_url", ""))):
            add("E", "E5 source_url không phải link", f"{cid}: {c.get('source_url')!r}")
        for k in ("text", "heading", "document_title"):
            v = c.get(k, "")
            if isinstance(v, str) and v != unicodedata.normalize("NFC", v):
                add("E", "E6 chữ không phải NFC", f"{cid}: {k}")
        y = c.get("year")
        if not isinstance(y, int) or not 2022 <= y <= 2026:
            add("E", "E8 year thiếu / không phải số năm", f"{cid}: {y!r}")
        if not DATE_RE.match(str(c.get("collection_date", ""))):
            add("E", "E9 collection_date sai", f"{cid}: {c.get('collection_date')!r}")
        if c.get("dataset_version") != DATASET_VERSION:
            add("E", "E9 dataset_version sai", f"{cid}: {c.get('dataset_version')!r}")
        if c.get("program_code") and c["program_code"] not in progs:
            add("E", "E10 program_code không có trong danh mục", f"{cid}: {c['program_code']}")
        if c.get("faculty_code") and c["faculty_code"] not in FACULTIES:
            add("E", "E10 faculty_code không có trong danh mục", f"{cid}: {c['faculty_code']}")
        if c.get("document_type") == "gioi_thieu_nganh" and not (c.get("program_code") and c.get("faculty_code")):
            add("E", "E10 chunk ngành thiếu program_code/faculty_code", cid)
        n = len(c.get("text", ""))
        if n > 2500 or n < 80:
            add("W", "W2 độ dài bất thường", f"{cid}: {n} ký tự")

    if MANIFEST.exists():
        prev = set(MANIFEST.read_text(encoding="utf-8").split())
        now = {c.get("chunk_id") for c in chunks}
        for cid in sorted(prev - now)[:20]:
            add("W", "W1 chunk_id biến mất so với lần trước", cid)
        for cid in sorted(now - prev)[:20]:
            add("W", "W1 chunk_id mới so với lần trước", cid)

    # ------------------------------------------------------------------ CSV
    for name, rows in tables.items():
        cols = rows[0].keys() if rows else []
        std = ["dataset_version"] if name in LOOKUP_TABLES else CSV_STD
        for c in std:
            if c not in cols:
                add("E", "E11 CSV thiếu cột chuẩn", f"{name}: {c}")
        if name in LOOKUP_TABLES:
            continue
        for i, r in enumerate(rows, 2):
            where = f"{name}:{i}"
            if not str(r.get("source") or "").strip():
                add("E", "E12 CSV thiếu source", where)
            url = str(r.get("source_url") or "")
            if not URL_RE.match(url) and not (url == "" and r.get("verification_status") == "rule_derived"):
                add("E", "E12 CSV source_url không phải link", f"{where}: {url!r}")
            if not DATE_RE.match(str(r.get("collection_date") or "")):
                add("E", "E12 CSV collection_date sai", f"{where}: {r.get('collection_date')!r}")
            if r.get("verification_status") not in STATUSES:
                add("E", "E12 CSV verification_status ngoài từ vựng", f"{where}: {r.get('verification_status')!r}")
            if r.get("dataset_version") != DATASET_VERSION:
                add("E", "E12 CSV dataset_version sai", f"{where}: {r.get('dataset_version')!r}")
            if not re.fullmatch(r"20(2[2-6])", str(r.get("year") or "")):
                add("E", "E13 CSV year sai", f"{where}: {r.get('year')!r}")
        if name.startswith(("admission_scores_", "tuition_")):
            n = sum(1 for r in rows if r.get("verification_status") == "vision_extracted")
            if n:
                add("W", "W4 còn dòng vision_extracted ở bảng điểm/học phí (nên soát tay)", f"{name}: {n} dòng")
    return out


def report(issues) -> tuple[int, int]:
    from collections import defaultdict
    groups = defaultdict(list)
    for lvl, rule, msg in issues:
        groups[(lvl, rule)].append(msg)
    for (lvl, rule), msgs in sorted(groups.items()):
        print(f"  [{'LỖI' if lvl == 'E' else 'CẢNH BÁO'}] {rule}: {len(msgs)}  vd: {msgs[:3]}")
    return sum(len(v) for (l, _), v in groups.items() if l == "E"), sum(len(v) for (l, _), v in groups.items() if l == "W")


def selftest(chunks, tables) -> bool:
    """Moi truong hop: (mo ta, ham cai loi, ma luat phai bat)."""
    def ch(i, **kw):
        def f(c, t):
            c[i].update(kw)
        return f

    def ch_del(i, k):
        def f(c, t):
            del c[i][k]
        return f

    pdf_i = next(i for i, c in enumerate(chunks) if c["source_kind"] == "pdf_scan")
    web_i = next(i for i, c in enumerate(chunks) if c["source_kind"] == "web")
    nganh_i = next(i for i, c in enumerate(chunks) if c["document_type"] == "gioi_thieu_nganh")
    cases = [
        ("chunk_id trùng", lambda c, t: c[1].update(chunk_id=c[0]["chunk_id"]), "E1 chunk_id trùng"),
        ("chunk_id có chữ hoa/dấu", ch(0, chunk_id="QCDT::Điều1"), "E1 chunk_id sai định dạng"),
        ("khoá rác lọt vào (lỗi N1 cũ)", ch(0, stop_at="Phụ lục I"), "E7 trường ngoài từ điển / thiếu trường"),
        ("thiếu source_kind", ch(0, source_kind=""), "E2 thiếu trường Nhóm A"),
        ("bản scan mất page_no", ch(pdf_i, page_no=""), "E3 nguồn PDF thiếu page_no"),
        ("page_no ngược", ch(pdf_i, page_no="9-4"), "E3 page_no ngược"),
        ("document_type cũ chưa gộp", ch(0, document_type="tsa_cam_nang"), "E4 document_type ngoài từ vựng"),
        ("cohort lạ", ch(0, cohort="K69"), "E4 cohort ngoài từ vựng"),
        ("source_url là đường dẫn file", ch(0, source_url="data/raw/admission/x.pdf"), "E5 source_url không phải link"),
        ("chữ NFD", ch(web_i, text="Học phí"), "E6 chữ không phải NFC"),
        ("year dạng chuỗi", ch(0, year="2025"), "E8 year thiếu / không phải số năm"),
        ("dataset_version sai", ch(0, dataset_version="2026.0"), "E9 dataset_version sai"),
        ("mã ngành lạ", ch(nganh_i, program_code="XX9"), "E10 program_code không có trong danh mục"),
        ("chunk ngành mất faculty_code", ch(nganh_i, faculty_code=""), "E10 chunk ngành thiếu program_code/faculty_code"),
        ("chunk quá dài", ch(0, text="x" * 3000), "W2 độ dài bất thường"),
        ("CSV mất cột source", lambda c, t: [r.pop("source") for r in t["quotas_2026"]], "E11 CSV thiếu cột chuẩn"),
        ("CSV source_url là tên file", lambda c, t: t["tuition_credit"][0].update(source_url="2024_2_ QĐ học phí.pdf"),
         "E12 CSV source_url không phải link"),
        ("CSV verification_status lạ", lambda c, t: t["quotas_2026"][0].update(verification_status="ok"),
         "E12 CSV verification_status ngoài từ vựng"),
        ("CSV year trống", lambda c, t: t["quotas_2026"][0].update(year=""), "E13 CSV year sai"),
    ]
    ok = True
    for desc, inject, rule in cases:
        c2, t2 = copy.deepcopy(chunks), copy.deepcopy(tables)
        inject(c2, t2)
        caught = any(r == rule for _, r, _ in check(c2, t2))
        print(f"  {'✓' if caught else '✗ KHÔNG BẮT ĐƯỢC'}  {desc:32s} -> {rule}")
        ok &= caught
    return ok


def main() -> None:
    chunks, tables = load()
    if "--selftest" in sys.argv:
        base = [r for r in check(chunks, tables) if r[0] == "E"]
        if base:
            print("Dữ liệu gốc đang có lỗi — sửa trước rồi mới tự thử ngược.")
            report(base)
            sys.exit(1)
        print("Tự thử ngược (cài lỗi cố ý, validator phải bắt được):")
        sys.exit(0 if selftest(chunks, tables) else 1)
    print(f"{len(chunks)} chunk, {len(tables)} bảng CSV")
    errors, warns = report(check(chunks, tables))
    print(f"\n{errors} lỗi, {warns} cảnh báo")
    if errors == 0:
        MANIFEST.write_text("\n".join(sorted(c["chunk_id"] for c in chunks)) + "\n", encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
