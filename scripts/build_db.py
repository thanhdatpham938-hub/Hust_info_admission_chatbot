"""Nap CSV (data/processed/ + data/processed/linking/) thanh SQLite theo PLAN - Data Linking (v1).

Mo hinh: muc 2 + 2.4 cua PLAN (bang danh muc khoa bang ma, bang so lieu khoa ghep, bang quy
dinh theo nhom co id doc duoc + bang cau). So do: muc 2.4.

DB la SAN PHAM SINH RA tu CSV — xoa va dung lai moi lan chay; sua du lieu chi sua CSV.
SQLite truoc (khong can server, dung duoc trong script kiem tra); sang PostgreSQL chi doi chuoi
ket noi + kieu cot (PLAN muc 5, R9).

Kiem tra ngay trong luc nap:
  - trung khoa chinh  -> liet ke het roi dung (khong dung o loi dau tien)
  - khoa ngoai mo coi -> PRAGMA foreign_key_check sau khi nap, liet ke het roi dung
  - ten chung chi / ten nhom nganh / ten Khoa khong doi duoc sang ma -> dung
Kiem tra lien ket logic (alias, chunk RAG, bang cau...) nam o validate_links.py.

PostgreSQL (PLAN - Backend PostgreSQL (v1)): SQLite van dung truoc lam cong kiem tra (D5); qua het
kiem tra moi nap cung cac dong do vao schema "hust" cua DATABASE_URL, trong MOT transaction (D4):
loi giua chung thi rollback, du lieu cu con nguyen. Schema "langgraph" (checkpointer) khong bi dung toi.

Dung: python scripts/build_db.py              -> data/db/hust.sqlite
      python scripts/build_db.py --postgres   -> data/db/hust.sqlite + Postgres (schema hust)
"""

import argparse
import csv
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
LINKING = PROCESSED / "linking"
DB_PATH = ROOT / "data" / "db" / "hust.sqlite"
PG_SCHEMA = "hust"

PROV = ["source", "source_url", "collection_date", "verification_status", "dataset_version"]
PROV_DDL = ", ".join(f"{c} TEXT" for c in PROV)

DDL = f"""
CREATE TABLE faculties (
  faculty_code TEXT PRIMARY KEY, faculty_name TEXT NOT NULL UNIQUE, official_channel_url TEXT,
  phone TEXT, email TEXT, address TEXT, contact_source_url TEXT, contact_note TEXT, {PROV_DDL});
CREATE TABLE faculty_units (
  faculty_code TEXT NOT NULL REFERENCES faculties(faculty_code), unit_name TEXT NOT NULL,
  unit_type TEXT NOT NULL CHECK (unit_type IN ('khoa', 'bo_mon', 'trung_tam')), note TEXT,
  source_url TEXT, verification_status TEXT, dataset_version TEXT,
  PRIMARY KEY (faculty_code, unit_name));
CREATE TABLE program_groups (
  program_group_code TEXT PRIMARY KEY, group_name TEXT NOT NULL);
CREATE TABLE programs (
  program_code TEXT PRIMARY KEY, program_name TEXT NOT NULL,
  faculty_code TEXT NOT NULL REFERENCES faculties(faculty_code),
  program_group_code TEXT REFERENCES program_groups(program_group_code),
  language TEXT, degree TEXT, duration TEXT, curriculum_url TEXT, short_description TEXT, {PROV_DDL});
CREATE TABLE program_years (
  program_code TEXT NOT NULL REFERENCES programs(program_code), year INTEGER NOT NULL, {PROV_DDL},
  PRIMARY KEY (program_code, year));
CREATE TABLE admission_methods (
  method_code TEXT PRIMARY KEY, method_name TEXT NOT NULL,
  parent_method TEXT REFERENCES admission_methods(method_code), scale INTEGER, note TEXT);
CREATE TABLE program_methods (
  program_code TEXT NOT NULL, year INTEGER NOT NULL,
  method_code TEXT NOT NULL REFERENCES admission_methods(method_code), {PROV_DDL},
  PRIMARY KEY (program_code, year, method_code),
  FOREIGN KEY (program_code, year) REFERENCES program_years(program_code, year));
CREATE TABLE combinations (
  combination_code TEXT PRIMARY KEY, subjects TEXT NOT NULL, {PROV_DDL});
CREATE TABLE scoring_formulas (
  formula_type TEXT NOT NULL, year INTEGER NOT NULL,
  method_code TEXT NOT NULL REFERENCES admission_methods(method_code),
  scale INTEGER, formula TEXT, note TEXT, {PROV_DDL},
  PRIMARY KEY (formula_type, year));
CREATE TABLE program_combinations (
  program_code TEXT NOT NULL, year INTEGER NOT NULL, method_code TEXT NOT NULL,
  combination_code TEXT NOT NULL REFERENCES combinations(combination_code),
  main_subject TEXT, formula_type TEXT, main_subject_status TEXT, note TEXT, {PROV_DDL},
  PRIMARY KEY (program_code, year, method_code, combination_code),
  FOREIGN KEY (program_code, year, method_code) REFERENCES program_methods(program_code, year, method_code),
  FOREIGN KEY (formula_type, year) REFERENCES scoring_formulas(formula_type, year));
CREATE TABLE admission_scores (
  program_code TEXT NOT NULL, year INTEGER NOT NULL,
  method_code TEXT NOT NULL REFERENCES admission_methods(method_code),
  combination_group TEXT NOT NULL, score REAL NOT NULL, scale INTEGER,
  subject_combinations TEXT, score_note TEXT, {PROV_DDL},
  PRIMARY KEY (program_code, year, method_code, combination_group),
  FOREIGN KEY (program_code, year) REFERENCES program_years(program_code, year));
CREATE TABLE quotas (
  program_code TEXT NOT NULL, year INTEGER NOT NULL, quota INTEGER, quota_type TEXT, {PROV_DDL},
  PRIMARY KEY (program_code, year),
  FOREIGN KEY (program_code, year) REFERENCES program_years(program_code, year));
CREATE TABLE tuition_program (
  program_code TEXT NOT NULL, year INTEGER NOT NULL, amount_min REAL, amount_max REAL, unit TEXT,
  is_approximate INTEGER, terms_per_year INTEGER, amount_text TEXT, {PROV_DDL},
  PRIMARY KEY (program_code, year),
  FOREIGN KEY (program_code, year) REFERENCES program_years(program_code, year));
CREATE TABLE tuition_rules (
  rule_id TEXT PRIMARY KEY, rule_type TEXT NOT NULL CHECK (rule_type IN ('nam', 'tin_chi')),
  year INTEGER NOT NULL, academic_year TEXT, group_text TEXT NOT NULL, course_type TEXT,
  cohort TEXT, applies_to_all INTEGER NOT NULL DEFAULT 0,
  amount_min REAL, amount_max REAL, unit TEXT, programs_text TEXT, note TEXT, {PROV_DDL});
CREATE TABLE tuition_rule_members (
  rule_id TEXT NOT NULL REFERENCES tuition_rules(rule_id),
  program_code TEXT NOT NULL REFERENCES programs(program_code),
  note TEXT, verification_status TEXT, dataset_version TEXT,
  PRIMARY KEY (rule_id, program_code));
CREATE TABLE language_requirements (
  req_id TEXT PRIMARY KEY, year INTEGER NOT NULL, cohort TEXT, group_text TEXT NOT NULL,
  main_language TEXT, degree_level TEXT, requirement TEXT, min_level_group TEXT,
  equivalence_table TEXT, note TEXT, {PROV_DDL});
CREATE TABLE language_req_members (
  req_id TEXT NOT NULL REFERENCES language_requirements(req_id),
  program_code TEXT NOT NULL REFERENCES programs(program_code),
  note TEXT, verification_status TEXT, dataset_version TEXT,
  PRIMARY KEY (req_id, program_code));
CREATE TABLE certificates (
  cert_code TEXT PRIMARY KEY, cert_name TEXT NOT NULL, language TEXT);
CREATE TABLE cert_bonus (
  cert_code TEXT NOT NULL REFERENCES certificates(cert_code), cert_value TEXT NOT NULL,
  table_purpose TEXT NOT NULL, year INTEGER NOT NULL, value_min REAL, value_max REAL,
  bonus_point INTEGER, converted_score_10 REAL, note TEXT, {PROV_DDL},
  PRIMARY KEY (cert_code, cert_value, table_purpose, year));
CREATE TABLE cert_cefr (
  cert_code TEXT NOT NULL REFERENCES certificates(cert_code), cert_value TEXT NOT NULL,
  year INTEGER NOT NULL, value_min REAL, value_max REAL, cefr_level TEXT, knlnn_level TEXT, {PROV_DDL},
  PRIMARY KEY (cert_code, cert_value, year));
CREATE TABLE cert_output (
  cert_code TEXT NOT NULL REFERENCES certificates(cert_code), cert_value TEXT NOT NULL,
  level TEXT NOT NULL, year INTEGER NOT NULL, value_min REAL, value_max REAL,
  level_group TEXT NOT NULL, note TEXT, {PROV_DDL},
  PRIMARY KEY (cert_code, cert_value, level, year));
CREATE TABLE admission_fees (
  fee_type TEXT NOT NULL, year INTEGER NOT NULL, amount INTEGER, unit TEXT, note TEXT, {PROV_DDL},
  PRIMARY KEY (fee_type, year));
CREATE TABLE entity_aliases (
  alias TEXT NOT NULL, entity_type TEXT NOT NULL, entity_code TEXT NOT NULL,
  alias_type TEXT, resolution TEXT, year INTEGER, note TEXT, dataset_version TEXT,
  PRIMARY KEY (alias, entity_type, entity_code));
"""

# Chi co o Postgres: de test biet DB co cu hon CSV khong (D10). SQLite khong can — luon dung lai ngay.
BUILD_INFO_DDL = """
CREATE TABLE build_info (
  built_at TEXT NOT NULL, git_commit TEXT, csv_sha256 TEXT NOT NULL, dataset_version TEXT);
"""


def pg_ddl(ddl: str) -> str:
    """DDL SQLite -> Postgres (D6). REAL cua Postgres la so thuc 4 byte (82.10 -> 82.0999985): sai khi so
    bang/tinh chenh lech diem -> NUMERIC. Khoa ngoai kiem luc COMMIT de thu tu nap khong quan trong
    (admission_methods.parent_method tro vao chinh bang do)."""
    ddl = re.sub(r"\bREAL\b", "NUMERIC", ddl)
    return re.sub(r"(REFERENCES \w+\([^)]*\))", r"\1 DEFERRABLE INITIALLY DEFERRED", ddl)

# Cot khoa chinh cua tung bang — dung de bao TRUNG KHOA truoc khi nap (sqlite chi bao dong dau)
PK = {
    "faculties": ["faculty_code"], "faculty_units": ["faculty_code", "unit_name"],
    "program_groups": ["program_group_code"],
    "programs": ["program_code"], "program_years": ["program_code", "year"],
    "admission_methods": ["method_code"],
    "program_methods": ["program_code", "year", "method_code"],
    "combinations": ["combination_code"], "scoring_formulas": ["formula_type", "year"],
    "program_combinations": ["program_code", "year", "method_code", "combination_code"],
    "admission_scores": ["program_code", "year", "method_code", "combination_group"],
    "quotas": ["program_code", "year"], "tuition_program": ["program_code", "year"],
    "tuition_rules": ["rule_id"], "tuition_rule_members": ["rule_id", "program_code"],
    "language_requirements": ["req_id"], "language_req_members": ["req_id", "program_code"],
    "certificates": ["cert_code"],
    "cert_bonus": ["cert_code", "cert_value", "table_purpose", "year"],
    "cert_cefr": ["cert_code", "cert_value", "year"],
    "cert_output": ["cert_code", "cert_value", "level", "year"],
    "admission_fees": ["fee_type", "year"],
    "entity_aliases": ["alias", "entity_type", "entity_code"],
}
# Cot khoa dang rong trong nguon nghia la "ap dung moi to hop" -> doi sang gia tri co ten (R12)
ALL_COMBINATIONS = "tat_ca"


class BuildError(Exception):
    pass


def read(path: Path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))


def years(prefix: str) -> list[tuple[int, list[dict]]]:
    out = []
    for p in sorted(PROCESSED.glob(f"{prefix}_*.csv")):
        m = re.fullmatch(rf"{prefix}_(\d{{4}})", p.stem)
        if m:
            out.append((int(m.group(1)), read(p)))
    return out


def num(v: str, kind=float):
    v = (v or "").strip()
    return kind(float(v)) if v else None


def prov(r: dict) -> dict:
    return {c: r.get(c, "") for c in PROV}


NUM = r"\d+(?:\.\d+)?"


def value_range(v: str) -> tuple[float | None, float | None]:
    """'5.5÷6.5' -> (5.5, 6.5); '5,5 - 6,5' -> (5.5, 6.5); '6.5' -> (6.5, 6.5); '≥ 7.0' / '>180' ->
    (7.0, None). Gia tri chu ('Level 3', 'B2 First...') hoac nhieu khoang ('6.0-6.5 / 7.0-7.5') ->
    (None, None). Cot so de SQL so sanh duoc ('IELTS 6.5 thuoc bac nao'); cert_value goc giu nguyen."""
    t = re.sub(r"(\d),(\d)", r"\1.\2", (v or "").strip())
    t = re.sub(r"\s*[÷–-]\s*", "-", t)
    if m := re.fullmatch(rf"({NUM})", t):
        return float(m.group(1)), float(m.group(1))
    if m := re.fullmatch(rf"({NUM})-({NUM})", t):
        return float(m.group(1)), float(m.group(2))
    if m := re.fullmatch(rf"(?:≥|>=|>)\s*({NUM})", t):
        return float(m.group(1)), None
    return None, None


def strip_new(name: str) -> str:
    """'Kế toán (CT tiên tiến) (mới)' -> 'Kế toán (CT tiên tiến)'. '(mới)' la trang thai theo
    nam (nam dau tuyen = nam nho nhat trong program_years), khong phai mot phan ten nganh."""
    return re.sub(r"\s*\(mới\)\s*$", "", name.strip())


def build_rows() -> dict[str, list[dict]]:
    T: dict[str, list[dict]] = {}

    # ---------------------------------------------------------------- danh muc
    fac = read(LINKING / "faculties.csv")
    # Lien he (PRD 15.1): tu muc "Don vi quan ly" tren trang nganh + data/link.md, cho lech da
    # duoc nguoi dung chot (2026-10-05) — ly do tung Khoa o cot contact_note
    T["faculties"] = [{k: r[k] for k in ("faculty_code", "faculty_name", "official_channel_url", "phone",
                                         "email", "address", "contact_source_url", "contact_note")}
                      | prov(r) for r in fac]
    fac_by_name = {r["faculty_name"]: r["faculty_code"] for r in fac}
    T["faculty_units"] = [{k: r[k] for k in ("faculty_code", "unit_name", "unit_type", "note", "source_url",
                                             "verification_status", "dataset_version")}
                          for r in read(LINKING / "faculty_units.csv")]

    groups = read(LINKING / "program_groups.csv")
    T["program_groups"] = [{"program_group_code": r["program_group_code"], "group_name": r["group_name"]}
                           for r in groups]
    group_by_text = {t: r["program_group_code"] for r in groups for t in r["source_texts"].split("|")}

    prog_years = years("programs")
    quota_years = years("quotas")
    group_of: dict[str, str] = {}
    for _, rows in sorted(quota_years):            # nam moi ghi de nam cu
        for r in rows:
            if r["program_group"] not in group_by_text:
                raise BuildError(f"nhóm ngành chưa có trong linking/program_groups.csv: {r['program_group']!r}")
            group_of[r["program_code"]] = group_by_text[r["program_group"]]
    overview = {r["program_code"]: r for r in read(PROCESSED / "program_overview_2026.csv")}

    canon: dict[str, dict] = {}
    for _, rows in sorted(prog_years, reverse=True):   # QD 1: ten chuan theo nam MOI NHAT (de an 2026)
        for r in rows:
            canon.setdefault(r["program_code"], r)
    T["programs"] = []
    for code, r in sorted(canon.items()):
        if r["faculty_name"] not in fac_by_name:
            raise BuildError(f"{code}: Trường/Khoa {r['faculty_name']!r} chưa có trong linking/faculties.csv")
        ov = overview.get(code, {})
        T["programs"].append({
            "program_code": code, "program_name": strip_new(r["program_name"]),
            "faculty_code": fac_by_name[r["faculty_name"]], "program_group_code": group_of.get(code),
            "language": ov.get("language"), "degree": ov.get("degree"), "duration": ov.get("duration"),
            "curriculum_url": ov.get("curriculum_url"), "short_description": ov.get("short_description"),
            **prov(r)})
    T["program_years"] = [{"program_code": r["program_code"], "year": y, **prov(r)}
                          for y, rows in prog_years for r in rows]

    T["admission_methods"] = [{"method_code": r["method_code"], "method_name": r["method_name"],
                               "parent_method": r["parent_method"] or None, "scale": num(r["scale"], int),
                               "note": r["note"]} for r in read(LINKING / "admission_methods.csv")]

    T["combinations"] = [{"combination_code": r["combination_code"], "subjects": r["subjects"], **prov(r)}
                         for r in read(PROCESSED / "subject_combinations_ref.csv")]
    T["scoring_formulas"] = [{"formula_type": r["formula_type"], "year": int(r["year"]),
                              "method_code": r["method_code"], "scale": num(r["scale"], int),
                              "formula": r["formula"], "note": r["note"], **prov(r)}
                             for r in read(PROCESSED / "scoring_formulas_2026.csv")]

    certs = read(LINKING / "certificates.csv")
    T["certificates"] = [{"cert_code": r["cert_code"], "cert_name": r["cert_name"], "language": r["language"]}
                         for r in certs]
    cert_by_name = {n: r["cert_code"] for r in certs for n in r["source_names"].split("|")}

    # ---------------------------------------------------------------- so lieu
    T["program_methods"] = [{"program_code": r["program_code"], "year": int(r["year"]),
                             "method_code": r["method_code"], **prov(r)}
                            for _, rows in years("program_methods") for r in rows]

    combos = read(PROCESSED / "subject_combinations_2026.csv")
    extra = read(LINKING / "program_combinations_extra.csv")     # L8: K00 cho FL1-FL4
    T["program_combinations"] = [{
        "program_code": r["program_code"], "year": int(r["year"]), "method_code": r["method_code"],
        "combination_code": r["combination_code"], "main_subject": r.get("main_subject") or None,
        "formula_type": r.get("formula_type") or None,
        "main_subject_status": r.get("main_subject_status") or None, "note": r.get("note", ""),
        **prov(r)} for r in combos + extra]

    T["admission_scores"] = [{
        "program_code": r["program_code"], "year": y, "method_code": r["method_code"],
        "combination_group": r["combination_group"] or ALL_COMBINATIONS,
        "score": num(r["score"]), "scale": num(r["scale"], int),
        "subject_combinations": r["subject_combinations"], "score_note": r["score_note"], **prov(r)}
        for y, rows in years("admission_scores") for r in rows]

    T["quotas"] = [{"program_code": r["program_code"], "year": y, "quota": num(r["quota"], int),
                    "quota_type": r["quota_type"], **prov(r)} for y, rows in quota_years for r in rows]

    T["tuition_program"] = [{
        "program_code": r["program_code"], "year": int(r["year"]),
        "amount_min": num(r["amount_min"]), "amount_max": num(r["amount_max"]), "unit": r["unit"],
        "is_approximate": num(r["is_approximate"], int), "terms_per_year": num(r["terms_per_year"], int),
        "amount_text": r["amount_text"], **prov(r)} for r in read(PROCESSED / "tuition_2026.csv")]

    # ---------------------------------------------------------------- quy dinh theo nhom + bang cau
    T["tuition_rules"] = [{
        "rule_id": r["rule_id"], "rule_type": "nam", "year": int(r["year"]),
        "academic_year": r["academic_year"], "group_text": r["program_group"], "course_type": None,
        "cohort": None, "applies_to_all": 0, "amount_min": num(r["amount_min"]),
        "amount_max": num(r["amount_max"]), "unit": r["unit"], "programs_text": r["program_codes"],
        "note": r["note"], **prov(r)} for r in read(PROCESSED / "tuition_by_year.csv")] + [{
        "rule_id": r["rule_id"], "rule_type": "tin_chi", "year": int(r["year"]),
        "academic_year": r["academic_year"], "group_text": r["program_group"],
        "course_type": r["course_type"], "cohort": r["cohort"] or None,
        "applies_to_all": int(r["applies_to_all"] or 0), "amount_min": num(r["amount"]),
        "amount_max": num(r["amount"]), "unit": r["unit"], "programs_text": r["programs_listed"],
        "note": r.get("note", ""), **prov(r)} for r in read(PROCESSED / "tuition_credit.csv")]
    T["tuition_rule_members"] = [{k: r[k] for k in
                                  ("rule_id", "program_code", "note", "verification_status", "dataset_version")}
                                 for r in read(LINKING / "tuition_rule_members.csv")]

    T["language_requirements"] = [{
        "req_id": r["req_id"], "year": int(r["year"]), "cohort": r["cohort"] or None,
        "group_text": r["program_group"], "main_language": r["main_language"],
        "degree_level": r["degree_level"], "requirement": r["requirement"],
        "min_level_group": r["min_level_group"] or None, "equivalence_table": r["equivalence_table"],
        "note": r["note"], **prov(r)} for r in read(PROCESSED / "language_exit_requirement_2026.csv")]
    T["language_req_members"] = [{k: r[k] for k in
                                  ("req_id", "program_code", "note", "verification_status", "dataset_version")}
                                 for r in read(LINKING / "language_req_members.csv")]

    def cert_code(name: str, table: str) -> str:
        if name not in cert_by_name:
            raise BuildError(f"{table}: chứng chỉ {name!r} chưa có trong linking/certificates.csv (cột source_names)")
        return cert_by_name[name]

    T["cert_bonus"] = [{
        "cert_code": cert_code(r["certificate"], "cert_bonus_conversion"), "cert_value": r["cert_value"],
        **dict(zip(("value_min", "value_max"), value_range(r["cert_value"]))),
        "table_purpose": r["table_purpose"], "year": int(r["year"]),
        "bonus_point": num(r["bonus_point"], int), "converted_score_10": num(r["converted_score_10"]),
        "note": r["note"], **prov(r)} for r in read(PROCESSED / "cert_bonus_conversion.csv")]
    T["cert_cefr"] = [{
        "cert_code": cert_code(r["certificate"], "cert_cefr_equivalence"), "cert_value": r["cert_value"],
        **dict(zip(("value_min", "value_max"), value_range(r["cert_value"]))),
        "year": int(r["year"]), "cefr_level": r["cefr_level"], "knlnn_level": r["knlnn_vn_level"], **prov(r)}
        for r in read(PROCESSED / "cert_cefr_equivalence.csv")]
    T["cert_output"] = [{
        "cert_code": cert_code(r["certificate"], "cert_equivalence_output_2026"), "cert_value": r["cert_value"],
        **dict(zip(("value_min", "value_max"), value_range(r["cert_value"]))),
        "level": r["level"], "year": int(r["year"]), "level_group": r["level_group"], "note": r["note"], **prov(r)}
        for r in read(PROCESSED / "cert_equivalence_output_2026.csv")]

    T["admission_fees"] = [{"fee_type": r["fee_type"], "year": int(r["year"]), "amount": num(r["amount"], int),
                            "unit": r["unit"], "note": r["note"], **prov(r)}
                           for r in read(PROCESSED / "admission_fees.csv")]
    T["entity_aliases"] = [{
        "alias": r["alias"], "entity_type": r["entity_type"], "entity_code": r["entity_code"],
        "alias_type": r["alias_type"], "resolution": r["resolution"], "year": num(r["year"], int),
        "note": r["note"], "dataset_version": r["dataset_version"]}
        for r in read(PROCESSED / "entity_aliases.csv")]
    return T


def duplicate_keys(T: dict[str, list[dict]]) -> list[str]:
    out = []
    for table, rows in T.items():
        c = Counter(tuple(r[k] for k in PK[table]) for r in rows)
        out += [f"{table}: trùng khoá {dict(zip(PK[table], k))} ({n} dòng)" for k, n in c.items() if n > 1]
    return out


def create(T: dict[str, list[dict]], path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(DDL)
    for table, rows in T.items():
        if not rows:
            continue
        cols = list(rows[0])
        con.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                        [tuple(r[c] for c in cols) for r in rows])
    con.commit()
    return con


def orphan_report(con: sqlite3.Connection) -> list[str]:
    """Moi khoa ngoai mo coi (nap voi foreign_keys OFF de liet ke het, khong dung o dong dau)."""
    out = []
    for table, rowid, parent, fkid in con.execute("PRAGMA foreign_key_check"):
        fk = [r for r in con.execute(f"PRAGMA foreign_key_list({table})") if r[0] == fkid]
        cols = [r[3] for r in fk]
        vals = con.execute(f"SELECT {', '.join(cols)} FROM {table} WHERE rowid = ?", (rowid,)).fetchone()
        out.append(f"{table}.({', '.join(cols)}) = {vals} không có trong {parent}")
    return out


def csv_fingerprint() -> str:
    """SHA-256 cua moi CSV nguon (data/processed/*.csv + linking/*.csv). Bo khac biet CRLF/LF: git tren
    Windows tu doi xuong dong khi checkout, khong phai du lieu doi. backend/tests goi lai ham nay."""
    h = hashlib.sha256()
    for p in sorted([*PROCESSED.glob("*.csv"), *LINKING.glob("*.csv")]):
        h.update(p.relative_to(PROCESSED).as_posix().encode())
        h.update(p.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def build_info(T: dict[str, list[dict]]) -> dict:
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    commit = git("rev-parse", "--short", "HEAD")
    if commit and git("status", "--porcelain", "--", "data/processed"):
        commit += "-dirty"                      # CSV dang sua chua commit: commit tren khong khop du lieu da nap
    versions = sorted({r["dataset_version"] for rows in T.values() for r in rows if r.get("dataset_version")})
    return {"built_at": datetime.now().astimezone().isoformat(timespec="seconds"), "git_commit": commit,
            "csv_sha256": csv_fingerprint(), "dataset_version": ",".join(versions)}


def load_env(path: Path = ROOT / ".env") -> None:
    """Doc .env vao os.environ (khong de bien da co). Khong dung python-dotenv de script khong them phu thuoc."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def create_pg(T: dict[str, list[dict]], url: str) -> dict[str, int]:
    """Nap vao schema hust trong mot transaction (D4); tra so dong tung bang doc lai tu Postgres."""
    import psycopg     # chi can khi --postgres: build SQLite khong phu thuoc thu vien nay

    # connect_timeout: Docker Desktop tat thi bao loi sau 10 giay thay vi treo (gap 2026-10-07)
    with psycopg.connect(url, connect_timeout=10) as con:
        with con.transaction():
            con.execute(f"DROP SCHEMA IF EXISTS {PG_SCHEMA} CASCADE")
            con.execute(f"CREATE SCHEMA {PG_SCHEMA}")
            con.execute(f"SET LOCAL search_path TO {PG_SCHEMA}")
            con.execute(pg_ddl(DDL) + BUILD_INFO_DDL)
            with con.cursor() as cur:
                for table, rows in [*T.items(), ("build_info", [build_info(T)])]:
                    if not rows:
                        continue
                    cols = list(rows[0])
                    cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                                    [tuple(r[c] for c in cols) for r in rows])
        # COMMIT xong (khoa ngoai DEFERRED da duoc kiem) moi dem lai
        return {t: con.execute(f"SELECT COUNT(*) FROM {PG_SCHEMA}.{t}").fetchone()[0] for t in T}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--postgres", action="store_true",
                    help="nap them vao Postgres (DATABASE_URL trong .env) sau khi SQLite qua kiem tra")
    args = ap.parse_args()
    try:
        T = build_rows()
    except BuildError as e:
        print(f"[LỖI] {e}")
        return 1
    dups = duplicate_keys(T)
    if dups:
        for d in dups:
            print(f"[LỖI] {d}")
        return 1
    con = create(T, DB_PATH)
    orphans = orphan_report(con)
    for o in orphans:
        print(f"[LỖI] khoá ngoại mồ côi: {o}")
    print(f"{DB_PATH.relative_to(ROOT)}")
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in T}
    for table, n in counts.items():
        print(f"  {table:24s} {n:5d}")
    con.close()
    print(f"\n{len(orphans)} khoá ngoại mồ côi")
    if orphans or not args.postgres:
        return 1 if orphans else 0

    # ---------------------------------------------------------------- Postgres (chi khi SQLite sach)
    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("[LỖI] thiếu DATABASE_URL (xem .env.example)")
        return 1
    try:
        pg_counts = create_pg(T, url)
    except Exception as e:      # loi ket noi / rang buoc: transaction da rollback, du lieu cu con nguyen
        print(f"[LỖI] nạp Postgres thất bại, đã rollback: {type(e).__name__}: {e}")
        return 1
    diff = [f"{t}: SQLite {counts[t]} ≠ Postgres {pg_counts[t]}" for t in T if counts[t] != pg_counts[t]]
    for d in diff:
        print(f"[LỖI] {d}")
    print(f"Postgres schema {PG_SCHEMA}: {len(T)} bảng + build_info, "
          f"{sum(pg_counts.values())} dòng, {'khớp' if not diff else 'LỆCH'} SQLite")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
