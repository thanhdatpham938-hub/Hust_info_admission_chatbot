"""Gioi han tan suat theo IP va khoa theo thread_id (PLAN - API (v1) muc 7).

Dem trong bo nho cua MOT tien trinh: chay 1 worker uvicorn, nhieu worker thi moi worker dem rieng, gioi han mat tac
dung. Mat khi restart: chap nhan cho MVP (plan Tuan 4 Q7).
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable

WINDOW_S = 60.0
SWEEP_EVERY = 1000         # moi 1.000 lan goi thi don khoa cu: khong phinh bo nho theo so IP / thread tung gap (review)


class RateLimiter:
    """Cua so truot 60 s. hit(key) ghi nhan mot lan goi; qua gioi han thi tra so giay phai cho (Retry-After)."""

    def __init__(self, per_min: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_min, self.clock = per_min, clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.calls = 0

    def hit(self, key: str) -> int | None:
        now = self.clock()
        self.calls += 1
        if self.calls % SWEEP_EVERY == 0:
            for k in [k for k, q in self.hits.items() if not q or q[-1] <= now - WINDOW_S]:
                del self.hits[k]
        q = self.hits[key]
        while q and q[0] <= now - WINDOW_S:
            q.popleft()
        if len(q) >= self.per_min:
            return max(1, math.ceil(q[0] + WINDOW_S - now))
        q.append(now)
        return None


class ThreadLocks:
    """Moi thread_id chi mot luot chay mot luc (Q4 = A: luot sau nhan 409). Hai luot song song tren cung thread se
    ghi de `context` cua nhau (luot sau doc checkpoint cu).

    Khoa co han `ttl` (= gioi han ca luot + du phong): nguoi dung ngat ket noi truoc khi luong SSE kip bat dau thi
    generator khong chay, `release` khong duoc goi; khoa tu het han thay vi khoa thread vinh vien. Mot event loop,
    khong co `await` giua kiem va ghi -> khong can asyncio.Lock."""

    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl, self.clock = ttl, clock
        self.busy: dict[str, float] = {}
        self.calls = 0

    def acquire(self, thread_id: str) -> bool:
        now = self.clock()
        self.calls += 1
        if self.calls % SWEEP_EVERY == 0:                  # khoa het han cua thread bi bo do
            for k in [k for k, t in self.busy.items() if now - t >= self.ttl]:
                del self.busy[k]
        since = self.busy.get(thread_id)
        if since is not None and now - since < self.ttl:
            return False
        self.busy[thread_id] = now
        return True

    def release(self, thread_id: str) -> None:
        self.busy.pop(thread_id, None)
