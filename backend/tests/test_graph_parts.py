"""Cau mau va dispatch (PLAN - StateGraph (v1), G1-G2). Khong mang, khong DB: tool gia."""

import asyncio
import time

import openai
import psycopg
import pytest
from pydantic import BaseModel

from app.graph import templates as T
from app.graph.dispatch import TOOLS, run_calls
from app.graph.state import MAX_CHARS, append_message


# ---------------------------------------------------------------- templates
def test_moi_cau_mau_du_hai_ngon_ngu():
    for code, t in T.TEMPLATES.items():
        assert set(t) == {"vi", "en"} and t["vi"] and t["en"], code


def test_ngon_ngu_khac_in_ca_hai_ban():
    text = T.render("other_language", "other")
    assert T.TEMPLATES["other_language"]["vi"] in text and T.TEMPLATES["other_language"]["en"] in text


def test_cau_cancel_nguoi_dung_sua():
    assert T.render("cancel", "vi") == "Bạn còn cần giải đáp thắc mắc nào nữa không?"
    assert "Đã bỏ" not in T.render("cancel", "vi")


def test_danh_sach_lua_chon_tu_candidates():
    cands = [{"code": "TE1", "name": "Kỹ thuật Ô tô"}, {"code": "TE-E2", "name": "Kỹ thuật Ô tô (CT tiên tiến)"}]
    text = T.render("ambiguous", "vi", mention="kỹ thuật ô tô", kind=T.kind_name("program", "vi"),
                    choices=T.choices_block(cands))
    assert "1. TE1 – Kỹ thuật Ô tô" in text and "2. TE-E2 – Kỹ thuật Ô tô (CT tiên tiến)" in text
    assert "các ngành sau" in text


def test_thieu_gi_co_gi():
    res = [{"missing": [{"what": "chỉ tiêu năm 2024", "reason": "year_out_of_range", "available_years": [2026, 2025]}]}]
    what, avail = T.missing_parts(res, "vi")
    assert what == "chỉ tiêu năm 2024" and avail == " Hiện có dữ liệu năm 2025, 2026."
    assert T.missing_parts(res, "en")[1] == " Data is available for 2025, 2026."


def test_cat_lich_su():
    msgs = append_message([], "assistant", "x" * 2000)
    assert len(msgs[0]["content"]) == MAX_CHARS["assistant"] + 1          # + dau "…"
    assert append_message([], "user", "ngắn")[0]["content"] == "ngắn"


# ---------------------------------------------------------------- dispatch
class Out(BaseModel):
    status: str = "ok"
    value: int = 0

    def model_dump(self, **kw):                                         # giong ToolResult.model_dump(mode="json")
        return super().model_dump()


class In(BaseModel):
    x: int


def fake_tools(**fns):
    return {name: (fn, In) for name, fn in fns.items()}


async def slow(inp, ctx):
    await asyncio.sleep(0.2)
    return Out(value=inp.x)


async def test_chay_song_song():
    t = time.perf_counter()
    res = await run_calls([{"tool": "a", "args": {"x": 1}}, {"tool": "a", "args": {"x": 2}}], tools=fake_tools(a=slow))
    assert [r["value"] for r in res] == [1, 2]
    assert time.perf_counter() - t < 0.35                               # tuan tu se mat >= 0.4 s


async def test_dung_lai_done_khong_goi_tool():
    called = []

    async def tool(inp, ctx):
        called.append(inp.x)
        return Out()
    res = await run_calls([{"tool": "a", "args": {"x": 1}, "done": {"status": "ok", "value": 9}}],
                          tools=fake_tools(a=tool))
    assert res == [{"status": "ok", "value": 9}] and called == []


@pytest.mark.parametrize("exc,code", [(psycopg.OperationalError("db"), "DATABASE_ERROR"),
                                      (openai.OpenAIError("oa"), "LLM_ERROR"),
                                      (RuntimeError("x"), "INTERNAL_ERROR")])
async def test_loi_thanh_ma_prd24(exc, code):
    async def boom(inp, ctx):
        raise exc
    res = await run_calls([{"tool": "a", "args": {"x": 1}}], tools=fake_tools(a=boom))
    assert res[0]["status"] == "error" and res[0]["error_code"] == code


async def test_qua_thoi_gian():
    res = await run_calls([{"tool": "a", "args": {"x": 1}}], tools=fake_tools(a=slow), timeout=0.05)
    assert res[0]["error_code"] == "INTERNAL_ERROR"


async def test_tham_so_sai_va_tool_la():
    res = await run_calls([{"tool": "a", "args": {"x": "khong phai so"}}, {"tool": "zzz", "args": {}}],
                          tools=fake_tools(a=slow))
    assert [r["status"] for r in res] == ["invalid", "invalid"]
    assert all(r["error_code"] == "INVALID_REQUEST" for r in res)


def test_bang_tool_du_7():
    assert set(TOOLS) == {"admission_scores", "list_programs", "program_info", "tuition_fees", "certificate_lookup",
                          "university_info", "rag_search"}
