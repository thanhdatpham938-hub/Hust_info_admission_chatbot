"""Runtime that cua server (PLAN - API (v1) muc 3, 7): mo MOT lan trong lifespan FastAPI, dong khi tat.

Gom: pool chi doc `hust` (tool), ToolContext (nap du lieu mot lan), checkpointer Postgres (pool ghi, schema
langgraph), Retriever T7 (Qdrant), graph that (Router + Synthesizer goi OpenAI). Test API dung Runtime gia cung giao
dien: `graph`, `health()`, `close()`.
"""

import logging

from app.core.config import get_settings
from app.db.pool import close_pool, fetch_one, open_pool
from app.graph.build import build_graph
from app.graph.checkpoint import close_checkpointer, open_checkpointer, ping
from app.graph.nodes import GraphDeps
from app.graph.router import route
from app.tools.context import ToolContext
from app.tools.rag_tool import close_retriever, get_retriever

log = logging.getLogger(__name__)


class Runtime:
    def __init__(self, graph, saver) -> None:
        self.graph, self.saver = graph, saver

    @classmethod
    async def open(cls) -> "Runtime":
        await open_pool()
        saver = None
        try:
            ctx = await ToolContext.load()
            saver = await open_checkpointer()
        except Exception:
            if saver is not None:
                await close_checkpointer(saver)
            await close_pool()
            raise

        async def tool_ctx() -> ToolContext:
            return ctx

        # synthesize=None -> Synthesizer that (app.graph.synthesizer.generate, co stream)
        graph = build_graph(GraphDeps(route=route, tool_ctx=tool_ctx, program_group=ctx.program_group,
                                      program_names=ctx.program_names), checkpointer=saver)
        return cls(graph, saver)

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
            r = get_retriever()
            out["qdrant"] = "ok" if await r.client.collection_exists(get_settings().qdrant_collection) else "error"
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
        await close_checkpointer(self.saver)
        await close_retriever()
        await close_pool()
