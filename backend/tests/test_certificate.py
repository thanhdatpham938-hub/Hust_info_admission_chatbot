"""T5 certificate_lookup — 19 ca da duyet (PLAN - T4 T5 hoc phi va chung chi (v1), muc B6)."""

import pytest
import pytest_asyncio

from app.db.pool import fetch_all
from app.schemas.certificate import CertificateInput as In
from app.schemas.common import ErrorCode, Status
from app.tools.certificate import certificate_lookup
from app.tools.context import ToolContext

pytestmark = [pytest.mark.db, pytest.mark.usefixtures("db_pool")]


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


async def call(dbctx, **kw):
    return await certificate_lookup(In(**kw), dbctx)


def conv(res):
    return [(c.cert_value, c.table, c.bonus_point, c.converted_score_10) for c in res.data.conversions]


async def test_t5_01_ielts_65_xet_tuyen(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="xet_tuyen")
    assert res.status == Status.OK and res.data.matched is True
    assert conv(res) == [("6.5", "ca_hai", 4, 9.5)] and res.data.conversions[0].year == 2026


async def test_t5_02_ielts_ca_bang_2026(dbctx):
    res = await call(dbctx, certificate="IELTS", purpose="xet_tuyen")
    assert res.data.matched is None
    assert [(v, b, s) for v, _, b, s in conv(res)] == [("5.0", 1, 8.0), ("5.5", 2, 8.5), ("6.0", 3, 9.0),
                                                       ("6.5", 4, 9.5), ("7.0-9.0", 5, 10.0)]


async def test_t5_03_ielts_75_khop_khoang(dbctx):
    res = await call(dbctx, certificate="IELTS", value="7.5", purpose="xet_tuyen")
    assert conv(res) == [("7.0-9.0", "ca_hai", 5, 10.0)]


async def test_t5_04_nam_2024_hai_bang(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="xet_tuyen", year=2024)
    got = {t: (v, b, s) for v, t, b, s in conv(res)}
    assert got == {"quy_doi": ("≥ 6.5", None, 10.0), "diem_thuong": ("6.5", 4, None)}
    assert any("hai bảng" in n for n in res.data.notes)


async def test_t5_05_ielts_45_duoi_muc_thap_nhat(dbctx):
    res = await call(dbctx, certificate="IELTS", value="4.5", purpose="xet_tuyen")
    assert res.data.matched is False and len(res.data.conversions) == 5
    assert min(c.cert_value for c in res.data.conversions) == "5.0"


async def test_t5_06_ielts_65_bac_4(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="chuan_dau_ra", cohort="K71")
    assert [(e.level, e.level_group) for e in res.data.exit_levels] == [("Bậc 4", "Bậc 4")]


async def test_t5_07_it1_dat(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="chuan_dau_ra", programs=["IT1"], cohort="K71")
    r = res.data.requirements
    assert [(x.req_id, x.min_level_group, x.meets) for x in r] == [("nn2026-chuan", "Bậc 3", True)]


async def test_t5_08_it_e10_chua_dat(dbctx):
    res = await call(dbctx, certificate="IELTS", value="5.0", purpose="chuan_dau_ra", programs=["IT-E10"], cohort="K71")
    assert [(e.level, e.level_group) for e in res.data.exit_levels] == [("Bậc 3.2", "Bậc 3")]
    assert [(x.req_id, x.min_level_group, x.meets) for x in res.data.requirements] == \
        [("nn2026-elitech-htqt", "Bậc 4", False)]


async def test_t5_09_o_gop_ielts_35(dbctx):
    res = await call(dbctx, certificate="IELTS", value="3.5", purpose="chuan_dau_ra", cohort="K71")
    assert sorted((e.level, e.level_group) for e in res.data.exit_levels) == [("Bậc 2.2", "Bậc 2"), ("Bậc 2.3", "Bậc 2")]


async def test_t5_10_khong_noi_khoa(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="chuan_dau_ra")
    assert res.status == Status.AMBIGUOUS
    assert [c.code for c in res.clarifications[0].candidates] == ["K71+", "K70-"]


async def test_t5_11_khoa_k70(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="chuan_dau_ra", cohort="K70")
    assert res.status == Status.NOT_FOUND and res.missing[0].reason == "not_collected"
    assert any("10728" in n for n in res.data.notes)


async def test_t5_12_khong_noi_muc_dich(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5")
    assert res.status == Status.AMBIGUOUS
    assert [c.code for c in res.clarifications[0].candidates] == ["xet_tuyen", "chuan_dau_ra"]


async def test_t5_13_toefl_mo_ho(dbctx):
    res = await call(dbctx, certificate="TOEFL", purpose="xet_tuyen")
    assert res.status == Status.AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"TOEFL_IBT", "TOEFL_ITP"}


async def test_t5_14_toeic_theo_ky_nang(dbctx):
    res = await call(dbctx, certificate="TOEIC", value="300", purpose="xet_tuyen")
    got = {c.cert_code: (c.cert_value, c.bonus_point, c.converted_score_10) for c in res.data.conversions}
    assert got == {"TOEIC_LISTENING": ("275-395", 1, 8.0), "TOEIC_READING": ("275-380", 1, 8.0)}
    assert any("trung bình cộng 4 kỹ năng" in n for n in res.data.notes)


async def test_t5_15_jlpt_n3(dbctx):
    res = await call(dbctx, certificate="JLPT", value="N3", purpose="xet_tuyen")
    assert sorted((v, b, s) for v, _, b, s in conv(res)) == [("N3 (121-149)", 3, 9.0), ("N3 (150-180)", 4, 9.5),
                                                             ("N3 (95-120)", 2, 8.5)]


async def test_t5_16_troy_yeu_cau_dau_khoa(dbctx):
    res = await call(dbctx, certificate="IELTS", purpose="chuan_dau_ra", programs=["TROY-IT"], cohort="K71")
    r = res.data.requirements
    assert [x.req_id for x in r] == ["nn2026-troy-daukhoa"] and r[0].meets is None
    assert "ĐẦU KHÓA" in r[0].note


async def test_t5_17_pfiev_nhieu_dieu_kien(dbctx):
    res = await call(dbctx, certificate="IELTS", value="6.5", purpose="chuan_dau_ra", programs=["EE-EP"], cohort="K71")
    r = res.data.requirements
    assert {x.req_id for x in r} == {"nn2026-pfiev-cunhan", "nn2026-pfiev-kysu", "nn2026-pfiev-phuluc-phap"}
    assert all(x.meets is None for x in r)


async def test_t5_18_chung_chi_khong_co(dbctx):
    res = await call(dbctx, certificate="abc", purpose="xet_tuyen")
    assert res.status == Status.NOT_FOUND and res.error_code == ErrorCode.ENTITY_NOT_FOUND


async def test_t5_19_quet_toan_bo(dbctx):
    """Moi dong cert_bonus 2026 va moi dong cert_output tra lai duoc dung bang chinh cert_value cua no."""
    names = {r["cert_code"]: r["cert_name"] for r in await fetch_all("SELECT cert_code, cert_name FROM certificates")}
    wrong = []
    for r in await fetch_all("SELECT cert_code, cert_value, table_purpose FROM cert_bonus WHERE year = 2026"):
        res = await call(dbctx, certificate=r["cert_code"], value=r["cert_value"], purpose="xet_tuyen")
        if not (res.data and res.data.matched and any(c.cert_code == r["cert_code"] and c.cert_value == r["cert_value"]
                                                       for c in res.data.conversions)):
            wrong.append(("bonus", r["cert_code"], r["cert_value"]))
    for r in await fetch_all("SELECT cert_code, cert_value, level FROM cert_output"):
        res = await call(dbctx, certificate=r["cert_code"], value=r["cert_value"], purpose="chuan_dau_ra", cohort="K71")
        if not (res.data and res.data.matched and any(e.cert_code == r["cert_code"] and e.level == r["level"]
                                                       for e in res.data.exit_levels)):
            wrong.append(("output", r["cert_code"], r["cert_value"], names.get(r["cert_code"])))
    assert not wrong
