"""T7 rag_search — 16 ca da duyet (PLAN - T7 retrieval (v2), muc 5). Can Qdrant + OPENAI_API_KEY.

Chay tay: pytest -m rag   (mac dinh bi bo qua de `pytest backend` khong ton phi embedding).
R-14 (do ca bo 120 cau) nam o scripts/eval_retrieval.py.
"""

import pytest
import pytest_asyncio

from app.schemas.common import ErrorCode, Status
from app.schemas.rag import RagSearchInput as In
from app.tools.context import ToolContext
from app.tools.rag_tool import rag_search
from app.rag.retriever import Retriever

pytestmark = [pytest.mark.rag, pytest.mark.db, pytest.mark.usefixtures("db_pool")]

Q10 = "Trường có tính hệ số 2 đối với môn chính (ví dụ Toán hoặc Tiếng Anh) khi xét tuyển theo điểm thi THPT không?"
Q12 = "Công thức tính điểm xét tuyển theo kỳ thi ĐGTD (TSA) có cộng điểm ưu tiên đối tượng và khu vực không?"
Q18 = "Điều kiện học bạ tối thiểu để nộp hồ sơ vào HUST là gì? Có yêu cầu điểm trung bình các môn học không?"
Q20 = "Điểm ưu tiên khu vực và đối tượng được tính như thế nào trong phương thức xét điểm thi ĐGTD?"
Q80 = ("Phân biệt sự khác nhau về nội dung đào tạo và chuẩn đầu ra giữa ngành Khoa học máy tính (IT1) "
       "và Kỹ thuật máy tính (IT2)")
Q84 = ("Chuẩn đầu ra tiếng Anh (TOEIC/IELTS) để được nhận đồ án tốt nghiệp và xét tốt nghiệp của chương trình "
       "chuẩn là bao nhiêu?")
Q106 = ("Sinh viên tốt nghiệp các ngành thuộc Trường Vật liệu thường đầu quân cho các doanh nghiệp, nhà máy "
        "thuộc lĩnh vực nào?")


@pytest_asyncio.fixture(scope="session")
async def dbctx(db_pool) -> ToolContext:
    return await ToolContext.load()


@pytest_asyncio.fixture(scope="session")
async def retriever():
    r = Retriever()
    try:
        await r.client.get_collection(r.collection)
    except Exception as e:
        pytest.fail(f"Không kết nối được Qdrant ({type(e).__name__}: {e}). Chạy: docker compose up -d", pytrace=False)
    yield r
    await r.close()


async def call(dbctx, retriever, **kw):
    return await rag_search(In(**kw), dbctx, retriever)


def ids(res):
    return [c.chunk_id for c in res.data.chunks]


async def test_r01_mon_chinh(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q10)
    assert {"ts::diem-chuan-2026-3", "dean2026::m3-1"} <= set(ids(res))
    assert "môn chính" in res.data.phrases_used


async def test_r02_cong_thuc_dgtd(dbctx, retriever):
    assert "ts::diem-chuan-2026-4" in ids(await call(dbctx, retriever, query=Q12))


async def test_r03_diem_uu_tien_dgtd(dbctx, retriever):
    assert ids(await call(dbctx, retriever, query=Q20))[0] == "ts::diem-chuan-2026-4"


async def test_r04_hoc_ba_cach_goi_tuong_duong(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q18)
    assert set(ids(res)) & {"xttn2026::d3k1", "xttn2026::d4k1", "dean2026::m1.2", "dean2026::m1.3"}
    assert "TBC" in res.data.phrases_used


async def test_r04b_ban_cu_van_con(dbctx, retriever):
    """R2: le phi tuyen sinh chi co o de an 2024 — khong duoc loc cung 'chi ban moi'."""
    assert "dean2024::m1.9" in ids(await call(dbctx, retriever, query="Lệ phí đăng ký dự thi đánh giá tư duy là bao nhiêu"))


async def test_r05_neu_nam_2026(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q18, years=[2026])
    assert not [c for c in res.data.chunks if c.document_type == "de_an_tuyen_sinh" and c.year in (2024, 2025)]


async def test_r06_hai_nganh_deu_co_mat(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q80, programs=["IT1", "IT2"])
    assert {"IT1", "IT2"} <= {c.program_code for c in res.data.chunks}


async def test_r07_truong_uu_tien_gioi_thieu(dbctx, retriever):
    assert ids(await call(dbctx, retriever, query=Q106, faculties=["Trường Vật liệu"]))[0] == "donvi::smse-1"


async def test_r08_hai_khoa_phai_hoi_lai(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q84)
    assert {"nnk70::d5", "nnk71::d5"} <= set(ids(res))
    assert res.data.cohorts_found == ["<=K70", "K71+"] and res.data.notes


async def test_r09_neu_khoa_k71(dbctx, retriever):
    res = await call(dbctx, retriever, query=Q84, cohort="K71")
    assert "nnk71::d5" in ids(res) and not [c for c in res.data.chunks if c.cohort == "<=K70"]


async def test_r10_lac_de(dbctx, retriever):
    res = await call(dbctx, retriever, query="Thời tiết Hà Nội hôm nay thế nào?")
    assert res.data.low_confidence and res.status == Status.NOT_FOUND
    assert res.error_code == ErrorCode.LOW_RETRIEVAL_CONFIDENCE


async def test_r11_truong_khac_nguong_khong_bat_duoc(dbctx, retriever):
    """Ghi lai gioi han cua T7: cau hoi truong khac co diem cao — Router (Tuan 4) phai chan OTHER_UNIVERSITY."""
    res = await call(dbctx, retriever, query="Điểm chuẩn Đại học Quốc gia Hà Nội năm 2025 là bao nhiêu?")
    assert not res.data.low_confidence


async def test_r12_nganh_mo_ho_hoi_lai(dbctx, retriever):
    res = await call(dbctx, retriever, query="Ngành Kỹ thuật Ô tô học những gì", programs=["Kỹ thuật Ô tô"])
    assert res.status == Status.AMBIGUOUS
    assert {c.code for c in res.clarifications[0].candidates} == {"TE1", "TE-E2"}


async def test_r13_trich_dan_day_du(dbctx, retriever):
    for q in (Q10, Q18, Q84, Q106, "Học phí học kỳ hè tính thế nào?"):
        for c in (await call(dbctx, retriever, query=q)).data.chunks:
            assert c.source_url and c.citation.title and c.citation.url
            if c.document_type in ("quy_che_dao_tao", "quy_che_thi_tsa", "so_tay_sinh_vien", "quy_dinh_ngoai_ngu"):
                assert c.page_no, c.chunk_id


async def test_r16_hoc_ky_he_ban_moi_nhat(dbctx, retriever):
    got = ids(await call(dbctx, retriever, query="Học phí học kỳ hè tính thế nào?"))
    assert "hocphi2026::d5" in got
    if "hocphi2024::d5" in got:
        assert got.index("hocphi2026::d5") < got.index("hocphi2024::d5")
