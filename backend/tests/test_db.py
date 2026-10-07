"""Test nen cho lop DB (PLAN - Backend PostgreSQL (v1), buoc 4): khoa lai cac gia dinh ma moi tool dua vao.
Hong o day thi sua o day, dung doan loi qua test cua tung tool."""

import csv
import sys
from decimal import Decimal

import psycopg
import pytest

from app.core.config import ROOT
from app.db.pool import fetch_all, fetch_one, get_pool

sys.path.insert(0, str(ROOT / "scripts"))
from build_db import ALL_COMBINATIONS, csv_fingerprint  # noqa: E402

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]


async def test_db_khop_csv_hien_tai():
    """Sua CSV ma quen build lai -> tool tra so lieu cu nhung moi test van xanh (D10)."""
    info = await fetch_one("SELECT csv_sha256, git_commit, built_at FROM build_info")
    assert info is not None
    assert info["csv_sha256"] == csv_fingerprint(), (
        f"DB dựng lúc {info['built_at']} (commit {info['git_commit']}) cũ hơn CSV hiện tại. "
        "Chạy: python scripts/build_db.py --postgres")


async def test_cac_bang_chinh_co_du_lieu():
    for table in ("programs", "program_years", "admission_methods", "admission_scores",
                  "entity_aliases", "faculties", "faculty_units", "tuition_program"):
        row = await fetch_one(f"SELECT COUNT(*) AS n FROM {table}")  # type: ignore[arg-type]
        assert row["n"] > 0, table


async def test_ket_noi_chi_doc():
    """Tool lo chay lenh ghi thi Postgres tu choi (D9)."""
    async with get_pool().connection() as con:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            await con.execute("DELETE FROM admission_scores")


async def test_diem_chuan_khop_tung_dong_csv():
    """Moi dong diem chuan 2024-2026 trong DB bang dung so trong CSV — kiem kieu NUMERIC giu nguyen
    so (REAL 4 byte se bien 82.10 thanh 82.0999985, D6) va khoa tat_ca cho to hop rong."""
    db = {(r["program_code"], r["year"], r["method_code"], r["combination_group"]): r["score"]
          for r in await fetch_all("SELECT program_code, year, method_code, combination_group, score "
                                   "FROM admission_scores")}
    n = 0
    for path in sorted((ROOT / "data" / "processed").glob("admission_scores_*.csv")):
        for r in csv.DictReader(path.open(encoding="utf-8-sig", newline="")):
            key = (r["program_code"], int(r["year"]), r["method_code"], r["combination_group"] or ALL_COMBINATIONS)
            assert key in db, f"{path.name}: thiếu {key}"
            assert isinstance(db[key], Decimal)
            assert db[key] == Decimal(r["score"]), f"{key}: DB {db[key]} ≠ CSV {r['score']}"
            n += 1
    assert n == len(db)


async def test_loc_theo_danh_sach_ma():
    """Admission Tool nhan list toi da 3 ma (PRD 10.2) va truyen thang thanh mang Postgres."""
    rows = await fetch_all(
        "SELECT DISTINCT program_code FROM admission_scores "
        "WHERE program_code = ANY(%(codes)s) AND year = ANY(%(years)s)",
        {"codes": ["IT1", "IT2", "IT-E10"], "years": [2025]})
    assert {r["program_code"] for r in rows} == {"IT1", "IT2", "IT-E10"}


async def test_diem_mau_it_e10_2025():
    row = await fetch_one(
        "SELECT score, scale, source_url FROM admission_scores "
        "WHERE program_code = %s AND year = %s AND method_code = %s", ("IT-E10", 2025, "THPT"))
    assert row["score"] == Decimal("29.39") and row["scale"] == 30
    assert row["source_url"].startswith("https://ts.hust.edu.vn/")
