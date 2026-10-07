"""T1 admission_scores (PLAN - Entity Resolution + Admission Tool (v1), muc 3.3).
Gia tri ky vong tinh tu CSV ngay trong test, khong lay tu cot "Dap an mong doi" cua bo 120 cau."""

import csv
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.config import ROOT
from app.schemas.admission import AdmissionScoresInput as In
from app.schemas.common import ErrorCode, Status
from app.tools.admission import TOO_MANY_MESSAGE, admission_scores
from app.tools.context import ToolContext

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]


def csv_scores() -> list[dict]:
    out = []
    for path in sorted((ROOT / "data" / "processed").glob("admission_scores_*.csv")):
        out += list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    return out




@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def test_quet_toan_bo_du_lieu(dbctx):
    """AC1 tool accuracy 100%: MOI dong diem chuan trong CSV phai lay lai dung qua T1."""
    rows = csv_scores()
    wrong = []
    keys = {(r["program_code"], int(r["year"]), r["method_code"]) for r in rows}
    got_all = {}
    for code, year, method in sorted(keys):
        res = await admission_scores(In(programs=[code], years=[year], methods=[method]), dbctx)
        for row in res.data.rows if res.data else []:
            got_all[(row.program_code, row.year, row.method_code, row.combination_group)] = row
    for r in rows:
        k = (r["program_code"], int(r["year"]), r["method_code"], r["combination_group"] or "tat_ca")
        row = got_all.get(k)
        if row is None or Decimal(str(row.score)) != Decimal(r["score"]) or row.scale != int(r["scale"]):
            wrong.append(k)
    assert len(rows) == 687 and not wrong


async def test_q26_it1_thpt_hai_nam(dbctx):
    res = await admission_scores(In(programs=["IT1"], years=[2024, 2025], methods=["THPT"]), dbctx)
    assert res.status == Status.OK
    want = {(int(r["year"]), r["combination_group"] or "tat_ca", Decimal(r["score"])) for r in csv_scores()
            if r["program_code"] == "IT1" and r["method_code"] == "THPT" and r["year"] in ("2024", "2025")}
    assert {(r.year, r.combination_group, Decimal(str(r.score))) for r in res.data.rows} == want
    for d in res.data.deltas:          # chi so cung khoi to hop (A1)
        assert d.kind == "year" and d.program_code == "IT1"
        assert d.diff == pytest.approx(d.value_b - d.value_a, abs=0.005)


async def test_q30_hai_nganh_ba_nam(dbctx):
    res = await admission_scores(In(programs=["IT1", "IT2"], years=[2024, 2025, 2026], methods=["THPT"]), dbctx)
    assert res.status == Status.OK
    assert {r.program_code for r in res.data.rows} == {"IT1", "IT2"}
    prog = [d for d in res.data.deltas if d.kind == "program"]
    assert prog and all((d.a, d.b) == ("IT1", "IT2") for d in prog)
    for d in prog:
        assert d.diff == pytest.approx(d.value_b - d.value_a, abs=0.005)


async def test_ten_mo_ho_phai_hoi_lai_va_khong_truy_van(dbctx):
    res = await admission_scores(In(programs=["Khoa học máy tính"]), dbctx)
    assert res.status == Status.AMBIGUOUS and res.error_code == ErrorCode.ENTITY_AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"IT1", "TROY-IT"}
    assert res.data is None


async def test_qua_ba_nganh(dbctx):
    res = await admission_scores(In(programs=["IT1", "IT2", "MI1", "EM1"]), dbctx)
    assert res.status == Status.INVALID and res.message == TOO_MANY_MESSAGE


async def test_nhom_nganh_chuyen_sang_list_programs(dbctx):
    res = await admission_scores(In(programs=["Elitech"]), dbctx)
    assert res.status == Status.INVALID and "list_programs" in res.message


async def test_nganh_dung_tuyen(dbctx):
    res = await admission_scores(In(programs=["EM4"], years=[2026]), dbctx)
    assert res.status == Status.NOT_FOUND
    assert any(m.reason == "program_not_open" and m.available_years == [2024, 2025] for m in res.missing)


async def test_nam_ngoai_pham_vi(dbctx):
    res = await admission_scores(In(programs=["IT1"], years=[2020]), dbctx)
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "year_out_of_range" and res.missing[0].available_years == [2024, 2025, 2026]


async def test_mot_nam_ngoai_pham_vi_van_tra_nam_con_lai(dbctx):
    res = await admission_scores(In(programs=["IT1"], years=[2020, 2025], methods=["THPT"]), dbctx)
    assert res.status == Status.PARTIAL and {r.year for r in res.data.rows} == {2025}


async def test_xttn_nam_2024_khong_co_diem(dbctx):
    res = await admission_scores(In(programs=["IT1"], years=[2024], methods=["tài năng"]), dbctx)
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "method_no_score" and res.missing[0].available_years == [2025, 2026]


async def test_xttn_mo_thanh_ma_con(dbctx):
    res = await admission_scores(In(programs=["IT1"], years=[2025], methods=["XTTN"]), dbctx)
    assert {r.method_code for r in res.data.rows} == {"XTTN_1.2", "XTTN_1.3"}


async def test_khong_noi_nam_lay_nam_moi_nhat(dbctx):
    res = await admission_scores(In(programs=["IT1"]), dbctx)
    assert {r.year for r in res.data.rows} == {2026}
    assert res.resolved[0].codes == ["IT1"]


async def test_alias_phuong_thuc_tsa(dbctx):
    res = await admission_scores(In(programs=["IT-E10"], years=[2025], methods=["TSA"]), dbctx)
    assert {r.method_code for r in res.data.rows} == {"DGTD"} and res.data.rows[0].scale == 100


async def test_hai_khoi_khong_so_voi_nhau(dbctx):
    res = await admission_scores(In(programs=["FL3"], years=[2025], methods=["THPT"]), dbctx)
    groups = {r.combination_group: r for r in res.data.rows}
    assert set(groups) == {"ky_thuat", "kinh_te_gd_nn"}
    assert groups["ky_thuat"].is_rule_derived
    assert groups["ky_thuat"].combination_group_label == "tổ hợp khối ngành kỹ thuật"
    assert not res.data.deltas


async def test_nguon_du_cho_moi_dong(dbctx):
    res = await admission_scores(In(programs=["IT1", "IT2"], years=[2024, 2025]), dbctx)
    urls = {s.url for s in res.sources}
    assert all(r.source.url in urls for r in res.data.rows)


async def test_khong_tim_thay_nganh(dbctx):
    res = await admission_scores(In(programs=["ngành không tồn tại xyz"]), dbctx)
    assert res.status == Status.NOT_FOUND and res.error_code == ErrorCode.ENTITY_NOT_FOUND
