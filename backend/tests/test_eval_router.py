"""scripts/eval_router.py (PLAN - Toi uu Router (v1), buoc B): cache ket qua LLM va --only-failed.
Client OpenAI gia: khong goi API, khong ton tien."""

from types import SimpleNamespace

import eval_router
from app.graph.router import RouterLLMOutput

ANSWER = RouterLLMOutput(language="vi", need="Điểm chuẩn IT1", topic="tuyen_sinh", calls=[], refers_to_context=False,
                         scope_note=None, missing_info=None, pick_status=None, picked=[])


class FakeOpenAI:
    """Dem so lan goi that."""

    def __init__(self):
        self.n = 0
        self.chat = SimpleNamespace(completions=self)

    async def parse(self, **kw):
        self.n += 1
        msg = SimpleNamespace(parsed=ANSWER, content=ANSWER.model_dump_json(), refusal=None)
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=10,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=80))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


def kw(question="Điểm IT1?"):
    return {"model": "gpt-4o-mini", "temperature": 0.0, "max_tokens": 800, "response_format": RouterLLMOutput,
            "messages": [{"role": "system", "content": "prompt"}, {"role": "user", "content": question}]}


async def test_goi_lai_y_het_thi_lay_cache():
    inner = FakeOpenAI()
    client = eval_router.UsageClient(inner)
    await client.chat.completions.parse(**kw())
    r = await client.chat.completions.parse(**kw())
    assert inner.n == 1
    assert r.choices[0].message.parsed == ANSWER and r.choices[0].message.refusal is None
    assert [u["from_cache"] for u in client.log] == [False, True]


async def test_doi_prompt_thi_khong_dung_cache_cu():
    inner = FakeOpenAI()
    client = eval_router.UsageClient(inner)
    await client.chat.completions.parse(**kw())
    changed = kw()
    changed["messages"][0]["content"] = "prompt đã gọt"
    await client.chat.completions.parse(**changed)
    assert inner.n == 2


async def test_no_cache_van_goi_that_va_ghi_de_cache():
    inner = FakeOpenAI()
    cache: dict = {}
    await eval_router.UsageClient(inner, cache).chat.completions.parse(**kw())
    await eval_router.UsageClient(inner, cache, read_cache=False).chat.completions.parse(**kw())
    assert inner.n == 2 and len(cache) == 1


async def test_cache_luu_file_lan_chay_sau_khong_goi_api(tmp_path):
    path = tmp_path / "cache" / "eval_router.json"
    inner = FakeOpenAI()
    first = eval_router.UsageClient(inner, eval_router.load_cache(path))
    await first.chat.completions.parse(**kw())
    eval_router.save_cache(path, first.cache)
    second = eval_router.UsageClient(inner, eval_router.load_cache(path))
    r = await second.chat.completions.parse(**kw())
    assert inner.n == 1 and r.choices[0].message.parsed == ANSWER


def test_chua_co_file_cache_thi_rong(tmp_path):
    assert eval_router.load_cache(tmp_path / "khong_co.json") == {}


def case(id_, intent="ADMISSION_QUERY", required="admission_scores", optional=""):
    return {"id": id_, "expected_intent": intent, "required_tools": required, "optional_tools": optional}


def test_only_failed_chon_ca_sai_intent_sai_tool_loi_va_sai_pick():
    cases = [case("R1"), case("R2"), case("R3"), case("R4")]
    picks = [{"id": "P1", "expected_pick_status": "picked"}, {"id": "P2", "expected_pick_status": "unclear"}]
    T1 = {"tool": "admission_scores", "args": {}}
    prev = [{"id": "R1", "intent": "ADMISSION_QUERY", "calls": [T1]},                      # dung
            {"id": "R2", "intent": "REGULATION_QUERY", "calls": [T1]},                     # sai intent
            {"id": "R3", "intent": "ADMISSION_QUERY", "calls": []},                        # sai tool
            {"id": "R4", "error": "timeout"},                                              # loi LLM
            {"id": "P1", "pick_status": "picked", "calls": []},                            # dung
            {"id": "P2", "pick_status": "picked", "calls": []}]                            # sai pick
    assert eval_router.failed_ids(prev, cases, picks) == {"R2", "R3", "R4", "P2"}
