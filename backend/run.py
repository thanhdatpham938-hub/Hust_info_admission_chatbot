"""Chay server API (PLAN - API (v1) muc 7). Tu goc du an:  python backend/run.py  [--host 127.0.0.1] [--port 8000]

- Windows: psycopg async khong chay tren ProactorEventLoop (mac dinh cua asyncio) -> chay uvicorn tren
  SelectorEventLoop qua asyncio.run(loop_factory=...) (Python 3.12+). Khong dung --reload: tien trinh con tu tao vong
  lap, bo qua cho dat nay.
- 1 worker: gioi han tan suat va khoa theo thread dem trong bo nho cua tien trinh.
- --proxy-headers: sau proxy (Render) lay IP that tu X-Forwarded-For cho gioi han tan suat.
"""

import argparse
import asyncio
import logging
import sys

import uvicorn
from app.api.main import create_app
from app.runtime import Runtime

app = create_app(Runtime.open)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--proxy-headers", action="store_true", help="bat khi chay sau proxy (deploy)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    server = uvicorn.Server(uvicorn.Config(app, host=a.host, port=a.port, proxy_headers=a.proxy_headers,
                                           forwarded_allow_ips="*" if a.proxy_headers else None))
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(server.serve(), loop_factory=factory)


if __name__ == "__main__":
    main()
