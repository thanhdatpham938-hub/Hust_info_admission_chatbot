"""Seam 2 cua PLAN - API (v1): create_app(runtime_factory) goi qua HTTP (httpx.ASGITransport).

Runtime gia: graph dung bang Router/tool/Synthesizer gia + InMemorySaver. Khong mang, khong Docker, khong OpenAI.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import httpx
import pytest
from app.api.main import create_app, with_deadline
from app.core.config import Settings
from app.graph.build import build_graph
from app.graph.nodes import GraphDeps
from test_graph_flow import (
    ASK,
    GROUPS,
    T1,
    T6,
    FakeRouter,
    Tools,
    ask_script,
    fake_synth,
    ro,
)
from test_run_turn import QUY_CHE, StreamingSynth

SCRIPT = {"Điểm IT1 2025?": ro(calls=[T1(["IT1"], [2025])])}


class FakeRuntime:
    def __init__(self, script=SCRIPT, health=None):
        self.graph = build_graph(GraphDeps(route=FakeRouter(script), tools=Tools().table(), program_group=GROUPS,
                                           synthesize=fake_synth))
        self.parts = health or {"postgres": "ok", "qdrant": "ok", "checkpointer": "ok"}
        self.closed = False

    async def health(self) -> dict:
        return {**self.parts, "dataset_version": "2026.1"}

    async def close(self) -> None:
        self.closed = True


def settings(**kw) -> Settings:
    return Settings(database_url="postgresql://khong-dung", **kw)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@asynccontextmanager
async def client_for(rt, clock=None, **kw):
    async def factory():
        return rt

    app = create_app(factory, settings(**kw), **({"clock": clock} if clock else {}))
    # ASGITransport khong tu chay lifespan -> chay tay
    async with (app.router.lifespan_context(app),
                httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c):
        yield c


async def test_chat_tra_cau_tra_loi_dung_khuon():
    tid = str(uuid.uuid4())
    async with client_for(FakeRuntime()) as c:
        r = await c.post("/api/chat", json={"thread_id": tid, "message": "Điểm IT1 2025?"})
    assert r.status_code == 200
    body = r.json()
    assert body["thread_id"] == tid
    assert body["answer"].startswith("Kết quả tra cứu admission_scores.")
    assert body["metadata"]["intent"] == "ADMISSION_QUERY" and body["clarification"] is None
    assert "_state" not in body and "draft" not in body["metadata"]


async def test_thieu_thread_id_thi_server_tao_va_dung_lai_duoc_de_bam_nut_chon():
    async with client_for(FakeRuntime(ask_script())) as c:
        r1 = await c.post("/api/chat", json={"message": ASK})
        assert r1.status_code == 200
        body = r1.json()
        tid = str(uuid.UUID(body["thread_id"]))                 # dung dang UUID
        assert body["metadata"]["intent"] == "CLARIFICATION_NEEDED"
        assert [x["code"] for x in body["clarification"]["choices"]] == ["TE1", "TE-E2"]
        r2 = await c.post("/api/chat", json={"thread_id": tid, "message": "bấm nút", "choice": "TE-E2"})
    assert r2.json()["metadata"]["intent"] == "ADMISSION_QUERY" and r2.json()["clarification"] is None


async def test_body_sai_tra_422_invalid_request():
    async with client_for(FakeRuntime()) as c:
        bad_id = await c.post("/api/chat", json={"thread_id": "1", "message": "Điểm IT1 2025?"})
        no_msg = await c.post("/api/chat", json={"thread_id": str(uuid.uuid4())})
        too_long = await c.post("/api/chat", json={"message": "a" * 4001})
    for r in (bad_id, no_msg, too_long):
        assert r.status_code == 422
        assert r.json()["error_code"] == "INVALID_REQUEST" and r.json()["message"]


class SlowRouter:
    async def __call__(self, question, ctx, history, today):
        await asyncio.sleep(5)


async def test_loi_ngoai_graph_va_qua_thoi_gian_tra_500_khong_lo_chi_tiet():
    boom = FakeRuntime({"Điểm IT1 2025?": ValueError("chi tiet noi bo bi mat")})
    slow = FakeRuntime()
    slow.graph = build_graph(GraphDeps(route=SlowRouter(), tools=Tools().table(), synthesize=fake_synth))
    async with client_for(boom) as c:
        r1 = await c.post("/api/chat", json={"message": "Điểm IT1 2025?"})
    async with client_for(slow, turn_timeout_s=0.1) as c:
        r2 = await c.post("/api/chat", json={"message": "Điểm IT1 2025?"})
    for r in (r1, r2):
        assert r.status_code == 500
        body = r.json()
        assert body["error_code"] == "INTERNAL_ERROR"
        assert "Xin lỗi" in body["answer"] and "Sorry" in body["answer"]          # chua biet ngon ngu: song ngu
        assert "bi mat" not in r.text and "Traceback" not in r.text


async def test_health_ok_va_503_khi_mot_phan_hong():
    async with client_for(FakeRuntime()) as c:
        ok = await c.get("/api/health")
    broken = FakeRuntime(health={"postgres": "error", "qdrant": "ok", "checkpointer": "ok"})
    async with client_for(broken) as c:
        bad = await c.get("/api/health")
    assert ok.status_code == 200
    assert ok.json() == {"status": "ok", "postgres": "ok", "qdrant": "ok", "checkpointer": "ok",
                         "dataset_version": "2026.1"}
    assert bad.status_code == 503 and bad.json()["status"] == "error" and bad.json()["postgres"] == "error"


def sse(text: str) -> list[tuple[str, dict]]:
    """Tach luong SSE thanh [(event, data)]."""
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


async def test_stream_luot_van_ban_gui_meta_token_final_done():
    rt = FakeRuntime(QUY_CHE)
    rt.graph = build_graph(GraphDeps(route=FakeRouter(QUY_CHE), tools=Tools().table(),
                                     synthesize=StreamingSynth("Sinh viên bị cảnh báo khi điểm thấp [{id}].")))
    tid = str(uuid.uuid4())
    async with client_for(rt) as c:
        r = await c.post("/api/chat/stream", json={"thread_id": tid, "message": "Điều kiện cảnh báo học tập?"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = sse(r.text)
    names = [e for e, _ in events]
    assert names[0] == "meta" and events[0][1] == {"thread_id": tid}
    assert names[-2:] == ["final", "done"] and "token" in names and "status" in names
    streamed = "".join(d["text"] for e, d in events if e == "token")
    final = events[-2][1]
    assert final["thread_id"] == tid and final["answer"].startswith(streamed)
    assert final["citations"][0]["title"] == "Quy chế đào tạo 2025"


async def test_stream_loi_ngoai_graph_gui_error_roi_done():
    async with client_for(FakeRuntime({"Điểm IT1 2025?": ValueError("chi tiet noi bo bi mat")})) as c:
        r = await c.post("/api/chat/stream", json={"message": "Điểm IT1 2025?"})
    events = sse(r.text)
    assert [e for e, _ in events][-2:] == ["error", "done"]
    assert events[-2][1]["error_code"] == "INTERNAL_ERROR" and "Sorry" in events[-2][1]["answer"]
    assert "bi mat" not in r.text


async def test_qua_tan_suat_tra_429_het_cua_so_thi_goi_lai_duoc():
    clock = Clock()
    q = {"message": "Điểm IT1 2025?"}
    async with client_for(FakeRuntime(), clock=clock, rate_limit_per_min=2) as c:
        for _ in range(5):
            assert (await c.get("/api/health")).status_code == 200        # health khong tinh
        assert (await c.post("/api/chat", json=q)).status_code == 200
        clock.t += 30
        assert (await c.post("/api/chat/stream", json=q)).status_code == 200
        over = await c.post("/api/chat", json=q)
        clock.t += 31                                                      # cau dau ra khoi cua so 60 s
        again = await c.post("/api/chat", json=q)
    assert over.status_code == 429 and over.json()["error_code"] == "RATE_LIMITED"
    assert over.headers["Retry-After"] == "30"
    assert again.status_code == 200


class GateRouter:
    """Router dung cho toi khi `gate` mo: giu luot dau dang chay de gui luot thu hai."""

    def __init__(self):
        self.gate, self.entered = asyncio.Event(), asyncio.Event()

    async def __call__(self, question, ctx, history, today):
        self.entered.set()
        await self.gate.wait()
        return SCRIPT["Điểm IT1 2025?"]


async def test_hai_cau_cung_luc_tren_mot_thread_thi_cau_sau_nhan_409():
    router = GateRouter()
    rt = FakeRuntime()
    rt.graph = build_graph(GraphDeps(route=router, tools=Tools().table(), synthesize=fake_synth))
    tid, q = str(uuid.uuid4()), "Điểm IT1 2025?"
    async with client_for(rt) as c:
        first = asyncio.create_task(c.post("/api/chat", json={"thread_id": tid, "message": q}))
        await router.entered.wait()
        busy = await c.post("/api/chat/stream", json={"thread_id": tid, "message": q})
        other = asyncio.create_task(c.post("/api/chat", json={"message": q}))   # thread khac: khong bi chan
        router.gate.set()
        assert (await first).status_code == 200 and (await other).status_code == 200
        after = await c.post("/api/chat", json={"thread_id": tid, "message": q})
    assert busy.status_code == 409 and busy.json()["error_code"] == "THREAD_BUSY"
    assert after.status_code == 200                                      # xong luot dau thi thread mo lai


async def test_cors_chi_cho_origin_da_khai_bao():
    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    async with client_for(FakeRuntime(), cors_origins="http://localhost:3000, https://hust-chat.vercel.app") as c:
        ok = await c.options("/api/chat", headers={"Origin": "https://hust-chat.vercel.app", **pre})
        stranger = await c.options("/api/chat", headers={"Origin": "https://evil.example", **pre})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "https://hust-chat.vercel.app"
    assert "access-control-allow-origin" not in stranger.headers


async def test_cau_thong_bao_tra_trich_dan_kenh_khong_danh_so():
    """Review 2026-11-27: node announcement dua trich dan {title, url} khong co `n` -> Citation bat buoc n gay 500."""
    q = "Viện CNTT có thông báo gì?"
    script = {q: ro(intent="ANNOUNCEMENT_QUERY", calls=[T6(["Viện CNTT"])])}
    async with client_for(FakeRuntime(script)) as c:
        r = await c.post("/api/chat", json={"message": q})
        s = await c.post("/api/chat/stream", json={"message": q})
    assert r.status_code == 200 and r.json()["metadata"]["intent"] == "ANNOUNCEMENT_QUERY"
    assert r.json()["citations"] == [{"n": None, "title": "Trường CNTT&TT", "url": "https://soict.hust.edu.vn/",
                                      "location": None}]
    assert [e for e, _ in sse(s.text)][-2:] == ["final", "done"]


async def test_het_gio_khi_dang_cho_ben_nhan_van_bao_timeout_khong_huy_ca_task():
    """Review 2026-11-27: asyncio.timeout boc qua `yield` thi het gio luc ben nhan dang ban (vd. Starlette dang send)
    se HUY task ngoai generator -> CancelledError khong duoc doi thanh TimeoutError, luong SSE dut khong co error/done."""
    async def two_events():
        yield 1
        await asyncio.sleep(0.01)
        yield 2

    gen = with_deadline(two_events(), 0.05)
    assert await anext(gen) == 1
    await asyncio.sleep(0.1)                          # ben nhan cham: het gio xay ra NGOAI generator
    with pytest.raises(TimeoutError):
        await anext(gen)
