"""Khuon vao/ra cua API (PLAN - API (v1) muc 4; PRD 19).

Bot tu choi / hoi lai / loi DB-LLM van la HTTP 200: loi nam o metadata.error_code, `answer` la cau mau (graph da xu
ly theo PRD 24). Ma HTTP khac 200 chi cho loi NGOAI graph (body sai, qua tan suat, thread dang ban, loi he thong).
"""

from uuid import UUID

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 4000       # chan body khong lo; cau > 1.000 ky tu da co prefilter tra cau mau `too_long`
MAX_CHOICE_CHARS = 64


class ChatRequest(BaseModel):
    # Frontend tao UUID va luu localStorage; thieu thi server tao ho (goi thu bang curl). Chi nhan UUID: chuoi tu do
    # de doan, nguoi khac co the doc tiep hoi thoai (Q3)
    thread_id: UUID | None = None
    message: str = Field(max_length=MAX_MESSAGE_CHARS)
    choice: str | None = Field(default=None, max_length=MAX_CHOICE_CHARS)   # ma lua chon khi bam nut


class Citation(BaseModel):
    n: int | None = None       # so [n] trong cau tra loi; None: kenh cua node announcement (khong danh so)
    title: str
    url: str
    location: str | None = None


class Choice(BaseModel):
    code: str
    name: str


class Clarification(BaseModel):
    mention: str
    choices: list[Choice]


class Metadata(BaseModel):
    intent: str | None
    language: str | None
    error_code: str | None
    fallback_reason: str | None
    used_template: bool
    rewrites: int


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    citations: list[Citation]
    clarification: Clarification | None
    metadata: Metadata


class ErrorBody(BaseModel):
    error_code: str            # INVALID_REQUEST | THREAD_BUSY | RATE_LIMITED | INTERNAL_ERROR
    message: str
    answer: str | None = None  # INTERNAL_ERROR: cau xin loi song ngu de frontend hien thang
