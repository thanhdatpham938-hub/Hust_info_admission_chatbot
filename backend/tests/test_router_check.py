"""Bo quet truoc Router + kiem sau Router (PLAN - Sua loi sau chay thu Synthesizer (v1), buoc 3). Khong goi OpenAI."""

import pytest
from app.graph.router import (
    AdmissionScoresCall,
    ListProgramsCall,
    TuitionCall,
    UniversityInfoCall,
    context_block,
)
from app.graph.router_check import hint_line, reconcile
from app.graph.state import empty_context
from app.schemas.admission import AdmissionScoresInput, ListProgramsInput
from app.schemas.tuition import TuitionInput
from app.schemas.university_info import UniversityInfoInput


def run(ctx, question, calls):
    fixes = reconcile(calls, question, ctx.scanner.scan(question), ctx.aliases)
    return calls, fixes


def test_ten_kem_ma_trong_ngoac_doi_thanh_ma(ctx):   # S01
    q = "Điểm chuẩn ngành Khoa học máy tính (IT1) theo điểm thi THPT của các năm 2024 và 2025 là bao nhiêu?"
    calls, fixes = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["Khoa học máy tính"], years=[2024, 2025]))])
    assert calls[0].args.programs == ["IT1"]
    assert fixes == ['admission_scores.programs: "Khoa học máy tính" → "IT1"']


def test_hai_cap_ten_ma(ctx):                          # S09
    q = "Học phí ngành Việt - Nhật (IT-E6) và Việt - Pháp (IT-EP) có cao hơn nhiều so với hệ chuẩn không?"
    calls, _ = run(ctx, q, [TuitionCall(tool="tuition_fees", args=TuitionInput(
        programs=["Việt - Nhật", "Việt - Pháp"], program_group="hệ chuẩn"))])
    assert calls[0].args.programs == ["IT-E6", "IT-EP"]
    assert calls[0].args.program_group == "hệ chuẩn"


def test_router_tu_dich_nhom_thay_bang_cum_bo_quet(ctx):   # S08
    q = "Học phí các chương trình đào tạo quốc tế liên kết (SIE, Troy, Leibniz) được tính như thế nào?"
    calls, fixes = run(ctx, q, [TuitionCall(tool="tuition_fees", args=TuitionInput(program_group="PFIEV"))])
    assert calls[0].args.program_group == "SIE"
    assert fixes == ['tuition_fees.program_group: "PFIEV" → "SIE"']


def test_ten_chinh_truong_o_o_truong_khoa_bi_bo(ctx):      # S04
    q = "Ngành nào có điểm chuẩn thấp nhất của Bách khoa trong năm ngoái?"
    calls, fixes = run(ctx, q, [ListProgramsCall(tool="list_programs", args=ListProgramsInput(
        metric="score", faculty="Bách khoa", years=[2025], order="asc"))])
    assert calls[0].args.faculty is None
    assert fixes == ['list_programs.faculty: "Bách khoa" → bỏ']


def test_cau_dung_khong_bi_dung(ctx):
    q = "So sánh điểm chuẩn ngành IT1 và IT2 theo phương thức THPT"
    calls, fixes = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["IT1", "IT2"], methods=["THPT"]))])
    assert calls[0].args.programs == ["IT1", "IT2"] and fixes == []


def test_khong_dau_va_ma_bo_gach_noi_van_giu(ctx):
    q = "diem chuan khoa hoc may tinh va ITE10 nam 2025"
    calls, fixes = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["khoa hoc may tinh", "ITE10"]))])
    assert calls[0].args.programs == ["khoa hoc may tinh", "ITE10"] and fixes == []


def test_router_dich_ten_tieng_anh_thay_bang_chu_nguoi_dung(ctx):
    q = "What was the admission score of Computer Engineering in 2025?"
    calls, fixes = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["Kỹ thuật máy tính"], years=[2025]))])
    assert calls[0].args.programs == ["Computer Engineering"]
    assert len(fixes) == 1


def test_khong_co_trong_cau_va_bo_quet_khong_thay_thi_giu(ctx):
    """Do 2026-10-21: bo thi mat nganh (R151 "CNTT" -> Router ghi "Công nghệ Thông tin"); giu de tool tu phan giai."""
    q = "60 điểm TSA có cơ hội vào CNTT không?"
    calls, fixes = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["Công nghệ Thông tin"]))])
    assert calls[0].args.programs == ["Công nghệ Thông tin"]
    assert fixes == ['admission_scores.programs: "Công nghệ Thông tin" không có trong câu, bộ quét không thấy cụm '
                     'cùng loại → giữ']


def test_nam_hoc_hoc_phi_chi_lay_nam_bat_dau(ctx):         # S39
    q = "How much is the tuition fee per credit for the standard program in the 2026-2027 school year?"
    calls, fixes = run(ctx, q, [TuitionCall(tool="tuition_fees", args=TuitionInput(
        program_group="chuong trinh chuan", years=[2026, 2027], kinds=["credit"]))])
    assert calls[0].args.years == [2026] and calls[0].args.program_group == "chuong trinh chuan"
    assert "tuition_fees.years: bỏ 2027 (năm học 2026-2027)" in fixes


def test_hai_nam_rieng_khong_bi_gop(ctx):
    q = "Học phí IT1 năm 2025 và 2026?"
    calls, _ = run(ctx, q, [TuitionCall(tool="tuition_fees", args=TuitionInput(programs=["IT1"], years=[2025, 2026]))])
    assert calls[0].args.years == [2025, 2026]


def test_cum_da_dung_khong_bi_lay_lai(ctx):
    """Router dich mot nganh, giu mot nganh: cho thay chi lay cum CHUA dung."""
    q = "So sánh điểm chuẩn Computer Engineering và IT1 năm 2025"
    calls, _ = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["Kỹ thuật máy tính", "IT1"]))])
    assert calls[0].args.programs == ["Computer Engineering", "IT1"]


def test_hai_lenh_goi_cung_nganh(ctx):
    q = "Điểm chuẩn và học phí ngành Khoa học máy tính (IT1)?"
    calls, _ = run(ctx, q, [
        AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(programs=["Khoa học máy tính"])),
        TuitionCall(tool="tuition_fees", args=TuitionInput(programs=["Khoa học máy tính"]))])
    assert calls[0].args.programs == ["IT1"] and calls[1].args.programs == ["IT1"]


def test_truong_khoa_co_trong_cau_giu_nguyen(ctx):
    q = "Trường CNTT&TT ở đâu?"
    calls, fixes = run(ctx, q, [UniversityInfoCall(tool="university_info", args=UniversityInfoInput(
        faculties=["Trường CNTT&TT"], fields=["contact"]))])
    assert calls[0].args.faculties == ["Trường CNTT&TT"] and fixes == []


@pytest.mark.parametrize("q, expect", [
    ("Điểm chuẩn ngành Khoa học máy tính (IT1) theo điểm thi THPT năm 2025",
     '# Từ điển nhận ra trong câu: "IT1" (ngành) · "điểm thi THPT" (phương thức) · năm 2025'),
    ("Ký túc xá có mấy khu?", None),
    ("Học phí năm học 2026-2027?", "# Từ điển nhận ra trong câu: năm học 2026-2027 (năm bắt đầu 2026)"),
])
def test_hint_line(ctx, q, expect):
    assert hint_line(ctx.scanner.scan(q), q) == expect


def test_hint_nam_trong_phan_thay_doi_cua_prompt(ctx):
    from datetime import date
    block = context_block(empty_context(), date(2026, 10, 21), "# Từ điển nhận ra trong câu: \"IT1\" (ngành)")
    assert block.splitlines()[1].startswith("# Từ điển nhận ra")


def test_n3_ten_khong_sat_ngoac_van_doi_ra_ma(ctx):              # S37
    q = "Học phí ngành Cơ điện tử hợp tác với ĐH Leibniz Hannover (ME-LUH) năm 2026 là bao nhiêu?"
    calls, fixes = run(ctx, q, [TuitionCall(tool="tuition_fees", args=TuitionInput(
        programs=["Cơ điện tử"], program_group="Leibniz", years=[2026]))])
    assert calls[0].args.programs == ["ME-LUH"]
    assert calls[0].args.program_group is None                   # cum cung doan da duoc ma thay
    assert len(fixes) == 2


def test_n3_hai_ten_cung_doan_chi_ten_sat_ngoac_doi_ma(ctx):
    q = "So sánh điểm chuẩn Cơ điện tử và Kỹ thuật Ô tô (TE1) năm 2025"
    calls, _ = run(ctx, q, [AdmissionScoresCall(tool="admission_scores", args=AdmissionScoresInput(
        programs=["Cơ điện tử", "Kỹ thuật Ô tô"]))])
    assert calls[0].args.programs == ["Cơ điện tử", "TE1"]
