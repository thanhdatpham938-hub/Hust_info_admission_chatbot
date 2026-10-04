"""Kiem tra lien ket giua cac bang trong data/db/hust.sqlite (sinh boi build_db.py) va voi chunk RAG.

Luat theo PLAN - Data Linking (v1), muc 4 (cap nhat 2026-10-04). E = loi, W = canh bao.
Khoa ngoai THAT da do build_db.py chan; o day kiem lai (E1) va kiem cac lien ket LOGIC ma
mot khoa ngoai khong dien ta duoc: alias tro nhieu loai bang, chunk RAG nam o Qdrant, bac
ngoai ngu toi thieu, phuong thuc cap cha/cap con.

--selftest: cai loi co y vao BAN SAO cua DB (trong bo nho) va cua danh sach chunk, xac nhan
moi luat bat duoc. Ly do (giong validate_metadata.py): validator chay sach chi co nghia khi da
chung minh no bat duoc loi.

Dung: python scripts/build_db.py && python scripts/validate_links.py [--selftest]
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "db" / "hust.sqlite"
NORM = ROOT / "data" / "rag" / "normalized"

ALIAS_TARGET = {"program": ("programs", "program_code"), "faculty": ("faculties", "faculty_code"),
                "certificate": ("certificates", "cert_code"),
                "program_group": ("program_groups", "program_group_code")}


def load_chunks() -> list[dict]:
    return [json.loads(l) for f in sorted(NORM.glob("*.chunks.jsonl")) for l in f.open(encoding="utf-8")]


def check(con: sqlite3.Connection, chunks: list[dict]) -> list[tuple[str, str, str]]:
    out = []
    add = lambda lvl, rule, msg: out.append((lvl, rule, msg))
    q = lambda sql, *a: con.execute(sql, a).fetchall()

    # E1 khoa ngoai mo coi
    for table, rowid, parent, _ in q("PRAGMA foreign_key_check"):
        add("E", "E1 khoá ngoại mồ côi", f"{table} rowid={rowid} -> {parent}")

    # E2 ten nganh chi song o bang programs (L2 khong duoc tai phat)
    for (table,) in q("SELECT name FROM sqlite_master WHERE type='table' AND name != 'programs'"):
        if any(c[1] == "program_name" for c in q(f"PRAGMA table_info({table})")):
            add("E", "E2 program_name ngoài bảng programs", table)

    # E3 alias tro toi ma ton tai, dung loai bang
    for alias, etype, code in q("SELECT alias, entity_type, entity_code FROM entity_aliases"):
        if etype not in ALIAS_TARGET:
            add("E", "E3 alias trỏ tới mã không tồn tại", f"{alias!r}: entity_type lạ {etype!r}")
            continue
        table, key = ALIAS_TARGET[etype]
        if not q(f"SELECT 1 FROM {table} WHERE {key} = ?", code):
            add("E", "E3 alias trỏ tới mã không tồn tại", f"{alias!r} -> {etype} {code!r}")

    # E4 chunk RAG <-> danh muc SQL (noi bang ma trong payload Qdrant)
    fac_of = dict(q("SELECT program_code, faculty_code FROM programs"))
    faculties = {r[0] for r in q("SELECT faculty_code FROM faculties")}
    for c in chunks:
        pc, fc = c.get("program_code", ""), c.get("faculty_code", "")
        if pc and pc not in fac_of:
            add("E", "E4 chunk trỏ tới mã không có trong DB", f"{c['chunk_id']}: program_code {pc}")
        if fc and fc not in faculties:
            add("E", "E4 chunk trỏ tới mã không có trong DB", f"{c['chunk_id']}: faculty_code {fc}")
        if pc in fac_of and fc and fc != fac_of[pc]:
            add("E", "E4b chunk ngành lệch Trường/Khoa với DB", f"{c['chunk_id']}: {pc} chunk={fc} DB={fac_of[pc]}")

    # E5 bac ngoai ngu toi thieu phai co trong bang tuong duong chuan dau ra
    levels = {r[0] for r in q("SELECT DISTINCT level_group FROM cert_output")}
    for req, lvl in q("SELECT req_id, min_level_group FROM language_requirements WHERE min_level_group IS NOT NULL"):
        if lvl not in levels:
            add("E", "E5 min_level_group không có trong cert_output", f"{req}: {lvl!r}")

    # E6 (L3) diem chuan theo phuong thuc con -> nganh phai co phuong thuc cap cha trong nam do.
    # Chi xet nam CO bang phuong thuc (2024 khong co — bao o W1, khong bao tung dong)
    years_with_methods = {r[0] for r in q("SELECT DISTINCT year FROM program_methods")}
    for code, year, method in q("""
        SELECT s.program_code, s.year, s.method_code FROM admission_scores s
        JOIN admission_methods m ON m.method_code = s.method_code
        WHERE NOT EXISTS (SELECT 1 FROM program_methods p WHERE p.program_code = s.program_code
              AND p.year = s.year AND p.method_code = COALESCE(m.parent_method, m.method_code))"""):
        if year in years_with_methods:
            add("E", "E6 điểm chuẩn có phương thức mà ngành không xét", f"{code} {year} {method}")

    # W1 du lieu thung theo (nganh, nam)
    for table, label in (("quotas", "chỉ tiêu"), ("admission_scores", "điểm chuẩn"), ("program_methods", "phương thức")):
        miss = defaultdict(list)
        for code, year in q(f"""SELECT program_code, year FROM program_years y WHERE NOT EXISTS
                (SELECT 1 FROM {table} t WHERE t.program_code = y.program_code AND t.year = y.year)"""):
            miss[year].append(code)
        for year, codes in sorted(miss.items()):
            total = q("SELECT COUNT(*) FROM program_years WHERE year = ?", year)[0][0]
            what = "cả năm không có bảng" if len(codes) == total else ", ".join(sorted(codes)[:8])
            add("W", f"W1 thiếu {label}", f"{year}: {len(codes)}/{total} ngành ({what})")

    # W2 (L8) nganh xet THPT/DGTD nam 2026 phai co to hop cua phuong thuc do (to hop chi co 2026 — L9)
    for code, method in q("""SELECT program_code, method_code FROM program_methods p
            WHERE year = 2026 AND method_code IN ('THPT', 'DGTD') AND NOT EXISTS
            (SELECT 1 FROM program_combinations c WHERE c.program_code = p.program_code
             AND c.year = p.year AND c.method_code = p.method_code)"""):
        add("W", "W2 có phương thức mà không có tổ hợp", f"{code} {method}")

    # W3 (L7) moi nganh dang tuyen 2026 va moi Khoa co it nhat 1 alias
    for (code,) in q("""SELECT program_code FROM program_years WHERE year = 2026 AND program_code NOT IN
            (SELECT entity_code FROM entity_aliases WHERE entity_type = 'program')"""):
        add("W", "W3 không có alias", f"ngành {code}")
    for (code,) in q("""SELECT faculty_code FROM faculties WHERE faculty_code NOT IN
            (SELECT entity_code FROM entity_aliases WHERE entity_type = 'faculty')"""):
        add("W", "W3 không có alias", f"Khoa {code}")

    # W4 (L5) bang cau phu het nganh trong pham vi ap dung
    for (code,) in q("""SELECT program_code FROM program_years WHERE year = 2026 AND program_code NOT IN
            (SELECT program_code FROM language_req_members)"""):
        add("W", "W4 ngành chưa gán vào bảng cầu", f"chuẩn đầu ra ngoại ngữ 2026: {code}")
    # Hoc phi theo nam: chi cac nganh co trong nam hoc 2024-2025. Hoc phi tin chi: MOI nganh, vi
    # nguoi dung chot dung chung bang tin chi 2024-2025 cho cac nam (2026-10-04)
    for rtype, yrs in (("nam", (2024, 2025)), ("tin_chi", (2024, 2025, 2026))):
        for (code,) in q(f"""SELECT DISTINCT program_code FROM program_years WHERE year IN ({', '.join('?' * len(yrs))})
                AND program_code NOT IN (SELECT m.program_code FROM tuition_rule_members m
                JOIN tuition_rules r ON r.rule_id = m.rule_id WHERE r.rule_type = ?)""", *yrs, rtype):
            add("W", "W4 ngành chưa gán vào bảng cầu", f"học phí {rtype}: {code}")
    return out


def report(issues) -> tuple[int, int]:
    groups = defaultdict(list)
    for lvl, rule, msg in issues:
        groups[(lvl, rule)].append(msg)
    for (lvl, rule), msgs in sorted(groups.items()):
        print(f"  [{'LỖI' if lvl == 'E' else 'CẢNH BÁO'}] {rule}: {len(msgs)}  vd: {msgs[:4]}")
    return (sum(len(v) for (l, _), v in groups.items() if l == "E"),
            sum(len(v) for (l, _), v in groups.items() if l == "W"))


def selftest(src: sqlite3.Connection, chunks: list[dict]) -> bool:
    nganh = next(c for c in chunks if c.get("program_code"))
    cases = [
        ("điểm chuẩn của mã ngành lạ", "INSERT INTO admission_scores (program_code, year, method_code, combination_group, score) VALUES ('XX9', 2026, 'THPT', 'tat_ca', 25)", None, "E1 khoá ngoại mồ côi"),
        ("ngành gán mã Khoa lạ", "UPDATE programs SET faculty_code = 'ABC' WHERE program_code = 'TE1'", None, "E1 khoá ngoại mồ côi"),
        ("bảng số liệu có lại program_name", "ALTER TABLE quotas ADD COLUMN program_name TEXT", None, "E2 program_name ngoài bảng programs"),
        ("alias Khoa trỏ mã lạ", "INSERT INTO entity_aliases VALUES ('Viện X', 'faculty', 'NOPE', 'old_name', 'unique', 2026, '', '')", None, "E3 alias trỏ tới mã không tồn tại"),
        ("chunk mang mã ngành lạ", None, lambda cs: cs.append(dict(nganh, chunk_id="nganh::xx9-1", program_code="XX9")), "E4 chunk trỏ tới mã không có trong DB"),
        ("chunk ngành lệch Khoa (lỗi TE1 cũ)", None, lambda cs: cs.append(dict(nganh, chunk_id="nganh::te1-9", program_code="TE1", faculty_code="FED")), "E4b chunk ngành lệch Trường/Khoa với DB"),
        ("bậc ngoại ngữ không tồn tại", "UPDATE language_requirements SET min_level_group = 'Bậc 9' WHERE req_id = 'nn2026-chuan'", None, "E5 min_level_group không có trong cert_output"),
        ("mất phương thức cấp cha (L3)", "DELETE FROM program_methods WHERE program_code = 'IT1' AND year = 2026 AND method_code = 'XTTN'", None, "E6 điểm chuẩn có phương thức mà ngành không xét"),
        ("thiếu chỉ tiêu 1 ngành", "DELETE FROM quotas WHERE program_code = 'IT1' AND year = 2026", None, "W1 thiếu chỉ tiêu"),
        ("bỏ dòng K00 của FL1 (L8)", "DELETE FROM program_combinations WHERE program_code = 'FL1' AND method_code = 'DGTD'", None, "W2 có phương thức mà không có tổ hợp"),
        ("Khoa mất hết alias", "DELETE FROM entity_aliases WHERE entity_type = 'faculty' AND entity_code = 'SEP'", None, "W3 không có alias"),
        ("ngành rơi khỏi bảng cầu ngoại ngữ", "DELETE FROM language_req_members WHERE program_code = 'IT1'", None, "W4 ngành chưa gán vào bảng cầu"),
    ]
    ok = True
    for desc, sql, mutate_chunks, rule in cases:
        con = sqlite3.connect(":memory:")
        src.backup(con)
        cs = list(chunks)
        if sql:
            con.execute(sql)
        if mutate_chunks:
            mutate_chunks(cs)
        caught = any(r == rule for _, r, _ in check(con, cs))
        print(f"  {'✓' if caught else '✗ KHÔNG BẮT ĐƯỢC'}  {desc:36s} -> {rule}")
        ok &= caught
        con.close()
    return ok


def main() -> int:
    if not DB_PATH.exists():
        print("Chưa có DB — chạy python scripts/build_db.py trước")
        return 1
    con = sqlite3.connect(DB_PATH)
    chunks = load_chunks()
    if "--selftest" in sys.argv:
        base = [r for r in check(con, chunks) if r[0] == "E"]
        if base:
            print("Dữ liệu gốc đang có lỗi — sửa trước rồi mới tự thử ngược.")
            report(base)
            return 1
        print("Tự thử ngược (cài lỗi cố ý, validator phải bắt được):")
        return 0 if selftest(con, chunks) else 1
    print(f"{DB_PATH.relative_to(ROOT)} + {len(chunks)} chunk")
    errors, warns = report(check(con, chunks))
    print(f"\n{errors} lỗi, {warns} cảnh báo")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
