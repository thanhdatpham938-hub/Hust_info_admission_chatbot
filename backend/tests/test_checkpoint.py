"""Seam 3 cua PLAN - API (v1): checkpointer Postgres (muc 6). Can Postgres dang chay (marker db), khong goi OpenAI.

Gia lap "tat roi bat lai server": mo checkpointer, chay luot hoi lai, DONG, mo checkpointer MOI + graph MOI, luot sau
van biet dang cho chon (di duong tat pick_choice, khong goi Router).
"""

import uuid

import pytest
from app.graph.build import build_graph, chat
from app.graph.checkpoint import close_checkpointer, open_checkpointer
from app.graph.nodes import GraphDeps
from test_graph_flow import ASK, GROUPS, FakeRouter, Tools, ask_script, fake_synth

pytestmark = pytest.mark.db


def graph_with(saver, router, tools):
    return build_graph(GraphDeps(route=router, tools=tools.table(), program_group=GROUPS, synthesize=fake_synth),
                       checkpointer=saver)


async def test_tat_bat_lai_van_nho_cau_dang_cho_chon():
    tid = str(uuid.uuid4())
    saver = await open_checkpointer()
    try:
        r1 = await chat(graph_with(saver, FakeRouter(ask_script()), Tools()), tid, ASK)
        assert r1["metadata"]["intent"] == "CLARIFICATION_NEEDED"
    finally:
        await close_checkpointer(saver)

    saver = await open_checkpointer()                       # "server bat lai": pool moi, graph moi
    try:
        router, tools = FakeRouter(ask_script()), Tools()
        r2 = await chat(graph_with(saver, router, tools), tid, "TE-E2")
        assert router.seen == [] and tools.last("admission_scores")["programs"] == ["TE-E2"]
        assert r2["metadata"]["intent"] == "ADMISSION_QUERY"
        r3 = await chat(graph_with(saver, router, tools), tid, ASK)     # them luot tren cung pool (prepare_threshold)
        assert r3["metadata"]["intent"] == "CLARIFICATION_NEEDED" and len(router.seen) == 1
    finally:
        await saver.adelete_thread(tid)
        await close_checkpointer(saver)
