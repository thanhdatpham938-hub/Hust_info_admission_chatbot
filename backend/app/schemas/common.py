"""Khuon ket qua chung cua moi tool (PLAN - Entity Resolution + Admission Tool (v1), muc 1.1).

Synthesizer va Clarification Node (Tuan 4) chi doc mot kieu du lieu nay. `status` anh xa thang sang
ma loi PRD muc 24 qua `error_code`.
"""

from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Status(StrEnum):
    OK = "ok"
    PARTIAL = "partial"            # co du lieu nhung thieu mot phan da hoi (xem `missing`)
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"        # phai hoi lai nguoi dung (xem `clarifications`), KHONG co du lieu (K1)
    INVALID = "invalid"            # dau vao sai (qua 3 phan tu, limit qua lon...) -> `message`


class ErrorCode(StrEnum):
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ENTITY_AMBIGUOUS = "ENTITY_AMBIGUOUS"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"


class Source(BaseModel):
    title: str
    url: str
    year: int | None = None
    verification_status: str | None = None


MissingReason = Literal[
    "year_out_of_range",    # nam ngoai pham vi du lieu (vd 2020)
    "program_not_open",     # nganh khong tuyen nam do (EM4, TROY-BA tu 2026)
    "method_no_score",      # phuong thuc khong co diem nam do (tuyen thang; XTTN nam 2024)
    "entity_not_found",     # cum tu khong khop nganh/phuong thuc nao
    "not_collected",        # du lieu chua thu thap (chi tieu theo phuong thuc, so ho so...)
]


class Missing(BaseModel):
    what: str
    reason: MissingReason
    available_years: list[int] = []


class Candidate(BaseModel):
    code: str
    name: str
    entity_type: str


class Clarification(BaseModel):
    mention: str
    candidates: list[Candidate]


class Resolved(BaseModel):
    mention: str
    entity_type: str
    codes: list[str]
    matched_by: Literal["exact", "substring", "fuzzy"]


class ToolResult(BaseModel, Generic[T]):
    status: Status
    error_code: ErrorCode | None = None
    data: T | None = None
    missing: list[Missing] = []
    clarifications: list[Clarification] = []
    resolved: list[Resolved] = []
    sources: list[Source] = []
    message: str | None = None


def dedupe_sources(sources: list[Source]) -> list[Source]:
    """Giu thu tu xuat hien, moi url mot lan."""
    seen, out = set(), []
    for s in sources:
        if s.url and s.url not in seen:
            seen.add(s.url)
            out.append(s)
    return out
