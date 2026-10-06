"""Pool ket noi PostgreSQL cho cac tool doc so lieu tuyen sinh (PLAN - Backend PostgreSQL (v1)).

- Moi ket noi dat search_path = hust (D3) va default_transaction_read_only = on (D9): tool viet
  "SELECT ... FROM admission_scores" khong can tien to schema, va lenh ghi nham bi Postgres tu choi.
- Dong tra ve dang dict (cot -> gia tri). Cot NUMERIC (diem, hoc phi) ra Decimal: ep sang float o
  model Pydantic dau ra cua tool, khong lam tron o day.
- Truyen danh sach bang mang Postgres: "WHERE program_code = ANY(%(codes)s)" voi codes la list.

Vong doi: open_pool() mot lan khi khoi dong (lifespan FastAPI o Tuan 4, conftest.py trong test),
close_pool() khi tat. Checkpointer LangGraph (Tuan 4) dung pool RIENG, ghi duoc, search_path = langgraph.

Windows: psycopg async khong chay tren ProactorEventLoop (mac dinh cua asyncio tren Windows) — can
WindowsSelectorEventLoopPolicy (xem tests/conftest.py).
"""

from typing import Any, LiteralString

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

DATA_SCHEMA = "hust"
_OPTIONS = f"-c search_path={DATA_SCHEMA} -c default_transaction_read_only=on"

_pool: AsyncConnectionPool | None = None


async def open_pool(url: str | None = None, *, min_size: int = 1, max_size: int = 5,
                    timeout: float = 10) -> AsyncConnectionPool:
    """Mo pool (goi lai khi da mo thi tra pool cu). Khong ket noi duoc trong `timeout` giay -> PoolTimeout."""
    global _pool
    if _pool is None:
        pool = AsyncConnectionPool(
            url or get_settings().database_url, min_size=min_size, max_size=max_size, open=False,
            # autocommit: moi cau SELECT la mot transaction chi doc rieng, khong giu transaction mo giua chung
            kwargs={"row_factory": dict_row, "autocommit": True, "options": _OPTIONS})
        await pool.open(wait=True, timeout=timeout)
        _pool = pool
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Pool PostgreSQL chưa mở — gọi await open_pool() khi khởi động")
    return _pool


async def fetch_all(sql: LiteralString, params: dict[str, Any] | tuple | None = None) -> list[dict[str, Any]]:
    """Chay mot cau SELECT co tham so (%(ten)s hoac %s), tra moi dong dang dict.
    `sql` la LiteralString: ghep chuoi tu du lieu nguoi dung vao cau SQL se bi type checker bao loi."""
    async with get_pool().connection() as con:
        cur = await con.execute(sql, params)
        return await cur.fetchall()


async def fetch_one(sql: LiteralString, params: dict[str, Any] | tuple | None = None) -> dict[str, Any] | None:
    async with get_pool().connection() as con:
        cur = await con.execute(sql, params)
        return await cur.fetchone()
