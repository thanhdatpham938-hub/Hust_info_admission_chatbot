"""Seam 1 cua PLAN - API (v1): chay mot luot va phat luong su kien (muc 3, 4.2, 5).

Ca /api/chat va /api/chat/stream dung chung ham nay: mot cho duy nhat quyet "stream hay dem", nen hai endpoint
khong the tra hai ket qua khac nhau.

Su kien: {"event": ten, "data": dict}
  status   {"step": routing | searching | writing | checking}   node bat dau mot buoc dai
  token    {"text": ...}         chi luot chi dung van ban (T7): chu LLM vua sinh
  replace  {"reason": ...}       ban dang stream bi loai, sap viet lai -> frontend xoa phan chu da hien
  final    response_of(state)    LUON la su kien cuoi, mang ca cau tra loi chot (khac phan da stream: co bang,
                                 khoi Nguon, da xoa [n] sai) -> frontend thay phan da stream bang final.answer
"""

from collections.abc import AsyncIterator


def response_of(state: dict) -> dict:
    """Phan state tra ra ngoai (PRD 19 + clarification cho nut bam Tuan 5). Khong co `draft` (co cua node `answer`
    tam truoc Synthesizer) va khong lo state noi bo."""
    t = state["turn"]
    return {"answer": t.get("answer", ""), "citations": t.get("citations") or [],
            "clarification": t.get("clarification"),
            "metadata": {"intent": t.get("intent_final"), "language": t.get("language"),
                         "error_code": t.get("error_code"), "fallback_reason": t.get("fallback_reason"),
                         "used_template": bool(t.get("used_template")), "rewrites": t.get("retry", 0)}}


def config_of(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def run_turn(graph, thread_id: str, question: str, choice: str | None = None) -> AsyncIterator[dict]:
    state = None
    async for mode, chunk in graph.astream({"turn": {"question": question, "choice": choice}},
                                           config=config_of(thread_id), stream_mode=["custom", "values"]):
        if mode == "custom":
            yield chunk
        else:
            state = chunk
    yield {"event": "final", "data": response_of(state)}
