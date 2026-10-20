"""Hoi thoai chay qua CA graph (PLAN - StateGraph (v1), G5). Router gia + tool gia + InMemorySaver:
khong goi OpenAI, khong can Postgres/Qdrant, khong ton tien."""

import uuid

import psycopg
import pytest

from app.graph.build import build_graph, chat
from app.graph.nodes import GraphDeps
from app.graph.router import RouterError, RouterOutput
from app.schemas.common import Candidate, Clarification, ErrorCode, Missing, Resolved, Source, Status, ToolResult
from app.tools.common import TOO_MANY_MESSAGE
from app.entity_resolution.normalize import normalize

OTO = [Candidate(code="TE1", name="Kỹ thuật Ô tô", entity_type="program"),
       Candidate(code="TE-E2", name="Kỹ thuật Ô tô (CT tiên tiến)", entity_type="program")]
BK = [Candidate(code=c, name=f"Ngành {c}", entity_type="program")
      for c in ("IT1", "IT2", "IT-E10", "IT-E15", "IT-E7", "IT-E6", "IT-EP")]
GROUPS = {"TE1": "chuan", "TE-E2": "elitech"}


# ---------------------------------------------------------------- Router gia
def ro(intent="ADMISSION_QUERY", calls=(), language="vi", **kw) -> RouterOutput:
    base = dict(need="", language=language, topic="tuyen_sinh", intent=intent, calls=list(calls),
                refers_to_context=False, scope_note=None, missing_info=None, pick_status=None, picked=[])
    return RouterOutput.model_validate({**base, **kw})


def T1(programs=(), years=(), methods=()):
    return {"tool": "admission_scores", "args": {"programs": list(programs), "years": list(years),
                                                 "methods": list(methods)}}


def T4(programs=()):
    return {"tool": "tuition_fees", "args": {"programs": list(programs)}}


def T6(faculties, fields=("channel",)):
    return {"tool": "university_info", "args": {"faculties": list(faculties), "fields": list(fields)}}


def T7(query, **args):
    return {"tool": "rag_search", "args": {"query": query, **args}}


class FakeRouter:
    """Kich ban theo cau hoi. Ghi lai lich su nhan duoc de kiem."""

    def __init__(self, script: dict):
        self.script, self.seen = script, []

    async def __call__(self, question, ctx, history, today):
        self.seen.append({"question": question, "history": list(history), "pending": bool(ctx.get("pending"))})
        out = self.script[question]
        if isinstance(out, Exception):
            raise out
        return out


# ---------------------------------------------------------------- tool gia
class Tools:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def table(self):
        from app.schemas.admission import AdmissionScoresInput
        from app.schemas.rag import RagSearchInput
        from app.schemas.tuition import TuitionInput
        from app.schemas.university_info import UniversityInfoInput
        return {"admission_scores": (self.t1, AdmissionScoresInput), "tuition_fees": (self.t4, TuitionInput),
                "university_info": (self.t6, UniversityInfoInput), "rag_search": (self.t7, RagSearchInput)}

    async def t1(self, inp, ctx):
        self.calls.append(("admission_scores", inp.model_dump()))
        progs = [normalize(p) for p in inp.programs]
        if "ky thuat o to" in progs:
            return ToolResult(status=Status.AMBIGUOUS, error_code=ErrorCode.ENTITY_AMBIGUOUS,
                              clarifications=[Clarification(mention="kỹ thuật ô tô", candidates=OTO)])
        if "bk cntt" in progs:
            return ToolResult(status=Status.AMBIGUOUS, clarifications=[Clarification(mention="BK CNTT", candidates=BK)])
        if "loi db" in progs:
            raise psycopg.OperationalError("mat ket noi")
        if len(inp.programs) > 3:
            return ToolResult(status=Status.INVALID, error_code=ErrorCode.INVALID_REQUEST, message=TOO_MANY_MESSAGE)
        if 2020 in inp.years:
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND,
                              missing=[Missing(what="năm 2020", reason="year_out_of_range",
                                               available_years=[2024, 2025, 2026])],
                              resolved=[Resolved(mention=p, entity_type="program", codes=[p], matched_by="exact")
                                        for p in inp.programs])
        return ToolResult(status=Status.OK, data={"rows": [{"program": p, "years": inp.years} for p in inp.programs]},
                          resolved=[Resolved(mention=p, entity_type="program", codes=[p], matched_by="exact")
                                    for p in inp.programs],
                          sources=[Source(title="Điểm chuẩn", url="https://ts.hust.edu.vn/diem-chuan")])

    async def t4(self, inp, ctx):
        self.calls.append(("tuition_fees", inp.model_dump()))
        return ToolResult(status=Status.OK, data={"programs": inp.programs},
                          resolved=[Resolved(mention=p, entity_type="program", codes=[p], matched_by="exact")
                                    for p in inp.programs])

    async def t6(self, inp, ctx):
        self.calls.append(("university_info", inp.model_dump()))
        return ToolResult(status=Status.OK, data={"faculties": [
            {"faculty_code": "SOICT", "faculty_name": "Trường CNTT&TT", "official_channel_url": "https://soict.hust.edu.vn/"}]},
            resolved=[Resolved(mention=f, entity_type="faculty", codes=["SOICT"], matched_by="exact")
                      for f in inp.faculties])

    async def t7(self, inp, ctx):
        self.calls.append(("rag_search", inp.model_dump()))
        if "ký túc xá" in inp.query:
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.LOW_RETRIEVAL_CONFIDENCE)
        if "dài" in inp.query:
            return ToolResult(status=Status.OK, data={"chunks": ["đoạn trích quy chế " * 80]})
        if "top_k" in inp.query:
            return ToolResult(status=Status.INVALID, error_code=ErrorCode.INVALID_REQUEST,
                              message="top_k phải từ 1 đến 10.")
        return ToolResult(status=Status.OK, data={"chunks": ["..."]})

    def count(self, tool):
        return sum(1 for t, _ in self.calls if t == tool)

    def last(self, tool):
        return [a for t, a in self.calls if t == tool][-1]


@pytest.fixture
def env():
    """(graph, router, tools, thread_id) moi cho moi test."""
    def make(script):
        router, tools = FakeRouter(script), Tools()
        graph = build_graph(GraphDeps(route=router, tools=tools.table(), program_group=GROUPS))
        return graph, router, tools, str(uuid.uuid4())
    return make


def ctx_of(r):
    return r["_state"]["context"]


# ================================================================ mot luot
async def test_tra_loi_mot_luot(env):
    g, router, tools, tid = env({"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])])})
    r = await chat(g, tid, "Điểm IT1 2025?")
    assert r["metadata"]["intent"] == "ADMISSION_QUERY" and r["metadata"]["draft"] is True
    assert "IT1" in r["answer"] and r["citations"] == [{"title": "Điểm chuẩn", "url": "https://ts.hust.edu.vn/diem-chuan"}]
    assert ctx_of(r)["programs"] == ["IT1"] and ctx_of(r)["years"] == [2025]


@pytest.mark.parametrize("intent,reason", [("OTHER_UNIVERSITY", "other_university"),
                                           ("GENERAL_OFF_TOPIC", "off_topic")])
async def test_tu_choi(env, intent, reason):
    g, _, tools, tid = env({"q": ro(intent=intent)})
    r = await chat(g, tid, "q")
    assert r["metadata"]["fallback_reason"] == reason and tools.calls == []


async def test_ngon_ngu_khac_cau_song_ngu(env):
    g, _, _, tid = env({"IT1专业的学费是多少？": ro(intent="UNKNOWN", language="other")})
    r = await chat(g, tid, "IT1专业的学费是多少？")
    assert "Mình hỗ trợ tiếng Việt và tiếng Anh" in r["answer"] and "I support Vietnamese and English" in r["answer"]


async def test_tieng_anh_cau_mau_tieng_anh(env):
    g, _, _, tid = env({"UET score?": ro(intent="OTHER_UNIVERSITY", language="en")})
    r = await chat(g, tid, "UET score?")
    assert r["answer"].startswith("I can only help") and r["metadata"]["language"] == "en"


async def test_thieu_thong_tin(env):
    g, _, tools, tid = env({"điểm bao nhiêu?": ro(intent="CLARIFICATION_NEEDED", missing_info="ngành")})
    r = await chat(g, tid, "điểm bao nhiêu?")
    assert r["answer"].startswith("Bạn muốn hỏi về ngành nào?") and r["metadata"]["intent"] == "CLARIFICATION_NEEDED"
    assert tools.calls == []


async def test_thong_bao_tra_link(env):
    g, _, _, tid = env({"Viện CNTT có thông báo gì?": ro(intent="ANNOUNCEMENT_QUERY", calls=[T6(["Viện CNTT"])])})
    r = await chat(g, tid, "Viện CNTT có thông báo gì?")
    assert "https://soict.hust.edu.vn/" in r["answer"] and r["metadata"]["intent"] == "ANNOUNCEMENT_QUERY"
    assert r["citations"][0]["url"] == "https://soict.hust.edu.vn/"


async def test_do_tin_cay_thap(env):
    g, _, _, tid = env({"Ký túc xá bao nhiêu chỗ?": ro(intent="REGULATION_QUERY", calls=[T7("ký túc xá bao nhiêu chỗ")])})
    r = await chat(g, tid, "Ký túc xá bao nhiêu chỗ?")
    assert r["metadata"]["fallback_reason"] == "low_confidence" and "ts.hust.edu.vn" in r["answer"]


async def test_khong_co_du_lieu_noi_ro_co_gi(env):
    g, _, _, tid = env({"Điểm IT1 năm 2020?": ro(calls=[T1(["IT1"], [2020])])})
    r = await chat(g, tid, "Điểm IT1 năm 2020?")
    assert "năm 2020" in r["answer"] and "Hiện có dữ liệu năm 2024, 2025, 2026." in r["answer"]
    assert ctx_of(r)["programs"] == ["IT1"]                     # cau hop le: van nho nganh


async def test_qua_ba_nganh(env):
    g, _, _, tid = env({"4 ngành": ro(calls=[T1(["IT1", "IT2", "IT3", "IT4"], [2025])])})
    r = await chat(g, tid, "4 ngành")
    assert r["metadata"]["fallback_reason"] == "too_many" and "tối đa 3 ngành" in r["answer"]
    assert ctx_of(r)["programs"] == []


async def test_invalid_khac_khong_lo_cau_ky_thuat(env):
    g, _, _, tid = env({"x": ro(intent="REGULATION_QUERY", calls=[T7("top_k")])})
    r = await chat(g, tid, "x")
    assert r["metadata"]["fallback_reason"] == "no_tool" and "top_k" not in r["answer"]


async def test_loi_db(env):
    g, _, _, tid = env({"x": ro(calls=[T1(["loi db"])])})
    r = await chat(g, tid, "x")
    assert r["metadata"]["error_code"] == "DATABASE_ERROR" and "sự cố" in r["answer"]


async def test_loi_router(env):
    g, _, tools, tid = env({"x": RouterError("timeout")})
    r = await chat(g, tid, "x")
    assert r["metadata"]["error_code"] == "LLM_ERROR" and tools.calls == []


async def test_intent_noi_dung_ma_khong_goi_tool(env):
    g, _, _, tid = env({"x": ro(calls=[])})
    r = await chat(g, tid, "x")
    assert r["metadata"]["fallback_reason"] == "no_tool"


# ================================================================ nhieu luot: ngu canh (C1-C3)
async def test_m1_the_con_2025(env):
    g, router, tools, tid = env({"Điểm IT1 2024?": ro(calls=[T1(["IT1"], [2024])]),
                                 "Thế còn 2025?": ro(calls=[T1([], [2025])], refers_to_context=True)})
    await chat(g, tid, "Điểm IT1 2024?")
    await chat(g, tid, "Thế còn 2025?")
    assert tools.last("admission_scores")["programs"] == ["IT1"] and tools.last("admission_scores")["years"] == [2025]
    h = router.seen[1]["history"]
    assert [m["role"] for m in h] == ["user", "assistant"] and h[0]["content"] == "Điểm IT1 2024?"


async def test_m2_khac_tool_khong_mang_nam(env):
    g, _, tools, tid = env({"Điểm IT1 2024?": ro(calls=[T1(["IT1"], [2024])]),
                            "Học phí ngành này?": ro(calls=[T4([])], refers_to_context=True)})
    await chat(g, tid, "Điểm IT1 2024?")
    await chat(g, tid, "Học phí ngành này?")
    assert tools.last("tuition_fees")["programs"] == ["IT1"] and tools.last("tuition_fees")["years"] == []


async def test_m10_tu_choi_giu_ngu_canh(env):
    g, _, _, tid = env({"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])]), "UET?": ro(intent="OTHER_UNIVERSITY")})
    await chat(g, tid, "Điểm IT1 2025?")
    r = await chat(g, tid, "UET?")
    assert ctx_of(r)["programs"] == ["IT1"]


async def test_hai_thread_khong_lan(env):
    g, _, _, tid = env({"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])]), "UET?": ro(intent="OTHER_UNIVERSITY")})
    await chat(g, tid, "Điểm IT1 2025?")
    r = await chat(g, "thread-khac", "UET?")
    assert ctx_of(r)["programs"] == []


async def test_lich_su_cat_ngan_cau_tra_loi_van_day_du(env):
    g, _, _, tid = env({"dài": ro(intent="REGULATION_QUERY", calls=[T7("trả lời dài")])})
    r = await chat(g, tid, "dài")
    assert len(r["answer"]) > 500                                    # API nhan ban day du
    saved = r["_state"]["messages"][-1]
    assert saved["role"] == "assistant" and saved["content"] == r["answer"][:500] + "…"


# ================================================================ hoi lai va chon (C4, C5)
ASK = "Điểm Kỹ thuật Ô tô 2025?"


def ask_script(**more):
    return {ASK: ro(calls=[T1(["kỹ thuật ô tô"], [2025])]), **more}


async def test_m4_hoi_lai_roi_chon_ma_khong_goi_router(env):
    g, router, tools, tid = env(ask_script())
    r = await chat(g, tid, ASK)
    assert r["metadata"]["intent"] == "CLARIFICATION_NEEDED"
    assert "1. TE1 – Kỹ thuật Ô tô" in r["answer"] and r["clarification"]["choices"][1]["code"] == "TE-E2"
    assert ctx_of(r)["pending"]["mention"] == "kỹ thuật ô tô"
    r = await chat(g, tid, "TE-E2")
    assert len(router.seen) == 1                                 # duong tat: khong goi Router
    assert tools.last("admission_scores")["programs"] == ["TE-E2"] and tools.last("admission_scores")["years"] == [2025]
    assert r["metadata"]["intent"] == "ADMISSION_QUERY"
    assert ctx_of(r)["pending"] is None and ctx_of(r)["programs"] == ["TE-E2"]


@pytest.mark.parametrize("text,choice,want", [("cái thứ hai", None, "TE-E2"), ("hệ chuẩn", None, "TE1"),
                                              ("bấm nút", "TE1", "TE1")])
async def test_m5_chon_bang_thu_tu_dac_diem_nut_bam(env, text, choice, want):
    g, router, tools, tid = env(ask_script())
    await chat(g, tid, ASK)
    await chat(g, tid, text, choice=choice)
    assert tools.last("admission_scores")["programs"] == [want] and len(router.seen) == 1


async def test_m15_giu_ket_qua_da_co(env):
    script = {ASK: ro(calls=[T1(["kỹ thuật ô tô"], [2025]), T7("cách tính điểm ô tô")])}
    g, _, tools, tid = env(script)
    await chat(g, tid, ASK)
    assert tools.count("rag_search") == 1
    await chat(g, tid, "TE-E2")
    assert tools.count("rag_search") == 1                       # khong chay lai T7
    assert tools.count("admission_scores") == 2


async def test_m6_hoi_cau_khac_khi_dang_cho(env):
    g, _, tools, tid = env(ask_script(**{"Học phí IT1?": ro(calls=[T4(["IT1"])], pick_status="new_question")}))
    await chat(g, tid, ASK)
    r = await chat(g, tid, "Học phí IT1?")
    assert tools.last("tuition_fees")["programs"] == ["IT1"] and ctx_of(r)["pending"] is None


async def test_m20_chon_kem_doi_nam(env):
    g, router, tools, tid = env(ask_script(**{"TE-E2, năm 2024": ro(calls=[T1([], [2024])], pick_status="picked",
                                                                     picked=["TE-E2"])}))
    await chat(g, tid, ASK)
    await chat(g, tid, "TE-E2, năm 2024")
    assert len(router.seen) == 2                                 # co phan thua -> Router
    assert tools.last("admission_scores")["programs"] == ["TE-E2"] and tools.last("admission_scores")["years"] == [2024]


async def test_m22_chon_kem_cau_khac_van_chay_cau_goc(env):
    g, _, tools, tid = env(ask_script(**{"TE1, học phí bao nhiêu?": ro(calls=[T4([])], pick_status="picked",
                                                                         picked=["TE1"])}))
    await chat(g, tid, ASK)
    await chat(g, tid, "TE1, học phí bao nhiêu?")
    assert tools.last("admission_scores")["programs"] == ["TE1"] and tools.last("tuition_fees")["programs"] == ["TE1"]


async def test_m25_tu_choi_khi_dang_cho_giu_pending(env):
    g, _, _, tid = env(ask_script(**{"Điểm UET?": ro(intent="OTHER_UNIVERSITY", pick_status="new_question")}))
    await chat(g, tid, ASK)
    r = await chat(g, tid, "Điểm UET?")
    assert r["metadata"]["fallback_reason"] == "other_university" and ctx_of(r)["pending"] is not None


async def test_m28_huy(env):
    g, _, _, tid = env({"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])]), **ask_script(),
                        "thôi không cần nữa": ro(intent="UNKNOWN", pick_status="cancel")})
    await chat(g, tid, "Điểm IT1 2025?")
    await chat(g, tid, ASK)
    r = await chat(g, tid, "thôi không cần nữa")
    assert r["answer"] == "Bạn còn cần giải đáp thắc mắc nào nữa không?"
    assert ctx_of(r)["pending"] is None and ctx_of(r)["programs"] == ["IT1"]


async def test_m29_m30_khong_ro_hai_lan_thi_tha(env):
    g, _, tools, tid = env(ask_script(**{"cái kia": ro(intent="UNKNOWN", pick_status="unclear"),
                                         "ừ": ro(intent="UNKNOWN", pick_status="unclear")}))
    await chat(g, tid, ASK)
    r = await chat(g, tid, "cái kia")
    assert "chưa rõ bạn chọn" in r["answer"] and "TE1 / TE-E2" in r["answer"]
    assert ctx_of(r)["pending"]["retries"] == 1
    r = await chat(g, tid, "ừ")
    assert r["metadata"]["fallback_reason"] == "released" and "kỹ thuật ô tô" in r["answer"]
    assert ctx_of(r)["pending"] is None and tools.count("admission_scores") == 1


async def test_m27_tat_ca_qua_ba(env):
    g, router, tools, tid = env({"Điểm BK CNTT?": ro(calls=[T1(["BK CNTT"])])})
    await chat(g, tid, "Điểm BK CNTT?")
    r = await chat(g, tid, "tất cả")
    assert "tối đa 3" in r["answer"] and len(router.seen) == 1 and ctx_of(r)["pending"] is not None


async def test_tieng_anh_hoi_lai_va_duong_tat_giu_ngon_ngu(env):
    q = "Automotive Engineering cut-off 2025?"
    g, router, _, tid = env({q: ro(calls=[T1(["kỹ thuật ô tô"], [2025])], language="en")})
    r = await chat(g, tid, q)
    assert "could be one of the following programs" in r["answer"]
    r = await chat(g, tid, "TE-E2")
    assert r["metadata"]["language"] == "en" and len(router.seen) == 1
