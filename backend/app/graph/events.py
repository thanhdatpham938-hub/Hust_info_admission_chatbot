"""Su kien giua chung cua mot luot (PLAN - API (v1), muc 4.2 va 5).

Node goi emit() de bao tien do (`status`) hoac stream chu (`token`, `replace`). run_turn() nhan qua
stream_mode="custom" cua LangGraph. Dung writer cua LangGraph (khong dung stream_mode="messages") vi du an goi
thang SDK `openai`, LangGraph khong tu bat duoc token.

Goi bang ainvoke (khong stream) thi writer khong lam gi. Goi node truc tiep ngoai graph (test tung node) thi
LangGraph bao RuntimeError: bo qua, node van chay nhu cu.
"""

from langgraph.config import get_stream_writer


def emit(event: str, data: dict) -> None:
    try:
        writer = get_stream_writer()
    except RuntimeError:                                   # ngoai graph
        return
    writer({"event": event, "data": data})
