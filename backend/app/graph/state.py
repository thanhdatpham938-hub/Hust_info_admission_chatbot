"""State cua LangGraph (PLAN - State va Context Rules (v1), muc 2; sodothietke.md muc 4).

Chi dung dict thuan (TypedDict), khong luu doi tuong Pydantic: checkpointer tuan tu hoa dict chac chan nhat,
doi ten truong model sau nay khong lam hong hoi thoai da luu.

Ba phan:
  context  giu qua cac luot, CHI chua ma da xac nhan (PRD 14)
  turn     chi song mot luot; start_turn ghi de bang dict moi
  messages 3 luot gan nhat cho Router
"""

from typing import Literal, NotRequired, TypedDict

MAX_HISTORY_TURNS = 3          # plan Tuan 4 Q8: 3 luot gan nhat, khong tom tat bang LLM
MAX_UNCLEAR = 2                # 4.3c: Router xep `unclear` lien tiep den muc nay thi tha pending
MAX_CHARS = {"assistant": 500, "user": 1000}   # cat tin nhan khi luu lich su (PLAN StateGraph 8)

PickStatus = Literal["picked", "new_question", "cancel", "unclear"]


class ToolCall(TypedDict):
    tool: str                  # ten ham tool: admission_scores, rag_search...
    args: dict                 # dung schema *Input cua tool
    done: NotRequired[dict | None]   # ToolResult.model_dump() da co (pending giu lai, 4.3b xung dot 4)


class Pending(TypedDict):
    """Cau hoi lai dang cho nguoi dung chon (muc 2 (3)). Moi luot chi mot cum mo ho."""
    calls: list[ToolCall]      # TOAN BO lenh goi cua luot da hoi lai; lenh nao xong thi co `done`
    index: int                 # lenh goi nao trong `calls` da hoi lai
    mention: str               # cum gay mo ho: "kỹ thuật ô tô", hoac cum T5 tu dat ("khoá học")
    field: str                 # tham so can thay: programs | faculties | methods | certificate | cohort | purpose
    entity_type: str           # program | faculty | method | certificate | cohort | purpose
    candidates: list[dict]     # {"code", "name"}
    retries: int               # so lan LIEN TIEP Router xep `unclear` (4.3c)
    intent: NotRequired[str]   # intent cua cau hoi goc: duong tat pick_choice khong goi Router van biet intent


class ConvContext(TypedDict, total=False):
    programs: list[str]        # ma DA xac nhan, toi da 3
    years: list[int]
    methods: list[str]
    faculties: list[str]
    cohort: str | None
    last_tool: str | None      # tool dau tien cua luot da tra loi gan nhat (C2/C3 so theo tool)
    last_intent: str | None
    last_language: str         # ngon ngu luot truoc: duong tat pick_choice khong goi Router (PLAN StateGraph 9)
    pending: Pending | None


class Turn(TypedDict, total=False):
    question: str
    choice: str | None         # ma lua chon nut bam gui len (4.3 buoc 0)
    router: dict               # RouterOutput.model_dump()
    calls: list[ToolCall]      # lenh goi sau khi ghep ngu canh
    results: list[dict]        # ToolResult.model_dump() theo thu tu calls
    route: str                 # node ke tiep do node hien tai chon (dieu kien cua canh)
    language: str              # vi | en | other
    intent: str                # intent cua luot (Router, hoac intent cau hoi goc o duong tat)
    outcome: str               # answered | clarify | refused | cancel | released -> save_context (PLAN StateGraph 3)
    clarification: dict | None # {"mention", "choices": [{"code", "name"}]} cho nut bam Tuan 5
    pending_new: Pending | None
    error_code: str | None
    draft: bool                # True: cau tra loi la ban nhap tu du lieu tho (chua co Synthesizer)
    intent_final: str
    fallback_reason: str | None
    answer: str
    citations: list[dict]
    retry: int
    verify_issues: list[str]
    trace_id: str | None


class ChatState(TypedDict):
    messages: list[dict]       # {"role", "content"}
    context: ConvContext
    turn: Turn


def empty_context() -> ConvContext:
    return ConvContext(programs=[], years=[], methods=[], faculties=[], cohort=None,
                       last_tool=None, last_intent=None, last_language="vi", pending=None)


def empty_state() -> ChatState:
    return ChatState(messages=[], context=empty_context(), turn=Turn())


def new_turn(question: str, choice: str | None = None) -> Turn:
    """start_turn: dict MOI moi luot, khong ke thua answer/retry/ket qua tool cua luot truoc
    (sodothietke.md muc 6: ban dau de retry cu lam luot sau truot verify vao thang review)."""
    return Turn(question=question, choice=choice, retry=0, verify_issues=[])


def append_message(messages: list[dict], role: str, content: str) -> list[dict]:
    """Them tin nhan, cat con MAX_HISTORY_TURNS luot (moi luot = 1 user + 1 assistant).

    Moi tin nhan cat con MAX_CHARS[role] ky tu (PLAN StateGraph 8, nguoi dung chot 2026-10-19): Router chi can biet
    luot truoc noi chu de gi; bang diem dai lam phinh prompt. Ban day du van nam trong turn.answer tra cho API."""
    limit = MAX_CHARS.get(role)
    if limit and len(content) > limit:
        content = content[:limit] + "…"
    return (messages + [{"role": role, "content": content}])[-2 * MAX_HISTORY_TURNS:]
