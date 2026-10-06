import asyncio
import sys

import pytest
import pytest_asyncio

from app.db.pool import close_pool, open_pool

HINT = "docker compose up -d postgres  rồi  python scripts/build_db.py --postgres"


def pytest_asyncio_loop_factories(config, item):
    # psycopg async khong chay tren ProactorEventLoop (mac dinh cua asyncio tren Windows)
    if sys.platform == "win32":
        return {"selector": asyncio.SelectorEventLoop}
    return None


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    """Pool chi doc vao schema hust. Khong ket noi duoc thi BAO LOI kem lenh can chay, khong bo qua
    im lang (D13) — bo qua thi ca bo test xanh du chua kiem tra gi."""
    try:
        pool = await open_pool(timeout=5)
    except Exception as e:
        pytest.fail(f"Không kết nối được PostgreSQL ({type(e).__name__}: {e}). Chạy: {HINT}", pytrace=False)
    yield pool
    await close_pool()
