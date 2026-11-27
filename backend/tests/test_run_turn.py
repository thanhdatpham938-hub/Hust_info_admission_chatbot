"""Seam 1 cua PLAN - API (v1): run_turn() phat luong su kien cua mot luot (muc 4.2, 5).

Router gia + tool gia + Synthesizer gia + InMemorySaver: khong goi OpenAI, khong can Postgres/Qdrant.
"""

import json
import uuid

import pytest
from app.graph.build import build_graph
from app.graph.nodes import GraphDeps
from app.graph.run import run_turn
from test_graph_flow import GROUPS, T1, T7, FakeRouter, Tools, fake_synth, ro


class StreamingSynth:
    """Synthesizer gia biet stream: tra lan luot cac ban trong `drafts`, moi tu goi on_token mot lan."""

    def __init__(self, *drafts):
        self.drafts, self.calls = list(drafts), 0

    async def __call__(self, payload, issues, on_token=None):
        chunk_id = payload["evidence"][0]["chunks"][0]["id"]
        text = self.drafts[min(self.calls, len(self.drafts) - 1)].format(id=chunk_id)
        self.calls += 1
        if on_token:
            for i, word in enumerate(text.split(" ")):
                on_token(word if i == 0 else " " + word)
        return text


QUY_CHE = {"Điều kiện cảnh báo học tập?": ro(intent="REGULATION_QUERY", calls=[T7("cảnh báo học tập")])}


def make_graph(script, synth=fake_synth):
    router, tools = FakeRouter(script), Tools()
    return build_graph(GraphDeps(route=router, tools=tools.table(), program_group=GROUPS, synthesize=synth))


async def collect(graph, question, choice=None, thread_id=None):
    return [e async for e in run_turn(graph, thread_id or str(uuid.uuid4()), question, choice)]


def names(events):
    return [e["event"] for e in events]


async def test_luot_so_lieu_chi_bao_tien_do_roi_gui_ca_cau():
    g = make_graph({"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])])})
    events = await collect(g, "Điểm IT1 2025?")
    assert names(events) == ["status", "status", "status", "status", "final"]
    assert [e["data"]["step"] for e in events[:-1]] == ["routing", "searching", "writing", "checking"]
    final = events[-1]["data"]
    assert final["answer"].startswith("Kết quả tra cứu admission_scores.")
    assert final["metadata"]["intent"] == "ADMISSION_QUERY"
    assert "_state" not in final and "draft" not in final["metadata"]


async def test_luot_chi_van_ban_stream_tung_chu_roi_gui_cau_chot():
    g = make_graph(QUY_CHE, StreamingSynth("Sinh viên bị cảnh báo khi điểm thấp [{id}]."))
    events = await collect(g, "Điều kiện cảnh báo học tập?")
    assert names(events)[-1] == "final"
    streamed = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert streamed == "Sinh viên bị cảnh báo khi điểm thấp [1]."
    assert names(events).index("token") < names(events).index("final")
    final = events[-1]["data"]["answer"]
    assert final.startswith(streamed) and final != streamed       # cau chot them khoi Nguon do code ghep
    assert "Quy chế đào tạo 2025" in final


async def test_ban_da_stream_bi_verify_loai_thi_bao_xoa_roi_stream_ban_moi():
    synth = StreamingSynth("Quy chế yêu cầu 99 tín chỉ [{id}].",          # so la -> verify loai
                           "Sinh viên bị cảnh báo khi điểm thấp [{id}].")
    g = make_graph(QUY_CHE, synth)
    events = await collect(g, "Điều kiện cảnh báo học tập?")
    seq = [e["event"] for e in events if e["event"] in ("token", "replace", "final")]
    cut = seq.index("replace")
    assert set(seq[:cut]) == {"token"} and seq.count("replace") == 1
    assert set(seq[cut + 1:-1]) == {"token"} and seq[-1] == "final"
    after = "".join(e["data"]["text"] for e in events[[e["event"] for e in events].index("replace"):]
                    if e["event"] == "token")
    assert after == "Sinh viên bị cảnh báo khi điểm thấp [1]."
    final = events[-1]["data"]
    assert "99" not in final["answer"] and final["metadata"]["rewrites"] == 1


async def test_luot_loi_giua_chung_khong_de_lai_cau_hoi_treo_trong_lich_su():
    """Review 2026-11-27: LangGraph luu checkpoint sau MOI buoc. Luot loi/het gio/bi huy giua chung (sau start_turn)
    de lai cau hoi trong `messages` ma khong co cau tra loi -> luot sau Router thay hai cau hoi lien tiep."""
    q1, q2, q3 = "Điểm IT1 2025?", "Điểm IT2 2025?", "Điểm IT1 2024?"
    router = FakeRouter({q1: ro(calls=[T1(["IT1"], [2025])]), q2: ro(calls=[T1(["IT2"], [2025])]),
                         q3: ro(calls=[T1(["IT1"], [2024])])})

    async def synth(payload, issues, on_token=None):
        if "IT2" in json.dumps(payload, ensure_ascii=False):
            raise RuntimeError("loi ngoai du kien")          # khong phai SynthError -> thoat khoi graph
        return await fake_synth(payload, issues)

    g = build_graph(GraphDeps(route=router, tools=Tools().table(), program_group=GROUPS, synthesize=synth))
    tid = str(uuid.uuid4())
    await collect(g, q1, thread_id=tid)
    with pytest.raises(RuntimeError):
        await collect(g, q2, thread_id=tid)
    await collect(g, q3, thread_id=tid)
    history = router.seen[-1]["history"]
    assert [m["content"] for m in history if m["role"] == "user"] == [q1]
