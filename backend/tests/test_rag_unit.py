"""T7 — phan khong can mang (PLAN - T7 retrieval (v2), muc 7): tach cum tu, dung bo loc, khoa, trich dan."""

from app.rag.phrases import extract_phrases
from app.rag.retriever import LATEST, SearchSpec, base_filter, faculty_branches, general_branches
from app.tools.rag_tool import citation_of, cohort_label


def matches(phrases):
    return [p.match for p in phrases]


def test_cum_tu_chuyen_nganh():
    assert matches(extract_phrases("Trường có tính hệ số 2 đối với môn chính không?")) == ["môn chính"]


def test_he_so_don_le_khong_loc():
    """'he so' co trong quy dinh XTTN (he so quy doi chung chi) — loc theo no lam Q10 lech tai lieu."""
    assert matches(extract_phrases("Hệ số quy đổi là bao nhiêu")) == []


def test_cach_goi_tuong_duong():
    assert matches(extract_phrases("Điều kiện học bạ tối thiểu là gì")) == ["TBC", "điểm trung bình chung"]
    assert "buộc thôi học" in matches(extract_phrases("Khi nào bị đuổi học"))
    assert "học lại" in matches(extract_phrases("rớt môn thì sao"))


def test_ma_to_hop_va_dieu():
    got = matches(extract_phrases("Tổ hợp D01 và K01 theo Điều 19"))
    assert {"D01", "K01", "Điều 19"} <= set(got)


def test_khong_cum_tu():
    assert extract_phrases("Thời tiết hôm nay thế nào") == []


def test_nhanh_khi_khong_neu_nam():
    """R2: co nhanh 'ban moi nhat' nhung nhanh 'moi ban' khong loc ban moi (uu tien, khong loai)."""
    spec = SearchSpec(query="x")
    branches = general_branches(spec, extract_phrases("môn chính"))
    assert len(branches) == 3
    assert LATEST not in (branches[0].must or [])           # A: moi ban
    assert LATEST in branches[1].must                       # B: ban moi nhat
    assert LATEST in branches[2].must                       # C: cum tu, chi ban moi


def test_neu_nam_thi_khong_co_nhanh_ban_moi():
    spec = SearchSpec(query="x", years=[2024])
    branches = general_branches(spec, [])
    assert len(branches) == 1
    year_cond = base_filter(spec).must[0]
    assert {c.key for c in year_cond.should} == {"versioned", "year"}


def test_loc_khoa_giu_chunk_khong_gan_khoa():
    cond = base_filter(SearchSpec(query="x", cohort="K71+")).must[0]
    assert {c.match.value for c in cond.should} == {"", "K71+"}


def test_truong_khoa_uu_tien_gioi_thieu_don_vi():
    b = faculty_branches(SearchSpec(query="x", faculty_codes=["SMSE"]))
    assert len(b) == 2 and any(getattr(c, "key", "") == "document_type" for c in b[1].must)


def test_doc_khoa():
    assert [cohort_label(x) for x in ["K71", "khoá 71", "2026", "K70", "K68", "khoá 2025", None]] == \
        ["K71+", "K71+", "K71+", "<=K70", "<=K70", "<=K70", None]


def test_trich_dan_van_ban_va_trang_web():
    van_ban = citation_of({"document_title": "Quy chế đào tạo trình độ đại học", "dieu_no": "15", "khoan_no": "2",
                           "page_no": "18", "heading": "Điều 15", "source_url": "https://x.hust.edu.vn/a.pdf",
                           "year": 2025, "verification_status": "pdf_text"})
    assert van_ban.title == "Quy chế đào tạo trình độ đại học — Điều 15 khoản 2 — Trang 18"
    web = citation_of({"document_title": "Công bố điểm chuẩn đại học 2026", "heading": "Cách tính điểm",
                       "source_url": "https://ts.hust.edu.vn/b", "year": 2026})
    assert web.title == "Công bố điểm chuẩn đại học 2026 — Cách tính điểm" and web.url
