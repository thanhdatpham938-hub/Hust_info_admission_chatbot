"""T3 program_info — 18 ca da duoc nguoi dung duyet (PLAN - T3 program_info (v1), muc 6).
Gia tri ky vong lay tu bang duyet; phan quet toan bo so thang voi CSV."""

import csv

import pytest
import pytest_asyncio

from app.core.config import ROOT
from app.schemas.common import ErrorCode, Status
from app.schemas.program_info import ProgramInfoInput as In
from app.tools.common import TOO_MANY_MESSAGE
from app.tools.context import ToolContext
from app.tools.program_info import program_info

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]
PROCESSED = ROOT / "data" / "processed"
SCORE_2026_URL = "https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026"


def read(path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def call(dbctx, **kw):
    return await program_info(In(**kw), dbctx)


def one(res):
    assert res.data and len(res.data.programs) == 1
    return res.data.programs[0]


def combos(p):
    return {(c.method_code, c.combination_code): c for c in p.combinations}


async def test_t3_01_it1_day_du(dbctx):
    res = await call(dbctx, programs=["IT1"])
    assert res.status == Status.OK
    p = one(res)
    assert (p.faculty_code, p.program_group_code) == ("SOICT", "chuan")
    assert (p.overview.language, p.overview.duration, p.overview.as_of_year) == ("Tiếng Việt", "4 - 5,5 năm", 2026)
    assert [(q.year, q.quota) for q in p.quotas] == [(2026, 300)]
    assert {m.method_code for m in p.methods} == {"DGTD", "THPT", "XTTN"}
    c = combos(p)
    assert set(c) == {("THPT", "A00"), ("THPT", "A01"), ("THPT", "K01"), ("DGTD", "K00")}
    assert c[("THPT", "A00")].main_subject == "Toán" and c[("THPT", "A01")].main_subject == "Toán"
    assert {f.formula_type for f in p.formulas} == {"mon_chinh_toan", "K01", "DGTD", "XTTN"}


async def test_t3_02_toan_tin_mon_chinh(dbctx):
    p = one(await call(dbctx, programs=["Toán Tin"], fields=["combinations"]))
    assert p.program_code == "MI1"
    c = combos(p)
    assert c[("THPT", "A00")].formula_type == c[("THPT", "A01")].formula_type == "mon_chinh_toan"
    assert c[("THPT", "K01")].formula_type == "K01"
    f = {x.formula_type: x for x in p.formulas}
    assert "Toán được tính 2 lần" in f["mon_chinh_toan"].note
    assert f["mon_chinh_toan"].source.url == SCORE_2026_URL      # P3: nguon chinh thuc, khong phai ben thu ba


async def test_t3_03_fl2_thang_diem(dbctx):
    p = one(await call(dbctx, programs=["FL2"], fields=["methods", "combinations"]))
    assert {m.method_code: m.scale for m in p.methods} == {"THPT": 30, "DGTD": 100, "XTTN": 100}
    c = combos(p)
    assert set(c) == {("THPT", "D01"), ("THPT", "K01"), ("DGTD", "K00")}
    assert c[("THPT", "D01")].formula_type == "khong_mon_chinh"


async def test_t3_04_troy_it_d01_chua_ro(dbctx):
    p = one(await call(dbctx, programs=["TROY-IT"], fields=["combinations"]))
    c = combos(p)
    d01 = c[("THPT", "D01")]
    assert d01.formula_type == "chua_ro" and d01.main_subject_known is False
    assert next(f for f in p.formulas if f.formula_type == "chua_ro").formula is None
    assert c[("THPT", "A00")].main_subject == c[("THPT", "A01")].main_subject == "Toán"
    assert ("THPT", "K01") in c


async def test_t3_05_chi_tieu_it2(dbctx):
    p = one(await call(dbctx, programs=["IT2"], fields=["quota"]))
    assert [(q.year, q.quota, q.quota_type) for q in p.quotas] == [(2026, 200, "tong_nganh")]


async def test_t3_06_chi_tieu_ba_nam(dbctx):
    res = await call(dbctx, programs=["IT1"], years=[2024, 2025, 2026], fields=["quota"])
    assert res.status == Status.PARTIAL
    assert [(q.year, q.quota) for q in one(res).quotas] == [(2025, 300), (2026, 300)]
    m = [x for x in res.missing if "2024" in x.what]
    assert len(m) == 1 and m[0].reason == "not_collected" and m[0].available_years == [2025, 2026]


async def test_t3_07_nganh_chua_mo(dbctx):
    res = await call(dbctx, programs=["CH-E20"], years=[2025])
    assert res.status == Status.NOT_FOUND
    assert any(m.reason == "program_not_open" and m.available_years == [2026] for m in res.missing)


async def test_t3_08_nganh_dung_tuyen(dbctx):
    res = await call(dbctx, programs=["EM4"])
    assert res.status == Status.NOT_FOUND
    assert any(m.reason == "program_not_open" and m.available_years == [2024, 2025] for m in res.missing)


async def test_t3_09_em4_nam_2025(dbctx):
    res = await call(dbctx, programs=["EM4"], years=[2025])
    assert res.status == Status.PARTIAL
    p = one(res)
    assert [(q.year, q.quota) for q in p.quotas] == [(2025, 80)]
    assert {m.method_code for m in p.methods} == {"DGTD", "THPT", "XTTN"}
    assert p.overview is None and p.combinations == []
    assert any(m.reason == "not_collected" and m.available_years == [2026] and "tổ hợp" in m.what
               for m in res.missing)


async def test_t3_10_to_hop_nam_2025(dbctx):
    res = await call(dbctx, programs=["IT1"], years=[2025], fields=["combinations"])
    assert res.status == Status.NOT_FOUND
    assert res.missing[0].reason == "not_collected" and res.missing[0].available_years == [2026]
    assert any("điểm chuẩn" in n for n in res.data.notes)


async def test_t3_11_fl3_thieu_ngon_ngu(dbctx):
    res = await call(dbctx, programs=["FL3"], fields=["overview"])
    o = one(res).overview
    assert o.language is None and o.degree and o.duration
    assert any(m.what == "ngôn ngữ đào tạo FL3" and m.reason == "not_collected" for m in res.missing)


async def test_t3_12_mo_ho(dbctx):
    res = await call(dbctx, programs=["Khoa học máy tính"])
    assert res.status == Status.AMBIGUOUS and res.error_code == ErrorCode.ENTITY_AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"IT1", "TROY-IT"} and res.data is None


async def test_t3_13_nhom_nganh(dbctx):
    res = await call(dbctx, programs=["Elitech"])
    assert res.status == Status.INVALID and "list_programs" in res.message


async def test_t3_14_qua_ba_nganh(dbctx):
    res = await call(dbctx, programs=["IT1", "IT2", "MI1", "EM1"])
    assert res.status == Status.INVALID and res.message == TOO_MANY_MESSAGE


async def test_t3_15_chi_lay_chi_tieu(dbctx):
    p = one(await call(dbctx, programs=["IT1"], fields=["quota"]))
    assert p.quotas and p.overview is None
    assert p.methods == [] and p.combinations == [] and p.formulas == []


async def test_t3_16_viet_nhat_global_ict(dbctx):
    res = await call(dbctx, programs=["Việt Nhật", "Global ICT"], fields=["overview"])
    got = {p.program_code: p.overview for p in res.data.programs}
    ov = {r["program_code"]: r for r in read(PROCESSED / "program_overview_2026.csv")}
    assert set(got) == {"IT-E6", "IT-E7"}
    for code, o in got.items():
        assert (o.language, o.degree, o.duration) == (ov[code]["language"], ov[code]["degree"], ov[code]["duration"])


async def test_t3_17_quet_toan_bo_68_nganh(dbctx):
    ov = {r["program_code"]: r for r in read(PROCESSED / "program_overview_2026.csv")}
    quota = {r["program_code"]: int(r["quota"]) for r in read(PROCESSED / "quotas_2026.csv") if r["quota"]}
    meth, combo = {}, {}
    for r in read(PROCESSED / "program_methods_2026.csv"):
        meth.setdefault(r["program_code"], set()).add(r["method_code"])
    for r in read(PROCESSED / "subject_combinations_2026.csv") + read(PROCESSED / "linking" / "program_combinations_extra.csv"):
        combo.setdefault(r["program_code"], set()).add((r["method_code"], r["combination_code"]))
    codes = sorted(ov)
    assert len(codes) == 68
    wrong = []
    for i in range(0, len(codes), 3):
        res = await call(dbctx, programs=codes[i:i + 3], years=[2026])
        for p in res.data.programs:
            o, c = ov[p.program_code], p.program_code
            want_ov = tuple(o[k] or None for k in ("language", "degree", "duration", "curriculum_url", "short_description"))
            got_ov = (p.overview.language, p.overview.degree, p.overview.duration, p.overview.curriculum_url,
                      p.overview.short_description)
            if got_ov != want_ov:
                wrong.append((c, "overview"))
            if [q.quota for q in p.quotas] != ([quota[c]] if c in quota else []):
                wrong.append((c, "quota"))
            if {m.method_code for m in p.methods} != meth.get(c, set()):
                wrong.append((c, "methods"))
            if set(combos(p)) != combo.get(c, set()):
                wrong.append((c, "combinations"))
    assert not wrong


async def test_t3_18_khong_lot_nguon_ngoai_hust(dbctx):
    """Nguon cua MOI nganh, moi phan, nam 2025-2026 deu thuoc hust.edu.vn — mon chinh lay tu
    tuyensinh247 khong duoc lot vao danh sach nguon (P3)."""
    codes = sorted({r["program_code"] for r in read(PROCESSED / "programs_2025.csv") + read(PROCESSED / "programs_2026.csv")})
    urls = set()
    for i in range(0, len(codes), 3):
        for year in (2025, 2026):
            res = await call(dbctx, programs=codes[i:i + 3], years=[year])
            urls |= {s.url for s in res.sources}
    assert len(urls) > 50
    assert all("hust.edu.vn" in u for u in urls), sorted(u for u in urls if "hust.edu.vn" not in u)
