"""Client OpenAI cho Router va Synthesizer (PLAN - Router (v1), muc 4).

Goi thang SDK `openai` (PLAN Tuan 4 Q2 = A), khong qua langchain. Retriever T7 co client rieng cho embedding.
SDK khong tu thu lai (max_retries=0): Router tu thu lai DUNG 1 lan de nam trong ngan sach TTFT (PRD 22.1).
"""

from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings

LLM_TIMEOUT_S = 20.0


class LLMNotConfigured(RuntimeError):
    pass


@lru_cache
def get_llm() -> AsyncOpenAI:
    s = get_settings()
    if s.openai_api_key is None:
        raise LLMNotConfigured("Thiếu OPENAI_API_KEY trong .env")
    return AsyncOpenAI(api_key=s.openai_api_key.get_secret_value(), timeout=LLM_TIMEOUT_S, max_retries=0)
