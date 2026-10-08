"""T6 university_info — 18 ca da duyet (PLAN - T6 university_info (v1), muc 6)."""

import csv

import pytest
import pytest_asyncio

from app.core.config import ROOT
from app.schemas.common import ErrorCode, Status
from app.schemas.university_info import UniversityInfoInput as In
from app.tools.common import TOO_MANY_MESSAGE
from app.tools.context import ToolContext
from app.tools.university_info import GROUP_MESSAGE, university_info

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]
PROCESSED = ROOT / "data" / "processed"


def read(path) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def call(dbctx, **kw):
    return await university_info(In(**kw), dbctx)


def one(res):
    assert res.data and len(res.data.faculties) == 1
    return res.data.faculties[0]


async def test_t6_01_soict_day_du(dbctx):
    res = await call(dbctx, faculties=["Trường CNTT&TT"])
    f = one(res)
    assert res.status == Status.OK and f.faculty_code == "SOICT"
    assert (f.contact.phones, f.contact.email) == (["024 3869 2463"], "vp@soict.hust.edu.vn")
    assert f.contact.address == "Văn phòng Trường CNTT&TT, Phòng 505, Nhà B1, ĐHBK Hà Nội"
    assert f.official_channel_url == "https://soict.hust.edu.vn/"
    kinds = [u.unit_type for u in f.units]
    assert (kinds.count("khoa"), kinds.count("trung_tam")) == (2, 7)
    assert [p.program_code for p in f.programs] == ["IT-E10", "IT-E15", "IT-E6", "IT-E7", "IT-EP", "IT1", "IT2"]
    assert f.programs_year == 2026


async def test_t6_02_ten_cu(dbctx):
    f = one(await call(dbctx, faculties=["Viện Điện"]))
    assert (f.faculty_code, f.faculty_name) == ("SEEE", "Trường Điện - Điện tử")
    assert {"Viện Điện", "Viện Điện tử - Viễn thông"} <= set(f.former_names)


async def test_t6_03_viet_tat(dbctx):
    assert one(await call(dbctx, faculties=["SoICT"])).faculty_code == "SOICT"


async def test_t6_04_nganh_toan_tin(dbctx):
    f = one(await call(dbctx, programs=["Toán Tin"], fields=["contact", "channel"]))
    assert (f.faculty_code, f.asked_programs) == ("FAMI", ["MI1"])
    assert f.contact.phones == ["024 3869 2137", "024 3868 2470"] and f.contact.email == "fami@hust.edu.vn"
    assert f.official_channel_url == "https://fami.hust.edu.vn/"
    assert f.units == [] and f.programs == []


async def test_t6_05_mo_ho_cung_truong_khong_hoi_lai(dbctx):
    res = await call(dbctx, programs=["Kỹ thuật Ô tô"])
    f = one(res)
    assert res.status != Status.AMBIGUOUS and f.faculty_code == "SME" and f.asked_programs == ["TE-E2", "TE1"]


async def test_t6_06_mo_ho_khac_truong_hoi_lai(dbctx):
    res = await call(dbctx, programs=["Khoa học máy tính"])
    assert res.status == Status.AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"IT1", "TROY-IT"}


async def test_t6_07_troy_it_thuoc_fami(dbctx):
    assert one(await call(dbctx, programs=["TROY-IT"])).faculty_code == "FAMI"


async def test_t6_08_sem_ba_so(dbctx):
    f = one(await call(dbctx, faculties=["Trường Kinh tế"], fields=["contact"]))
    assert f.contact.phones == ["024 3869 2304", "024 3868 0791", "093 898 3868 (riêng chương trình TROY)"]


async def test_t6_09_sem_chua_co_don_vi(dbctx):
    res = await call(dbctx, faculties=["SEM"], fields=["units"])
    assert res.status == Status.PARTIAL and one(res).units == []
    assert any(m.what == "đơn vị trực thuộc SEM" and m.reason == "not_collected" for m in res.missing)


async def test_t6_10_sem_nganh_2026(dbctx):
    f = one(await call(dbctx, faculties=["Trường Kinh tế"], fields=["programs"]))
    assert [p.program_code for p in f.programs] == ["EM-E13", "EM-E14", "EM-E17", "EM1", "EM2", "EM3", "EM5"]


async def test_t6_11_sem_nganh_2025(dbctx):
    f = one(await call(dbctx, faculties=["Trường Kinh tế"], fields=["programs"], year=2025))
    codes = [p.program_code for p in f.programs]
    assert len(codes) == 8 and {"EM4", "TROY-BA"} <= set(codes) and "EM-E17" not in codes


async def test_t6_12_tat_ca_kenh_thong_tin(dbctx):
    res = await call(dbctx, fields=["channel"])
    assert len(res.data.faculties) == 10 and all(f.official_channel_url for f in res.data.faculties)


async def test_t6_13_nhom_nganh(dbctx):
    res = await call(dbctx, programs=["Elitech"])
    assert res.status == Status.INVALID and res.message == GROUP_MESSAGE


async def test_t6_14_khong_tim_thay(dbctx):
    res = await call(dbctx, faculties=["Trường Y"])
    assert res.status == Status.NOT_FOUND and res.error_code == ErrorCode.ENTITY_NOT_FOUND


async def test_t6_15_qua_ba(dbctx):
    res = await call(dbctx, faculties=["SOICT", "SEEE", "SME", "SEM"])
    assert res.status == Status.INVALID and res.message == TOO_MANY_MESSAGE


async def test_t6_16_khong_lap_truong(dbctx):
    f = one(await call(dbctx, faculties=["SOICT"], programs=["IT2"]))
    assert (f.faculty_code, f.asked_programs) == ("SOICT", ["IT2"])


async def test_t6_17_quet_toan_bo(dbctx, tables):
    fac = {r["faculty_code"]: r for r in read(PROCESSED / "linking" / "faculties.csv")}
    units = {}
    for r in read(PROCESSED / "linking" / "faculty_units.csv"):
        units.setdefault(r["faculty_code"], set()).add((r["unit_name"], r["unit_type"]))
    prog = {}
    for r in tables["programs"]:
        if any(y["program_code"] == r["program_code"] and y["year"] == 2026 for y in tables["program_years"]):
            prog.setdefault(r["faculty_code"], set()).add(r["program_code"])
    res = await call(dbctx)
    assert len(res.data.faculties) == 10
    for f in res.data.faculties:
        src = fac[f.faculty_code]
        assert f.contact.phones == [p.strip() for p in src["phone"].split(";") if p.strip()]
        assert (f.contact.email, f.contact.address, f.official_channel_url) == \
            (src["email"], src["address"], src["official_channel_url"])
        assert {(u.unit_name, u.unit_type) for u in f.units} == units.get(f.faculty_code, set())
        assert {p.program_code for p in f.programs} == prog.get(f.faculty_code, set())


async def test_t6_18_nguon_va_khong_lo_ghi_chu_noi_bo(dbctx):
    res = await call(dbctx)
    assert res.sources and all("hust.edu.vn" in s.url for s in res.sources)
    dumped = res.model_dump_json()
    assert "contact_note" not in dumped and "data/link.md" not in dumped      # U7
