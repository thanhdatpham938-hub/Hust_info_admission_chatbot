"""scan(): tim cum tu trong ca cau hoi (PLAN - Entity Resolution + Admission Tool (v1), muc 2.4). Khong can DB."""

import pytest


def found(ctx, question):
    r = ctx.scanner.scan(question)
    return [(m.text, sorted(m.entity_types)) for m in r.mentions], r.years


def test_cau_co_ma_ten_phuong_thuc_va_nam(ctx):
    mentions, years = found(ctx, "Điểm IT1 và Toán Tin năm 2025 theo TSA?")
    assert mentions == [("IT1", ["program"]), ("Toán Tin", ["program"]), ("TSA", ["method"])]
    assert years == [2025]


def test_viet_tat_phan_biet_hoa_thuong(ctx):
    """E8: 'ba nam' khong phai nganh BA."""
    assert found(ctx, "Học ba năm thì ra trường được không?")[0] == []
    assert found(ctx, "Ngành BA lấy bao nhiêu điểm")[0] == [("BA", ["program"])]


def test_cum_dai_thang_truoc(ctx):
    """E9: 'Kỹ thuật Ô tô' la mot cum, khong tach them 'Ô tô'."""
    mentions, _ = found(ctx, "Kỹ thuật Ô tô khác Kỹ thuật Cơ khí thế nào?")
    assert [t for t, _ in mentions] == ["Kỹ thuật Ô tô", "Kỹ thuật Cơ khí"]


@pytest.mark.parametrize("q", ["điểm IT-E10", "điểm it-e10", "điểm ITE10"])
def test_ma_go_nhieu_kieu(ctx, q):
    mentions, _ = found(ctx, q)
    assert len(mentions) == 1 and mentions[0][1] == ["program"]


def test_nhieu_nam(ctx):
    _, years = found(ctx, "Điểm chuẩn IT1 theo điểm thi THPT của các năm 2024 và 2025")
    assert years == [2024, 2025]


def test_truong_khoa_va_chung_chi(ctx):
    assert found(ctx, "Trường CNTT&TT ở đâu")[0] == [("Trường CNTT&TT", ["faculty"])]
    assert found(ctx, "Em có IELTS 6.5")[0] == [("IELTS", ["certificate"])]


def test_vi_tri_tra_ve_dung_cum_goc(ctx):
    q = "Ngành  Toán Tin  có tốt không"
    m = ctx.scanner.scan(q).mentions[0]
    assert q[m.start:m.end] == "Toán Tin"
