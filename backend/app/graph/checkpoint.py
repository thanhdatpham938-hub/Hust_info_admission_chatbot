"""Checkpointer Postgres cho hoi thoai (PLAN - API (v1) muc 6; plan Tuan 4 muc 7). Seam 3.

- Pool RIENG, ghi duoc, search_path = langgraph. Pool cua tool (app/db/pool.py) giu chi doc, schema hust.
  Vi sao schema rieng: build_db.py --postgres xoa va dung lai `hust`, hoi thoai khong mat theo.
- Ba tuy chon ket noi theo tai lieu LangGraph cho AsyncPostgresSaver: autocommit (setup() co CREATE INDEX
  CONCURRENTLY, khong chay trong transaction), row_factory=dict_row (saver doc cot theo ten), prepare_threshold=0.
  Luu y psycopg: 0 = prepare NGAY lan chay dau; None moi la TAT prepared statement. Deploy sau PgBouncer che do
  transaction (vd. mot so goi Postgres tren Render) thi phai doi thanh None, neu khong se loi
  'prepared statement ... does not exist' (review 2026-11-27).
- Lan dau: CREATE SCHEMA IF NOT EXISTS langgraph roi setup() tao bang; chay lai khong sao.
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

SCHEMA = "langgraph"


async def open_checkpointer(url: str | None = None, *, max_size: int = 5, timeout: float = 10) -> AsyncPostgresSaver:
    pool = AsyncConnectionPool(
        url or get_settings().database_url, min_size=1, max_size=max_size, open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row,
                "options": f"-c search_path={SCHEMA}"})
    await pool.open(wait=True, timeout=timeout)
    try:
        async with pool.connection() as con:
            await con.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
    except Exception:
        await pool.close()
        raise
    return saver


async def close_checkpointer(saver: AsyncPostgresSaver) -> None:
    await saver.conn.close()


async def ping(saver: AsyncPostgresSaver) -> None:
    """Cho /api/health: nem loi neu khong ket noi duoc."""
    async with saver.conn.connection() as con:
        await con.execute("SELECT 1")
