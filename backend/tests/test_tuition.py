"""T4 tuition_fees — cac ca da duyet (PLAN - T4 T5 hoc phi va chung chi (v1), muc A6)."""

import csv
from collections import defaultdict

import pytest
import pytest_asyncio

from app.core.config import ROOT
from app.schemas.common import ErrorCode, Status
from app.schemas.tuition import TuitionInput as In
from app.tools.common import TOO_MANY_MESSAGE
from app.tools.context import ToolContext
from app.tools.tuition import NEED_SCOPE_MESSAGE, to_vnd, tuition_fees

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]
PROCESSED = ROOT / "data" / "processed"
NN = {"ngoaingu-a1", "ngoaingu-a2", "ngoaingu-b1", "ngoaingu-b2", "ngoaingu-nangcao"}


def read(path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def call(dbctx, **kw):
    return await tuition_fees(In(**kw), dbctx)


def progs(res):
    return {p.program_code: p for p in res.data.programs}


def credit(res):
    return {r.rule_id.split("-", 1)[1]: r for r in res.data.credit_rules}


async def test_t4_01_it1(dbctx):
    res = await call(dbctx, programs=["IT1"])
    p = progs(res)["IT1"]
    assert res.status == Status.OK and (p.year, p.amount_min, p.amount_max, p.unit) == (2026, 28, 40, "triệu đồng/năm")


async def test_t4_02_troy_hoc_ky(dbctx):
    p = progs(await call(dbctx, programs=["TROY-IT"]))["TROY-IT"]
    assert (p.amount_min, p.unit, p.per, p.terms_per_year) == (33, "triệu đồng/học kỳ", "học kỳ", 3)
    assert p.unit_vnd == "đồng/học kỳ" and p.amount_vnd_min == 33_000_000      # khong co so /nam tu tinh (A5-T1)


async def test_t4_03_so_sanh_ba_nganh(dbctx):
    res = await call(dbctx, programs=["IT-E6", "IT-EP", "IT1"])
    got = {c: (p.amount_min, p.amount_max, p.unit) for c, p in progs(res).items()}
    assert got == {"IT-E6": (40, 50, "triệu đồng/năm"), "IT-EP": (40, 50, "triệu đồng/năm"),
                   "IT1": (28, 40, "triệu đồng/năm")}
    assert not hasattr(res.data, "deltas")          # A5-T3: khong tinh chenh lech


async def test_t4_04_hoc_phi_khoang(dbctx):
    p = progs(await call(dbctx, programs=["IT-E10"]))["IT-E10"]
    assert (p.amount_min, p.is_approximate, p.amount_text) == (68, True, "~ 68 triệu đồng/năm")


async def test_t4_05_elitech_tach_don_vi(dbctx):
    stats = {s.unit: s for s in (await call(dbctx, program_group="Elitech")).data.stats}
    assert (stats["triệu đồng/năm"].count, stats["triệu đồng/năm"].min, stats["triệu đồng/năm"].max) == (22, 35, 68)
    hk = stats["triệu đồng/học kỳ"]
    assert (hk.count, hk.min, hk.max, set(hk.program_codes)) == (4, 24, 30, {"ET-LUH", "ME-LUH", "ME-NUT", "ME-GU"})


async def test_t4_05b_pfiev_lay_het(dbctx):
    res = await call(dbctx, program_group="PFIEV")
    assert res.status != Status.AMBIGUOUS and set(progs(res)) == {"EE-EP", "IT-EP", "TE-EP"}
    assert [s.unit for s in res.data.stats] == ["triệu đồng/năm"]


async def test_t4_06_chuan_tin_chi_2026(dbctx):
    res = await call(dbctx, program_group="chương trình chuẩn", kinds=["credit"])
    c = credit(res)
    assert {k: v.amount_min for k, v in c.items() if k.startswith("chuan")} == \
        {"chuan-700": 700, "chuan-680": 680, "chuan-620": 620}
    assert all(v.academic_year == "2026-2027" for v in c.values())
    assert NN <= set(c) and all(c[k].applies_to_all for k in NN)
    assert "IT1" in c["chuan-700"].program_codes and "CH1" in c["chuan-620"].program_codes


@pytest.mark.parametrize("years,want", [([], (700, "2026-2027")), ([2025], (630, "2025-2026")),
                                        ([2024], (550, "2024-2025"))])
async def test_t4_07_it1_tin_chi_theo_nam(dbctx, years, want):
    """T4-07, T4-07b, T4-07c: dung nam hoc, khong dung chung (A5-T4)."""
    res = await call(dbctx, programs=["IT1"], kinds=["credit"], years=years)
    own = [r for r in res.data.credit_rules if not r.applies_to_all]
    assert [(r.amount_min, r.academic_year) for r in own] == [want]
    assert own[0].amount_vnd_min == want[0] * 1000 and own[0].unit_vnd == "đồng/tín chỉ"
    assert len([r for r in res.data.credit_rules if r.applies_to_all]) == 5


async def test_t4_07d_nam_chua_co(dbctx):
    res = await call(dbctx, programs=["IT1"], kinds=["credit"], years=[2027])
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "not_collected" and res.missing[0].available_years == [2024, 2025, 2026]


async def test_t4_08_troy_tin_chi(dbctx):
    res = await call(dbctx, programs=["TROY-IT"], kinds=["credit"])
    got = {r.cohort: (r.amount_min, r.unit, r.amount_vnd_min) for r in res.data.credit_rules}
    assert got == {"K71": (34000, "nghìn đồng/học kỳ", 34_000_000), "K70": (30000, "nghìn đồng/học kỳ", 30_000_000),
                   "K69": (28600, "nghìn đồng/học kỳ", 28_600_000), "<=K68": (26000, "nghìn đồng/học kỳ", 26_000_000)}
    assert not any(r.applies_to_all for r in res.data.credit_rules)            # A5-T10: khong kem ngoai ngu
    assert any("1,7 triệu" in n for n in res.data.notes)


async def test_t4_09_nhom_nam_hoc_2024(dbctx):
    res = await call(dbctx, programs=["IT1"], years=[2024], kinds=["year_rule"])
    r = res.data.year_rules
    assert [(x.amount_min, x.amount_max, x.unit, x.academic_year) for x in r] == [(24, 30, "triệu đồng/năm học", "2024-2025")]


async def test_t4_10_hoc_phi_nganh_2025_chua_co(dbctx):
    res = await call(dbctx, programs=["IT1"], years=[2025])
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "not_collected" and res.missing[0].available_years == [2026]
    assert any("tín chỉ" in n and "year_rule" in n for n in res.data.notes)


async def test_t4_11_em4_dung_tuyen(dbctx):
    res = await call(dbctx, programs=["EM4"])
    assert res.status == Status.NOT_FOUND
    assert any(m.reason == "program_not_open" and m.available_years == [2024, 2025] for m in res.missing)


async def test_t4_12_em4_nam_2024(dbctx):
    res = await call(dbctx, programs=["EM4"], years=[2024], kinds=["year_rule"])
    assert [(x.amount_min, x.amount_max) for x in res.data.year_rules] == [(24, 30)]


async def test_t4_13_le_phi_tuyen_sinh(dbctx):
    res = await call(dbctx, kinds=["fee"])
    fees = {f.fee_type: f for f in res.data.fees}
    assert len(fees) == 6 and all(f.year == 2024 for f in fees.values())
    tsa = fees["Lệ phí đăng ký dự thi Đánh giá tư duy"]
    assert (tsa.amount, tsa.unit, tsa.note) == (500000, "đồng", "Mỗi đợt thi")
    assert any("không phải học phí" in n for n in res.data.notes)


async def test_t4_14_le_phi_2026_khong_co(dbctx):
    res = await call(dbctx, kinds=["fee"], years=[2026])
    assert res.status == Status.NOT_FOUND and res.data.fees == []
    assert res.missing[0].available_years == [2024]


async def test_t4_15_mo_ho(dbctx):
    res = await call(dbctx, programs=["Khoa học máy tính"])
    assert res.status == Status.AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"IT1", "TROY-IT"}


async def test_t4_16_qua_ba_nganh(dbctx):
    res = await call(dbctx, programs=["IT1", "IT2", "MI1", "EM1"])
    assert res.status == Status.INVALID and res.message == TOO_MANY_MESSAGE


async def test_t4_17_thieu_pham_vi(dbctx):
    res = await call(dbctx, kinds=["program"])
    assert res.status == Status.INVALID and res.message == NEED_SCOPE_MESSAGE and res.error_code == ErrorCode.INVALID_REQUEST


async def test_t4_18_quet_toan_bo(dbctx):
    want = {r["program_code"]: (float(r["amount_min"]), float(r["amount_max"]), r["unit"])
            for r in read(PROCESSED / "tuition_2026.csv")}
    codes = sorted(want)
    got = {}
    for i in range(0, len(codes), 3):
        got |= {c: (p.amount_min, p.amount_max, p.unit) for c, p in progs(await call(dbctx, programs=codes[i:i + 3])).items()}
    assert got == want

    rule_year = {r["rule_id"]: int(r["year"]) for r in read(PROCESSED / "tuition_credit.csv")}
    members = defaultdict(set)
    for r in read(PROCESSED / "linking" / "tuition_rule_members.csv"):
        if r["rule_id"] in rule_year:
            members[(r["program_code"], rule_year[r["rule_id"]])].add(r["rule_id"])
    wrong = []
    for (code, year), rules in sorted(members.items()):
        if year not in dbctx.aliases.valid_years[code]:
            continue        # nganh chua mo / da chuyen nganh (EM4 -> EM-E17) nam do: anh chot khong tra (2026-10-09)
        res = await call(dbctx, programs=[code], kinds=["credit"], years=[year])
        own = {r.rule_id for r in (res.data.credit_rules if res.data else []) if not r.applies_to_all}
        if own != rules:
            wrong.append((code, year, sorted(rules - own), sorted(own - rules)))
    assert not wrong


async def test_t4_19_moi_so_tien_co_don_vi_va_doi_dung(dbctx):
    res = await call(dbctx, program_group="Elitech", kinds=["program", "credit"])
    fees = await call(dbctx, kinds=["fee"])
    for x in res.data.programs + res.data.credit_rules:
        assert x.unit and x.unit_vnd
        assert (x.amount_vnd_min, x.unit_vnd) == to_vnd(x.amount_min, x.unit)
    assert all(r.academic_year for r in res.data.credit_rules)
    assert all(f.unit for f in fees.data.fees)
    assert to_vnd(26000, "nghìn đồng/học kỳ") == (26_000_000, "đồng/học kỳ")
    assert to_vnd(33, "triệu đồng/học kỳ") == (33_000_000, "đồng/học kỳ")


@pytest.mark.parametrize("years,want", [([], ("EM-E17", 680, "2026-2027")), ([2025], ("EM4", 600, "2025-2026"))])
async def test_t4_20_ke_toan_theo_nam(dbctx, years, want):
    """Anh chot 2026-10-09: 'ke toan' khong noi nam -> EM-E17 (nam moi nhat); nhac 2025 -> EM4."""
    res = await call(dbctx, programs=["kế toán"], kinds=["credit"], years=years)
    own = [r for r in res.data.credit_rules if not r.applies_to_all]
    assert res.resolved[0].codes == [want[0]]
    assert [(r.amount_min, r.academic_year) for r in own] == [want[1:]]
