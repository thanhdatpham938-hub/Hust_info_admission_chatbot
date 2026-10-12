"""State va quy tac ngu canh (PLAN - State va Context Rules (v1), muc 5: ca M1-M32). Khong can DB, khong LLM:
Router duoc gia bang dict dinh san. Ten nganh / nhom chuong trinh lay tu du lieu that qua fixture `ctx` (doc CSV).
"""

import pytest

from app.graph.context_rules import (build_pending, merge_context, merge_pick, pick_choice, register_unclear,
                                     update_context)
from app.graph.state import MAX_HISTORY_TURNS, append_message, empty_context, empty_state, new_turn


# ---------------------------------------------------------------- helpers
def call(tool, **args):
    return {"tool": tool, "args": args}


def ctx_with(**kw):
    c = empty_context()
    c.update(kw)
    return c


def ok(status="ok", **resolved):
    """ToolResult gia: resolved={entity_type: [ma...]}."""
    return {"status": status, "resolved": [{"mention": "x", "entity_type": t, "codes": cs, "matched_by": "exact"}
                                           for t, cs in resolved.items()]}


def ambiguous(mention, cands, etype="program"):
    return {"status": "ambiguous", "clarifications": [{"mention": mention, "candidates": [
        {"code": c["code"], "name": c["name"], "entity_type": etype} for c in cands]}]}


def candidates(ctx, mention):
    r = ctx.resolve(mention, "program")
    assert r.status == "clarify", (mention, r.status)
    return [{"code": c, "name": ctx.aliases.name("program", c)} for c in r.codes]


@pytest.fixture
def oto(ctx):
    """Luot truoc: "Điểm chuẩn Kỹ thuật Ô tô 2025?" -> T1 hoi lai TE1 / TE-E2."""
    calls = [call("admission_scores", programs=["kỹ thuật ô tô"], years=[2025], methods=[])]
    # co dinh thu tu hien thi (1. TE1, 2. TE-E2) de kiem "cái thứ hai"; ten van lay tu du lieu that
    cands = sorted(candidates(ctx, "Kỹ thuật Ô tô"), key=lambda c: c["code"] != "TE1")
    return build_pending(calls, [ambiguous("kỹ thuật ô tô", cands)])


def pick(text, pending, ctx, choice=None):
    return pick_choice(text, pending, choice, ctx.program_group)


def picked_codes(out):
    return out.calls[0]["args"]["programs"] if out.calls else None


IT1_2024 = ctx_with(programs=["IT1"], years=[2024], last_tool="admission_scores", last_intent="ADMISSION_QUERY")


# ---------------------------------------------------------------- state
def test_state_rong_va_cat_lich_su():
    s = empty_state()
    assert s["context"]["pending"] is None and s["messages"] == []
    msgs = []
    for i in range(5):
        msgs = append_message(msgs, "user", f"q{i}")
        msgs = append_message(msgs, "assistant", f"a{i}")
    assert len(msgs) == 2 * MAX_HISTORY_TURNS and msgs[0]["content"] == "q2"


def test_new_turn_khong_ke_thua_luot_cu():
    t = new_turn("Điểm IT1?")
    assert t["retry"] == 0 and t["verify_issues"] == [] and "answer" not in t


# ---------------------------------------------------------------- C1-C3 merge_context
def test_m1_cung_tool_dien_nganh_giu_nam_moi():
    out = merge_context([call("admission_scores", programs=[], years=[2025], methods=[])], True, IT1_2024)
    assert out[0]["args"]["programs"] == ["IT1"] and out[0]["args"]["years"] == [2025]


def test_m2_khac_tool_chi_mang_nganh():
    out = merge_context([call("tuition_fees", programs=[], years=[])], True, IT1_2024)
    assert out[0]["args"] == {"programs": ["IT1"], "years": []}


def test_m3_khong_tham_chieu_khong_mang_gi():
    c = call("rag_search", query="Điều kiện cảnh báo học tập?", programs=[], years=[])
    assert merge_context([c], False, IT1_2024) == [c]


def test_m8_mang_truong_khoa():
    ctx = ctx_with(faculties=["SoICT"], last_tool="university_info")
    out = merge_context([call("university_info", faculties=[], fields=["channel"])], True, ctx)
    assert out[0]["args"]["faculties"] == ["SoICT"]


def test_m9_mang_hai_nganh():
    ctx = ctx_with(programs=["IT1", "IT2"], years=[2025], last_tool="admission_scores")
    out = merge_context([call("admission_scores", programs=[], years=[2024], methods=["TSA"])], True, ctx)
    assert out[0]["args"] == {"programs": ["IT1", "IT2"], "years": [2024], "methods": ["TSA"]}


def test_m11_khong_ghi_de_gia_tri_cau_moi():
    out = merge_context([call("admission_scores", programs=["IT2"], years=[], methods=[])], True, IT1_2024)
    assert out[0]["args"]["programs"] == ["IT2"] and out[0]["args"]["years"] == [2024]


def test_m12_tool_mot_gia_tri_ma_ngu_canh_nhieu_thi_khong_dien():
    many = ctx_with(years=[2024, 2025], methods=["THPT", "TSA"], last_tool="list_programs")
    out = merge_context([call("list_programs", metric="score", years=[], method=None)], True, many)
    assert out[0]["args"]["method"] is None
    one = ctx_with(years=[2025], methods=["TSA"], last_tool="list_programs")
    out = merge_context([call("list_programs", metric="score", years=[], method=None)], True, one)
    assert out[0]["args"]["method"] == "TSA"
    uni = ctx_with(years=[2024, 2025], last_tool="university_info")
    assert "year" not in merge_context([call("university_info", faculties=["SoICT"])], True, uni)[0]["args"]


def test_khong_dien_tham_so_tool_khong_co():
    ctx = ctx_with(methods=["TSA"], last_tool="program_info")
    out = merge_context([call("program_info", programs=["IT1"])], True, ctx)
    assert "methods" not in out[0]["args"]


def test_merge_khong_sua_dau_vao():
    c = call("admission_scores", programs=[], years=[2025], methods=[])
    merge_context([c], True, IT1_2024)
    assert c["args"]["programs"] == []


# ---------------------------------------------------------------- build_pending
def test_build_pending_giu_ket_qua_lenh_da_xong(ctx):
    rag_ok = ok(program=[])
    calls = [call("admission_scores", programs=["kỹ thuật ô tô"], years=[2025]), call("rag_search", query="q")]
    p = build_pending(calls, [ambiguous("kỹ thuật ô tô", candidates(ctx, "Kỹ thuật Ô tô")), rag_ok])
    assert p["index"] == 0 and p["field"] == "programs" and p["retries"] == 0
    assert p["calls"][0]["done"] is None and p["calls"][1]["done"] == rag_ok
    assert {c["code"] for c in p["candidates"]} == {"TE1", "TE-E2"}


def test_m16_hai_cum_mo_ho_chi_hoi_cum_dau(ctx):
    calls = [call("admission_scores", programs=["kỹ thuật ô tô", "cơ điện tử"], years=[2025])]
    res = {"status": "ambiguous", "clarifications": [
        {"mention": "kỹ thuật ô tô", "candidates": [{"code": "TE1", "name": "a", "entity_type": "program"},
                                                    {"code": "TE-E2", "name": "b", "entity_type": "program"}]},
        {"mention": "cơ điện tử", "candidates": [{"code": "ME1", "name": "c", "entity_type": "program"},
                                                 {"code": "ME-E1", "name": "d", "entity_type": "program"}]}]}
    p = build_pending(calls, [res])
    out = pick("TE-E2", p, ctx)
    assert out.calls[0]["args"]["programs"] == ["TE-E2", "cơ điện tử"]      # cum con lai de tool hoi tiep


def test_khong_ambiguous_thi_khong_pending():
    assert build_pending([call("admission_scores", programs=["IT1"])], [ok(program=["IT1"])]) is None


# ---------------------------------------------------------------- C4 pick_choice
@pytest.mark.parametrize("text,want", [
    ("TE-E2", ["TE-E2"]),                     # M4
    ("te e2", ["TE-E2"]),
    ("cái thứ hai", ["TE-E2"]),               # M5
    ("số 1", ["TE1"]),
    ("cái cuối", ["TE-E2"]),
    ("TE-E2 nhé", ["TE-E2"]),                 # M19: chi con tu dem
    ("hệ tiên tiến", ["TE-E2"]),              # 5a
    ("hệ chuẩn", ["TE1"]),                    # 5b
    ("Elitech", ["TE-E2"]),                   # 5b
    ("cả hai", ["TE1", "TE-E2"]),             # M26
    ("TE1 và TE-E2", ["TE1", "TE-E2"]),       # go hai ma: ro rang, lay ca hai
])
def test_pick_duong_tat(oto, ctx, text, want):
    out = pick(text, oto, ctx)
    assert picked_codes(out) == want
    assert out.calls[0]["args"]["years"] == [2025]


@pytest.mark.parametrize("text", [
    "ô tô",                                   # M13: khop ca hai -> khong doan
    "Học phí năm 2 là bao nhiêu?",            # M14: cau dai, "2" khong phai thu tu
    "TE-E2, năm 2024",                        # M20: con phan thua -> Router
    "cái tiên tiến, so với IT1 luôn",         # M21
    "TE1, học phí bao nhiêu?",                # M22
    "cái kia",
    "Học phí IT1 bao nhiêu?",                 # M6: cau moi
])
def test_pick_de_router_xu_ly(oto, ctx, text):
    assert pick(text, oto, ctx).calls is None


def test_m17_m18_nut_bam(oto, ctx):
    assert picked_codes(pick("gì cũng được", oto, ctx, choice="TE-E2")) == ["TE-E2"]
    assert picked_codes(pick("TE1", oto, ctx, choice="IT1")) == ["TE1"]       # choice ngoai danh sach -> bo qua


def test_m7_chon_khoa(ctx):
    cohorts = [{"code": "K71+", "name": "Khoá 71 trở về sau"}, {"code": "K70-", "name": "Khoá 70 trở về trước"}]
    calls = [call("certificate_lookup", certificate="TOEIC", purpose="chuan_dau_ra", cohort=None)]
    p = build_pending(calls, [ambiguous("khoá học", cohorts, etype="cohort")])
    assert p["field"] == "cohort"
    for text, want in [("K70", "K70-"), ("khoá 69", "K70-"), ("K71", "K71+"), ("năm 2026", "K71+")]:
        out = pick(text, p, ctx)
        assert out.calls and out.calls[0]["args"]["cohort"] == want, text
    assert pick("em khoá 70, còn IELTS thì sao?", p, ctx).calls is None        # P014: co phan thua


def test_viet_nhat_khong_thanh_thu_nhat(ctx):
    """"nhất" trong "Việt Nhật" khong duoc hieu la "thứ nhất" (lua chon so 1)."""
    p = build_pending([call("admission_scores", programs=["công nghệ thông tin"])],
                      [ambiguous("công nghệ thông tin", candidates(ctx, "Công nghệ thông tin"))])
    assert picked_codes(pick("Việt Nhật", p, ctx)) == ["IT-E6"]
    assert picked_codes(pick("Global ICT", p, ctx)) == ["IT-E7"]
    assert pick("chuẩn", p, ctx).calls is None                                 # IT1, IT2 deu chuan
    # P015: nhac hai lua chon -> khong duoc chi lay IT-E6, de Router chon ca hai
    assert pick("Khoa học máy tính với Việt Nhật", p, ctx).calls is None


def test_nhac_ten_day_du_cua_lua_chon(oto, ctx):
    assert picked_codes(pick("kỹ thuật ô tô tiên tiến", oto, ctx)) == ["TE-E2"]


def test_co_dien_tu_nhom_elitech_co_nhieu_nganh(ctx):
    p = build_pending([call("admission_scores", programs=["cơ điện tử"])],
                      [ambiguous("cơ điện tử", candidates(ctx, "Cơ điện tử"))])
    assert pick("Elitech", p, ctx).calls is None                               # 3 nganh cung nhom
    assert picked_codes(pick("chuẩn", p, ctx)) == ["ME1"]
    assert picked_codes(pick("Nagaoka", p, ctx)) == ["ME-NUT"]


def test_m27_tat_ca_qua_ba(ctx):
    p = build_pending([call("admission_scores", programs=["BK CNTT"])],
                      [ambiguous("BK CNTT", candidates(ctx, "BK CNTT"))])
    out = pick("tất cả", p, ctx)
    assert out.too_many and out.calls is None


def test_m15_giu_done_khi_chi_chon(ctx, oto):
    rag_done = ok()
    oto["calls"].append({"tool": "rag_search", "args": {"query": "q", "years": [2025]}, "done": rag_done})
    out = pick("TE-E2", oto, ctx)
    assert out.calls[0]["done"] is None and out.calls[1]["done"] == rag_done


# ---------------------------------------------------------------- C4 merge_pick (Router da xu ly ca cau)
def test_m20_doi_nam(oto):
    out = merge_pick(oto, ["TE-E2"], [call("admission_scores", programs=[], years=[2024])])
    assert out == [{"tool": "admission_scores", "args": {"programs": ["TE-E2"], "years": [2024], "methods": []},
                    "done": None}]


def test_m21_them_nganh_ma_da_chon_bi_khoa(oto):
    out = merge_pick(oto, ["TE-E2"], [call("admission_scores", programs=["IT1"])])
    assert out[0]["args"]["programs"] == ["TE-E2", "IT1"] and out[0]["args"]["years"] == [2025]


def test_m22_luon_chay_cau_hoi_goc(oto):
    out = merge_pick(oto, ["TE-E2"], [call("tuition_fees", programs=[])])
    assert [c["tool"] for c in out] == ["admission_scores", "tuition_fees"]
    assert out[0]["args"]["programs"] == ["TE-E2"] and out[1]["args"]["programs"] == ["TE-E2"]


def test_m23_doi_nam_thi_chay_lai_done(oto):
    oto["calls"].append({"tool": "rag_search", "args": {"query": "q", "years": [2025]}, "done": ok()})
    out = merge_pick(oto, ["TE-E2"], [call("admission_scores", years=[2024])])
    assert out[1]["args"]["years"] == [2024] and out[1]["done"] is None


def test_m24_picked_ngoai_danh_sach(oto):
    assert merge_pick(oto, ["IT1"], [call("admission_scores", programs=["IT1"])]) is None
    assert merge_pick(oto, [], []) is None


def test_m32_ca_hai_kem_doi_nam(oto):
    out = merge_pick(oto, ["TE1", "TE-E2"], [call("admission_scores", years=[2024])])
    assert out[0]["args"]["programs"] == ["TE1", "TE-E2"] and out[0]["args"]["years"] == [2024]


def test_router_chep_lai_cum_mo_ho_khong_thanh_vong_lap(oto):
    out = merge_pick(oto, ["TE-E2"], [call("admission_scores", programs=["kỹ thuật ô tô"], years=[2024])])
    assert out[0]["args"]["programs"] == ["TE-E2"]


def test_p014_chon_khoa_kem_doi_chung_chi():
    cohorts = [{"code": "K71+", "name": "Khoá 71"}, {"code": "K70-", "name": "Khoá 70"}]
    p = build_pending([call("certificate_lookup", certificate="TOEIC", purpose="chuan_dau_ra", cohort=None)],
                      [ambiguous("khoá học", cohorts, etype="cohort")])
    out = merge_pick(p, ["K70-"], [call("certificate_lookup", certificate="IELTS", purpose="chuan_dau_ra")])
    assert len(out) == 1 and out[0]["args"] == {"certificate": "IELTS", "purpose": "chuan_dau_ra", "cohort": "K70-"}


# ---------------------------------------------------------------- update_context
def test_tra_loi_luu_ma_da_xac_nhan():
    out = update_context(empty_context(), "answered", [call("admission_scores", programs=["it1"], years=[2024])],
                         [ok(program=["IT1"])], intent="ADMISSION_QUERY")
    assert out["programs"] == ["IT1"] and out["years"] == [2024]
    assert out["last_tool"] == "admission_scores" and out["pending"] is None


def test_o_khong_nhac_thi_giu():
    out = update_context(IT1_2024, "answered", [call("program_info", programs=["IT2"])], [ok(program=["IT2"])])
    assert out["programs"] == ["IT2"] and out["years"] == [2024]                 # doi nganh khong mat nam
    out = update_context(IT1_2024, "answered", [call("rag_search", query="q")], [ok()])
    assert out["programs"] == ["IT1"]


def test_khong_luu_nam_tool_tu_chon():
    out = update_context(empty_context(), "answered", [call("admission_scores", programs=["IT1"], years=[])],
                         [ok(program=["IT1"])])
    assert out["years"] == []


def test_nhom_nganh_qua_ba_ma_khong_luu():
    out = update_context(IT1_2024, "answered", [call("list_programs", metric="score", program_group="Elitech")],
                         [ok(program_group=[f"X{i}" for i in range(26)])])
    assert out["programs"] == ["IT1"]


def test_invalid_khong_xac_nhan_gi():
    out = update_context(IT1_2024, "answered", [call("admission_scores", programs=["a", "b", "c", "d"])],
                         [{"status": "invalid", "resolved": []}])
    assert out["programs"] == ["IT1"] and out["last_tool"] == "admission_scores"


def test_hoi_lai_khong_doi_ngu_canh(oto):
    out = update_context(IT1_2024, "clarify", pending=oto)
    assert out["pending"] == oto and out["programs"] == ["IT1"]
    assert out["last_intent"] == "CLARIFICATION_NEEDED" and out["last_tool"] == "admission_scores"


def test_m10_m25_tu_choi_khong_doi_gi(oto):
    before = {**IT1_2024, "pending": oto}
    assert update_context(before, "refused") == before


def test_m6_m31_cau_moi_bo_pending(oto):
    out = update_context({**IT1_2024, "pending": oto}, "answered", [call("tuition_fees", programs=["IT1"])],
                         [ok(program=["IT1"])])
    assert out["pending"] is None and out["last_tool"] == "tuition_fees"


def test_m28_huy(oto):
    out = update_context({**IT1_2024, "pending": oto}, "cancel")
    assert out["pending"] is None and out["programs"] == ["IT1"]


def test_m29_m30_unclear_hai_lan_thi_tha(oto):
    ctx1, released = register_unclear({**IT1_2024, "pending": oto})
    assert not released and ctx1["pending"]["retries"] == 1
    ctx2, released = register_unclear(ctx1)
    assert released and ctx2["pending"] is None and ctx2["programs"] == ["IT1"]
    assert oto["retries"] == 0                                                   # khong sua dau vao
