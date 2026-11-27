"""FastAPI (PLAN - API (v1)). Seam 2: create_app(runtime_factory, settings).

Lop mong: kiem body, goi run_turn() (app/graph/run.py), doi su kien thanh JSON / SSE. Moi quy tac tra loi nam
trong graph. Runtime (pool, ToolContext, checkpointer, graph) mo mot lan trong lifespan; test truyen Runtime gia.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.limits import RateLimiter, ThreadLocks
from app.api.schemas import ChatRequest, ChatResponse, ErrorBody
from app.core.config import Settings, get_settings
from app.graph import templates as T
from app.graph.run import run_turn

log = logging.getLogger(__name__)
RuntimeFactory = Callable[[], Awaitable[Any]]
# Loi ngoai graph chua biet ngon ngu nguoi hoi -> in ca hai ban (templates.render "other")
INTERNAL_ANSWER = T.render("internal_error", "other")


def error(status: int, code: str, message: str, answer: str | None = None,
          headers: dict[str, str] | None = None) -> JSONResponse:
    body = ErrorBody(error_code=code, message=message, answer=answer).model_dump(exclude_none=True)
    return JSONResponse(body, status_code=status, headers=headers)


async def with_deadline(agen: AsyncIterator, seconds: float) -> AsyncIterator:
    """Gioi han CA luot (Q7). Chi boc timeout quanh tung lan cho phan tu ke tiep, KHONG boc qua `yield`: neu boc qua
    yield, het gio luc ben nhan dang ban (Starlette dang send) se huy task o ngoai generator -> CancelledError khong
    duoc doi thanh TimeoutError, luong SSE dut khong co error/done (review 2026-11-27)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError
            try:
                async with asyncio.timeout(remaining):
                    x = await anext(agen)
            except StopAsyncIteration:
                return
            yield x
    finally:
        await agen.aclose()


def sse_line(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def internal_error() -> JSONResponse:
    return error(500, "INTERNAL_ERROR", "Lỗi hệ thống", INTERNAL_ANSWER)


def create_app(runtime_factory: RuntimeFactory, settings: Settings | None = None,
               clock: Callable[[], float] = time.monotonic) -> FastAPI:
    """`clock`: test truyen dong ho gia de kiem cua so 60 s."""
    s = settings or get_settings()
    limiter = RateLimiter(s.rate_limit_per_min, clock)
    locks = ThreadLocks(s.turn_timeout_s + 10, clock)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime = await runtime_factory()
        try:
            yield
        finally:
            await app.state.runtime.close()

    app = FastAPI(title="HUST Info & Admission Assistant", lifespan=lifespan)
    app.state.settings = s
    # Frontend khac cong/ten mien -> trinh duyet chan neu khong khai bao. Chi GET, POST; khong cookie
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",") if o.strip()],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", ())[1:]) or "body"
        return error(422, "INVALID_REQUEST", f"{where}: {first.get('msg', 'dữ liệu không hợp lệ')}")

    def refuse(request: Request, tid: str) -> JSONResponse | None:
        """Kiem truoc khi chay luot (va truoc khi mo luong SSE). Khong tu choi thi thread DA bi khoa: noi goi phai
        release. IP sau proxy: bat --proxy-headers cua uvicorn."""
        wait = limiter.hit(request.client.host if request.client else "?")
        if wait is not None:
            return error(429, "RATE_LIMITED", f"Bạn gửi quá {s.rate_limit_per_min} câu mỗi phút, thử lại sau {wait} giây.",
                         headers={"Retry-After": str(wait)})
        if not locks.acquire(tid):
            return error(409, "THREAD_BUSY", "Câu trước trong cuộc trò chuyện này chưa trả lời xong.")
        return None

    def events(request: Request, tid: str, req: ChatRequest) -> AsyncIterator[dict]:
        """run_turn() co gioi han ca luot (Q7: 60 s). Loi/qua gio -> nem ra de route doi thanh 500 / su kien error."""
        return with_deadline(run_turn(request.app.state.runtime.graph, tid, req.message, req.choice),
                             s.turn_timeout_s)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest, request: Request):
        tid = str(req.thread_id or uuid.uuid4())
        if (no := refuse(request, tid)) is not None:
            return no
        try:
            final = [ev async for ev in events(request, tid, req) if ev["event"] == "final"][-1]["data"]
        except Exception:                                  # log day du, nguoi dung chi thay cau mau
            log.exception("Luot hoi loi ngoai graph (thread %s)", tid[:8])
            return internal_error()
        finally:
            locks.release(tid)
        return {"thread_id": tid, **final}

    @app.post("/api/chat/stream")
    async def chat_stream(req: ChatRequest, request: Request):
        """SSE (muc 4.2): meta -> status/token/replace... -> final -> done. Loi sau khi da mo luong -> error -> done.
        Nguoi dung dong trang thi Starlette huy generator: luot dang chay bi huy, khong ghi checkpoint (run_turn dung
        durability="exit"); cau hoi treo neu co do start_turn bo o luot sau."""
        tid = str(req.thread_id or uuid.uuid4())
        if (no := refuse(request, tid)) is not None:
            return no

        async def body() -> AsyncIterator[str]:
            try:
                yield sse_line("meta", {"thread_id": tid})
                try:
                    async for ev in events(request, tid, req):
                        data = ev["data"]
                        if ev["event"] == "final":
                            data = ChatResponse.model_validate({"thread_id": tid, **data}).model_dump(mode="json")
                        yield sse_line(ev["event"], data)
                except Exception:                          # log day du, nguoi dung chi thay cau mau
                    log.exception("Luot hoi loi ngoai graph (thread %s, stream)", tid[:8])
                    yield sse_line("error", ErrorBody(error_code="INTERNAL_ERROR", message="Lỗi hệ thống",
                                                      answer=INTERNAL_ANSWER).model_dump())
                yield sse_line("done", {})
            finally:                                       # ca khi nguoi dung dong trang (generator bi huy)
                locks.release(tid)

        # X-Accel-Buffering: proxy (nginx/Render) khong gom luong lai roi moi gui
        return StreamingResponse(body(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/health")
    async def health(request: Request) -> JSONResponse:
        """Kiem Postgres, Qdrant, checkpointer (Runtime.health). KHONG goi OpenAI (Q8): bi goi dinh ky, ton tien va
        cham; thieu key thi luot chat da tu tra LLM_ERROR. Khong tinh vao gioi han tan suat."""
        parts = await request.app.state.runtime.health()
        ok = all(v == "ok" for k, v in parts.items() if k != "dataset_version")
        return JSONResponse({"status": "ok" if ok else "error", **parts}, status_code=200 if ok else 503)

    return app
