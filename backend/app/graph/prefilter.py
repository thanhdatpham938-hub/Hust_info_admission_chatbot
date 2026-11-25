"""Cong truoc Router (PLAN - Toi uu Router (v1), buoc A): cau code tu xu ly tat dinh thi KHONG goi LLM.

Chi chan mau ma code da tu quyet (truoc day LLM van bi goi roi ket qua bi ghi de) hoac khong can hieu ngon ngu.
Cau lac de thong thuong, truong khac, chu de: van do Router (LLM) lam.
"""

from app.graph.router import is_deictic_only, looks_like_injection
from app.graph.state import ConvContext

MAX_QUESTION_CHARS = 1000      # Q1 (nguoi dung chot 2026-11-25)
# Intent cua luot bi chan, giong intent Router tra cho cung loai cau (graph va scripts/eval_router.py dung chung)
GATE_INTENT = {"off_topic": "GENERAL_OFF_TOPIC", "unclear": "CLARIFICATION_NEEDED"}      # con lai: UNKNOWN


def prefilter(question: str, ctx: ConvContext) -> str | None:
    """None = cho qua Router. Chuoi = ly do chan (fallback_reason / "unclear")."""
    q = question.strip()
    if not q:
        return "empty_input"
    if len(q) > MAX_QUESTION_CHARS:
        return "too_long"
    if looks_like_injection(q):
        return "off_topic"
    if ctx.get("pending") and is_deictic_only(q):
        return "unclear"
    return None
