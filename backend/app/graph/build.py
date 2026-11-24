"""Dung StateGraph (PLAN - StateGraph (v1), muc 2).

Moi canh co dieu kien liet ke DU dich: gia tri la lam graph bao loi ngay khi chay test, khong roi vao nhanh sai
mot cach im lang. Checkpointer mac dinh InMemorySaver; Postgres o buoc 4 (PLAN Tuan 4).
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import GraphDeps, make_nodes
from app.graph.state import ChatState

ANSWER_NODES = ("clarification", "announcement", "fallback", "answer")


def _route(s: ChatState) -> str:
    return s["turn"]["route"]


def build_graph(deps: GraphDeps, checkpointer=None):
    n = make_nodes(deps)
    g = StateGraph(ChatState)
    for name, fn in n.items():
        g.add_node(name, fn)

    g.add_edge(START, "start_turn")
    g.add_conditional_edges("start_turn", lambda s: "pick_choice" if s["context"].get("pending") else "router",
                            ["pick_choice", "router"])
    g.add_conditional_edges("pick_choice", _route, ["run_tools", "clarification", "router"])
    g.add_conditional_edges("router", _route, ["merge", "clarification", "fallback"])
    g.add_conditional_edges("merge", _route, ["run_tools", "fallback"])
    g.add_edge("run_tools", "check_status")
    g.add_conditional_edges("check_status", _route, ["clarification", "announcement", "fallback", "answer"])
    for name in ANSWER_NODES:
        g.add_edge(name, "save_context")
    g.add_edge("save_context", END)
    return g.compile(checkpointer=checkpointer if checkpointer is not None else InMemorySaver())


async def chat(graph, thread_id: str, question: str, choice: str | None = None) -> dict:
    """Mot luot hoi. Tra dang gan voi API PRD 19: answer, citations, clarification, metadata."""
    state = await graph.ainvoke({"turn": {"question": question, "choice": choice}},
                                config={"configurable": {"thread_id": thread_id}})
    t = state["turn"]
    return {"answer": t.get("answer", ""), "citations": t.get("citations") or [],
            "clarification": t.get("clarification"),
            "metadata": {"intent": t.get("intent_final"), "language": t.get("language"),
                         "error_code": t.get("error_code"), "draft": bool(t.get("draft")),
                         "fallback_reason": t.get("fallback_reason")},
            "_state": state}                                   # cho test; API se bo truong nay
