"""Runtime that cua server (PLAN - API (v1) muc 3, 7): mo MOT lan trong lifespan FastAPI, dong khi tat.

Gom: pool chi doc `hust` (tool), ToolContext (nap du lieu mot lan), checkpointer Postgres (pool ghi, schema
langgraph), Retriever T7 (Qdrant), graph that (Router + Synthesizer goi OpenAI). Test API dung Runtime gia cung giao
dien: `graph`, `health()`, `close()`.

Tai nguyen dong bang AsyncExitStack (review 2026-11-27): buoc nao loi khi mo thi dong nguoc nhung cai da mo; khi tat,
mot cai dong loi khong lam bo sot cac cai con lai.
"""

import logging
from contextlib import AsyncExitStack

from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.db.pool import close_pool, fetch_one, open_pool
from app.graph.build import build_graph
from app.graph.checkpoint import close_checkpointer, open_checkpointer, ping
from app.graph.nodes import GraphDeps
from app.graph.router import route
from app.tools.context import ToolContext
from app.tools.rag_tool import close_retriever

log = logging.getLogger(__name__)


class Runtime:
    def __init__(self, graph, saver, qdrant: AsyncQdrantClient, stack: AsyncExitStack) -> None:
        self.graph, self.saver, self.qdrant, self._stack = graph, saver, qdrant, stack

    @classmethod
    async def open(cls) -> "Runtime":
        s = get_settings()
        async with AsyncExitStack() as stack:
            await open_pool()
            stack.push_async_callback(close_pool)
            stack.push_async_callback(close_retriever)          # Retriever T7 tao luoi o luot dau, dong khi tat
            ctx = await ToolContext.load()
            saver = await open_checkpointer()
            stack.push_async_callback(close_checkpointer, saver)
            # Client Qdrant RIENG cho /api/health: Retriever tao kem AsyncOpenAI, thieu OPENAI_API_KEY thi nem loi ->
            # health bao nham Qdrant hong (Q8: health khong phu thuoc OpenAI)
            qdrant = AsyncQdrantClient(url=s.qdrant_url.replace("localhost", "127.0.0.1"), timeout=5)
            stack.push_async_callback(qdrant.close)

            async def tool_ctx() -> ToolContext:
                return ctx

            # synthesize=None -> Synthesizer that (app.graph.synthesizer.generate, co stream)
            graph = build_graph(GraphDeps(route=route, tool_ctx=tool_ctx, program_group=ctx.program_group,
                                          program_names=ctx.program_names), checkpointer=saver)
            return cls(graph, saver, qdrant, stack.pop_all())   # mo xong: chuyen quyen dong cho Runtime.close

    async def health(self) -> dict:
        """Tung phan "ok" / "error"; khong goi OpenAI (Q8)."""
        out, version = {}, None
        try:
            row = await fetch_one("SELECT dataset_version FROM build_info LIMIT 1")
            version = row["dataset_version"] if row else None
            out["postgres"] = "ok"
        except Exception as e:                             # noqa: BLE001 — health bao loi, khong nem
            log.warning("health postgres: %s", e)
            out["postgres"] = "error"
        try:
            ok = await self.qdrant.collection_exists(get_settings().qdrant_collection)
            out["qdrant"] = "ok" if ok else "error"
        except Exception as e:                             # noqa: BLE001
            log.warning("health qdrant: %s", e)
            out["qdrant"] = "error"
        try:
            await ping(self.saver)
            out["checkpointer"] = "ok"
        except Exception as e:                             # noqa: BLE001
            log.warning("health checkpointer: %s", e)
            out["checkpointer"] = "error"
        return {**out, "dataset_version": version}

    async def close(self) -> None:
        await self._stack.aclose()
