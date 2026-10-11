"""Dau vao / dau ra cua T7 rag_search (PLAN - T7 retrieval (v2), muc 2.1)."""

from pydantic import BaseModel, Field

from app.schemas.common import Source


class RagSearchInput(BaseModel):
    query: str = Field(description="Câu hỏi cần tìm văn bản")
    programs: list[str] = Field(default=[], description="0–3 ngành; mơ hồ -> hỏi lại (R7)")
    faculties: list[str] = Field(default=[], description="0–3 Trường/Khoa")
    years: list[int] = Field(default=[], description="Nêu năm -> tài liệu nhiều năm chỉ lấy đúng năm đó")
    cohort: str | None = Field(default=None, description="Khoá: K71, K70, 'khoá 2026'...")
    document_types: list[str] = Field(default=[], description="Tuỳ chọn: so_tay_sinh_vien, quy_che_dao_tao...")
    top_k: int = Field(default=5, description="1–10")


class RetrievedChunk(BaseModel):
    rank: int
    chunk_id: str
    document_title: str
    document_type: str
    document_no: str | None
    year: int
    heading: str
    chuong: str | None
    dieu_no: str | None
    khoan_no: str | None
    muc_no: str | None
    page_no: str | None              # co the la khoang trang, vd "4-5"
    source_url: str
    verification_status: str
    cohort: str | None
    program_code: str | None
    faculty_code: str | None
    is_latest: bool
    versioned: bool
    dense_score: float               # cosine; dung cho nguong, KHONG dung diem RRF (R6)
    text: str
    citation: Source                 # dung san tu metadata (R4, PRD 12)


class RagSearchData(BaseModel):
    chunks: list[RetrievedChunk]
    top_dense_score: float
    low_confidence: bool
    phrases_used: list[str] = []
    cohorts_found: list[str] = []
    notes: list[str] = []
