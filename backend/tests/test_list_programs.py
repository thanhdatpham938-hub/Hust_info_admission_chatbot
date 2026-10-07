"""T2 list_programs (PLAN - Entity Resolution + Admission Tool (v1), muc 4.3).
Gia tri ky vong tinh tu CSV ngay trong test."""

import csv
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.config import ROOT
from app.schemas.admission import ListProgramsInput as In
from app.schemas.common import Status
from app.tools.admission import list_programs
from app.tools.context import ToolContext

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]
PROCESSED = ROOT / "data" / "processed"


def read(name: str) -> list[dict]:
    return list(csv.DictReader((PROCESSED / name).open(encoding="utf-8-sig", newline="")))


def scores(year: int, method: str) -> list[dict]:
    return [r for r in read(f"admission_scores_{year}.csv") if r["method_code"] == method]


def faculty_of(tables) -> dict[str, str]:
    return {r["program_code"]: r["faculty_code"] for r in tables["programs"]}


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def test_q27_top5_tsa_nam_moi_nhat(dbctx):
    res = await list_programs(In(metric="score", method="TSA", limit=5), dbctx)
    rows = scores(2026, "DGTD")
    vals = [Decimal(r["score"]) for r in rows]
    # RANK(): hang = 1 + so dong co diem cao hon han; lay moi dong hang <= 5
    want = {(r["program_code"], r["combination_group"] or "tat_ca") for r, v in zip(rows, vals)
            if 1 + sum(x > v for x in vals) <= 5}
    assert res.status == Status.OK
    assert {(r.program_code, r.combination_group) for r in res.data.rows} == want
    assert [r.rank for r in res.data.rows] == sorted(r.rank for r in res.data.rows)
    assert res.data.truncated and res.data.total_rows == len(rows)


async def test_q28_ca_bang_dgtd_2025(dbctx):
    res = await list_programs(In(metric="score", method="DGTD", years=[2025], limit=None), dbctx)
    assert len(res.data.rows) == len(scores(2025, "DGTD")) == 65
    assert not res.data.truncated


async def test_q32_thap_nhat_moi_phuong_thuc(dbctx):
    res = await list_programs(In(metric="score", years=[2025], order="asc", limit=1), dbctx)
    by_method = {}
    for r in res.data.rows:
        by_method.setdefault(r.method_code, set()).add(Decimal(str(r.value)))
    assert set(by_method) == {"THPT", "DGTD", "XTTN_1.2", "XTTN_1.3"}
    for m, vals in by_method.items():
        assert vals == {min(Decimal(r["score"]) for r in scores(2025, m))}


async def test_q31_truong_dien_ba_nam(dbctx, tables):
    res = await list_programs(In(metric="score", faculty="Trường Điện - Điện tử", method="THPT",
                                 years=[2024, 2025, 2026], limit=None), dbctx)
    fac = faculty_of(tables)
    assert res.data.rows and all(r.faculty_code == "SEEE" for r in res.data.rows)
    want = sum(1 for y in (2024, 2025, 2026) for r in scores(y, "THPT") if fac.get(r["program_code"]) == "SEEE")
    assert len(res.data.rows) == want
    assert any(d.kind == "year" for d in res.data.deltas)


async def test_q33_khoang_diem_truong_vat_lieu(dbctx, tables):
    res = await list_programs(In(metric="score", faculty="Trường Vật liệu", method="THPT", years=[2025]), dbctx)
    fac = faculty_of(tables)
    vals = [Decimal(r["score"]) for r in scores(2025, "THPT") if fac.get(r["program_code"]) == "SMSE"]
    st = res.data.stats[0]
    assert (Decimal(str(st.min)), Decimal(str(st.max)), st.count) == (min(vals), max(vals), len(vals))


async def test_loc_nhom_elitech(dbctx):
    res = await list_programs(In(metric="score", program_group="Elitech", method="DGTD", limit=None), dbctx)
    assert res.data.rows and all(r.program_group_code == "elitech" for r in res.data.rows)


async def test_loc_to_hop_d01(dbctx):
    res = await list_programs(In(metric="score", combination="d01", method="THPT", limit=None), dbctx)
    want = {(r["program_code"], r["combination_group"] or "tat_ca") for r in scores(2026, "THPT")
            if "D01" in r["subject_combinations"].split(";")}
    assert {(r.program_code, r.combination_group) for r in res.data.rows} == want


async def test_to_hop_nam_2024_co_ghi_chu(dbctx):
    res = await list_programs(In(metric="score", combination="A00", method="THPT", years=[2024]), dbctx)
    assert any("2024" in n for n in res.data.notes)


async def test_q37_tong_chi_tieu_hai_nam(dbctx):
    res = await list_programs(In(metric="quota", years=[2025, 2026], limit=None), dbctx)
    totals = {s.year: s.total for s in res.data.stats}
    want = {y: float(sum(int(r["quota"]) for r in read(f"quotas_{y}.csv") if r["quota"])) for y in (2025, 2026)}
    assert totals == want
    d = [d for d in res.data.deltas if d.kind == "total"][0]
    assert (d.a, d.b, d.diff) == ("2025", "2026", want[2026] - want[2025])


async def test_chi_tieu_2024_khong_co(dbctx):
    res = await list_programs(In(metric="quota", years=[2024]), dbctx)
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "year_out_of_range" and res.missing[0].available_years == [2025, 2026]


async def test_q36_chi_tieu_theo_phuong_thuc_chua_co(dbctx):
    res = await list_programs(In(metric="quota", programs=["IT2"], method="tài năng"), dbctx)
    assert res.status == Status.PARTIAL
    assert res.data.rows[0].program_code == "IT2"
    assert any(m.reason == "not_collected" for m in res.missing)


async def test_q43_nganh_khong_xet_thpt(dbctx):
    res = await list_programs(In(metric="quota", without_method="THPT", years=[2026], limit=None), dbctx)
    with_thpt = {r["program_code"] for r in read("program_methods_2026.csv") if r["method_code"] == "THPT"}
    want = {r["program_code"] for r in read("quotas_2026.csv") if r["quota"] and r["program_code"] not in with_thpt}
    assert {r.program_code for r in res.data.rows} == want


async def test_ten_mo_ho_lay_het_ung_vien(dbctx):
    """T2-3: T2 la liet ke, moi dong ghi ro ma -> lay du 7 nganh CNTT thay vi hoi lai."""
    res = await list_programs(In(metric="score", programs=["BK CNTT"], method="DGTD", years=[2025],
                                 score_max=90, limit=None), dbctx)
    assert res.status == Status.OK
    assert {r.program_code for r in res.data.rows} <= {"IT1", "IT2", "IT-E6", "IT-E7", "IT-E10", "IT-E15", "IT-EP"}
    assert all(r.value <= 90 for r in res.data.rows)


async def test_limit_qua_lon(dbctx):
    assert (await list_programs(In(metric="score", limit=500), dbctx)).status == Status.INVALID
