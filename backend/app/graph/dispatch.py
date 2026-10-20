"""Chay lenh goi tool (PLAN - StateGraph (v1), muc 5).

- Song song (asyncio.gather): 2-3 tool chay tuan tu se cong don do tre.
- Lenh co `done` (pending giu lai, PLAN State 2(3)) -> tra lai `done`, khong goi tool: tranh chay lai T7 ton embedding.
- Kiem tham so bang *Input truoc khi goi: merge_context / merge_pick sinh dict, sai thi thanh INVALID_REQUEST ro rang.
- Moi tool cho toi da TOOL_TIMEOUT_S; loi -> ma PRD 24, ghi log day du, nguoi dung chi thay cau xin loi.
- Bang tool truyen vao duoc: test dung tool gia, khong can DB.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import openai
import psycopg
from pydantic import BaseModel, ValidationError

from app.schemas.admission import AdmissionScoresInput, ListProgramsInput
from app.schemas.certificate import CertificateInput
from app.schemas.program_info import ProgramInfoInput
from app.schemas.rag import RagSearchInput
from app.schemas.tuition import TuitionInput
from app.schemas.university_info import UniversityInfoInput
from app.tools.admission import admission_scores, list_programs
from app.tools.certificate import certificate_lookup
from app.tools.program_info import program_info
from app.tools.rag_tool import rag_search
from app.tools.tuition import tuition_fees
from app.tools.university_info import university_info

log = logging.getLogger(__name__)

TOOL_TIMEOUT_S = 10.0         # nguoi dung chot 2026-10-19; chua co so do thoi gian tool, buoc 8 se chinh

ToolFn = Callable[..., Awaitable[BaseModel]]
TOOLS: dict[str, tuple[ToolFn, type[BaseModel]]] = {
    "admission_scores": (admission_scores, AdmissionScoresInput),
    "list_programs": (list_programs, ListProgramsInput),
    "program_info": (program_info, ProgramInfoInput),
    "tuition_fees": (tuition_fees, TuitionInput),
    "certificate_lookup": (certificate_lookup, CertificateInput),
    "university_info": (university_info, UniversityInfoInput),
    "rag_search": (rag_search, RagSearchInput),
}


def error_result(code: str, message: str | None = None) -> dict:
    """Ket qua loi he thong. Dict (khong doi ToolResult) de khong sua schema 7 tool da co test."""
    return {"status": "error", "error_code": code, "message": message, "data": None, "missing": [],
            "clarifications": [], "resolved": [], "sources": []}


def invalid_result(message: str) -> dict:
    return {**error_result("INVALID_REQUEST", message), "status": "invalid"}


async def run_one(call: dict, ctx, tools: dict, timeout: float) -> dict:
    if call.get("done") is not None:
        return call["done"]
    if call["tool"] not in tools:
        return invalid_result(f"Tool không tồn tại: {call['tool']}")
    fn, model = tools[call["tool"]]
    try:
        inp = model.model_validate(call["args"])
    except ValidationError as e:
        log.warning("Tham so sai cho %s: %s", call["tool"], e)
        return invalid_result("Tham số không hợp lệ.")
    try:
        result = await asyncio.wait_for(fn(inp, ctx), timeout)
    except psycopg.Error:
        log.exception("Loi DB o tool %s", call["tool"])
        return error_result("DATABASE_ERROR")
    except openai.OpenAIError:
        log.exception("Loi OpenAI o tool %s", call["tool"])          # T7: embedding cau hoi
        return error_result("LLM_ERROR")
    except TimeoutError:
        log.error("Tool %s qua %.0f s", call["tool"], timeout)
        return error_result("INTERNAL_ERROR")
    except Exception:                                                  # noqa: BLE001 — khong de sap ca luot
        log.exception("Loi khac o tool %s", call["tool"])
        return error_result("INTERNAL_ERROR")
    return result.model_dump(mode="json")


async def run_calls(calls: list[dict], ctx=None, tools: dict | None = None,
                    timeout: float = TOOL_TIMEOUT_S) -> list[dict]:
    """Moi lenh goi mot ket qua dict, cung thu tu `calls`."""
    tools = tools if tools is not None else TOOLS
    return list(await asyncio.gather(*(run_one(c, ctx, tools, timeout) for c in calls)))
