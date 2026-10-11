"""Entity Resolution (PLAN - Entity Resolution + Admission Tool (v1), muc 2.7). Khong can DB."""

from collections import defaultdict

import pytest

from app.entity_resolution.normalize import normalize


def codes(ctx, mention, etype="program", years=None):
    r = ctx.resolve(mention, etype, years)
    return r.status, set(r.codes)


def test_moi_alias_trong_csv_tra_ra_dung_ma(ctx, tables):
    """Thay cho simulate_lookup cu: tung alias -> dung tap ma da khai bao."""
    declared, shown = defaultdict(set), {}
    for r in tables["entity_aliases"]:
        k = (normalize(r["alias"]), r["entity_type"])
        declared[k].add(r["entity_code"])
        shown.setdefault(k, r["alias"])
    wrong = []
    for (key, etype), want in declared.items():
        years = sorted({y for c in want for y in ctx.aliases.valid_years.get(c, ())}) or None
        res = ctx.resolve(shown[(key, etype)], etype, years)
        got = {res.group_code} if res.group_code else set(res.codes)
        if got != want:
            wrong.append((shown[(key, etype)], etype, sorted(got), sorted(want)))
    assert not wrong


# ---------------------------------------------------------------- 4 quy tac PRD 10.3
@pytest.mark.parametrize("year,want", [(2026, {"EM-E17"}), (2025, {"EM4"})])
def test_accounting_theo_nam(ctx, year, want):
    assert codes(ctx, "Accounting", years=[year]) == ("unique", want)


def test_khop_chinh_xac_thang_chuoi_con(ctx):
    status, got = codes(ctx, "Chemistry")
    assert status == "unique" and len(got) == 1 and "CH-E20" not in got    # khong bi "Cosmetic Chemistry" nuot


def test_viet_tat_chi_khop_chinh_xac(ctx):
    assert codes(ctx, "BA") == ("unique", {"EM-E13"})
    # "BA" khong duoc khop chuoi con vao cac ten chua "ba" (Bach khoa, ban dan, Nagaoka...)
    assert ctx.resolve("ba", "program").matched_by == "exact"


def test_khoa_hoc_may_tinh_phai_hoi_lai(ctx):
    assert codes(ctx, "Khoa học máy tính") == ("clarify", {"IT1", "TROY-IT"})


def test_toan_tin(ctx):
    assert codes(ctx, "Toán Tin") == ("unique", {"MI1"})


def test_cap_chuan_tien_tien_trung_ten_deu_hoi_lai(ctx):
    assert codes(ctx, "Kỹ thuật Ô tô") == ("clarify", {"TE1", "TE-E2"})


def test_liet_ke_du_ung_vien_da_khai_bao(ctx):
    """Anh chot 2026-10-07: alias khai bao clarify thi liet ke DU, khong cat 3."""
    status, got = codes(ctx, "BK CNTT")
    assert status == "clarify" and len(got) == 7


# ---------------------------------------------------------------- nam (E1, E3)
def test_clarify_con_mot_ma_sau_loc_nam_thi_unique(ctx):
    assert codes(ctx, "Troy", years=[2026]) == ("unique", {"TROY-IT"})
    assert codes(ctx, "Troy", years=[2025]) == ("clarify", {"TROY-IT", "TROY-BA"})


def test_ten_cu_van_dung_cho_nam_moi(ctx):
    """Cot year cua alias la nam GHI NHAN, khong phai nam het hieu luc (E1)."""
    assert codes(ctx, "Logistics và Quản lý chuỗi cung ứng", years=[2026]) == ("unique", {"EM-E14"})


def test_nganh_dung_tuyen_bao_nam_co_du_lieu(ctx):
    r = ctx.resolve("EM4", "program", [2026])
    assert r.status == "not_found" and r.other_years == {"EM4": [2024, 2025]}


def test_khong_noi_nam_lay_nam_moi_nhat(ctx):
    assert ctx.aliases.latest_year == 2026
    assert codes(ctx, "Accounting") == ("unique", {"EM-E17"})


# ---------------------------------------------------------------- chuan hoa
@pytest.mark.parametrize("mention", ["toán tin", "TOÁN TIN", "toan tin", "  Toán   Tin "])
def test_chuan_hoa(ctx, mention):
    assert codes(ctx, mention) == ("unique", {"MI1"})


def test_chu_d():
    assert normalize("Điện tử") == "dien tu"


@pytest.mark.parametrize("mention", ["IT-E10", "it-e10", "ITE10", "it e10"])
def test_ma_go_nhieu_kieu(ctx, mention):
    assert codes(ctx, mention) == ("unique", {"IT-E10"})


# ---------------------------------------------------------------- fuzzy
def test_fuzzy_go_sai_chinh_ta(ctx):
    r = ctx.resolve("Khoa hoc may tihn", "program")
    assert r.matched_by == "fuzzy" and set(r.codes) == {"IT1", "TROY-IT"}
    assert ctx.resolve("logictics", "program").codes == ["EM-E14"]


def test_ten_dung_nhung_nganh_chua_mo_khong_doan_fuzzy(ctx):
    """Do 2026-10-08: FL4 (mo tu 2026) hoi nam 2025 tung bi fuzzy doan sang FL3 (Tieng Trung)."""
    r = ctx.resolve("Tiếng Hàn Khoa học và Công nghệ", "program", [2025])
    assert r.status == "not_found" and r.other_years == {"FL4": [2026]}


def test_fuzzy_chi_hoi_lai_ung_vien_sat_diem(ctx):
    """Do 2026-10-08: 'ky thuat oto' tung keo them ME-E1 (87 diem) vao cap TE1/TE-E2 (96 diem)."""
    assert codes(ctx, "ky thuat oto") == ("clarify", {"TE1", "TE-E2"})


@pytest.mark.parametrize("mention", ["Trường Y", "Trường Luật", "Khoa Y"])
def test_chu_dau_chung_khong_lam_fuzzy_doan_bua(ctx, mention):
    """Do 2026-10-09: 'truong y' tung duoc 86 diem voi moi 'truong ...'; 'Truong Luat' tung ra Truong Vat lieu."""
    assert ctx.resolve(mention, "faculty").status == "not_found"


def test_fuzzy_van_bat_loi_go_sau_chu_dau_chung(ctx):
    assert codes(ctx, "truong vat lieuu", "faculty") == ("unique", {"SMSE"})
    assert codes(ctx, "Ngành Logictics") == ("unique", {"EM-E14"})


def test_cum_qua_ngan_khong_fuzzy(ctx):
    assert ctx.resolve("co", "program").status == "not_found"


def test_khong_tim_thay(ctx):
    assert ctx.resolve("học phí", "program").status == "not_found"


# ---------------------------------------------------------------- nhom va loai khac
def test_nhom_elitech(ctx):
    r = ctx.resolve("Elitech", "program")
    assert r.status == "group" and r.group_code == "elitech" and len(r.codes) == 26


def test_ma_nhom_noi_bo_khong_phai_khoa_tra(ctx):
    """'pfiev' la ma nhom tu dat; PFIEV phai ra 3 nganh anh da chot, khong ra nhom."""
    assert codes(ctx, "PFIEV") == ("clarify", {"EE-EP", "TE-EP", "IT-EP"})


def test_toeic_la_ca_4_ky_nang(ctx):
    status, got = codes(ctx, "TOEIC", "certificate")
    assert status == "group" and len(got) == 4


@pytest.mark.parametrize("mention,want", [("TSA", "DGTD"), ("đánh giá tư duy", "DGTD"), ("thi THPT", "THPT"),
                                          ("tài năng", "XTTN"), ("diện 1.3", "XTTN_1.3"), ("tuyển thẳng", "XTTN_1.1")])
def test_alias_phuong_thuc(ctx, mention, want):
    assert codes(ctx, mention, "method") == ("unique", {want})


def test_mo_ma_phuong_thuc_cha(ctx):
    assert ctx.expand_method("XTTN") == ["XTTN_1.1", "XTTN_1.2", "XTTN_1.3"]
    assert ctx.expand_method("THPT") == ["THPT"]
