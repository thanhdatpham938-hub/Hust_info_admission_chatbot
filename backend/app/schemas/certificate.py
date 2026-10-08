"""Dau vao / dau ra cua T5 certificate_lookup (PLAN - T4 T5 hoc phi va chung chi (v1), muc B2-B3)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source

Purpose = Literal["xet_tuyen", "chuan_dau_ra", "khung_cefr"]


class CertificateInput(BaseModel):
    certificate: str = Field(description="Tên chứng chỉ: IELTS, TOEIC, TOEFL iBT, JLPT...")
    value: str | None = Field(default=None, description="Mức/điểm: 6.5, 300, N3, B2; bỏ trống = cả bảng")
    purpose: Purpose | None = Field(default=None, description="xet_tuyen | chuan_dau_ra | khung_cefr; "
                                                              "bỏ trống -> hỏi lại (B5-T1)")
    year: int | None = Field(default=None, description="Xét tuyển: năm tuyển sinh; rỗng = mới nhất")
    programs: list[str] = Field(default=[], description="Chuẩn đầu ra: 0–3 ngành")
    cohort: str | None = Field(default=None, description="Chuẩn đầu ra: K71, K70, 'khoá 2026'...")


class CertConversion(BaseModel):
    cert_code: str
    cert_name: str
    cert_value: str
    year: int
    table: str                         # ca_hai | quy_doi | diem_thuong
    bonus_point: int | None            # diem thuong (cong vao diem xet DGTD)
    converted_score_10: float | None   # diem quy doi mon tieng Anh, thang 10
    note: str | None
    source: Source


class ExitLevel(BaseModel):
    cert_code: str
    cert_name: str
    cert_value: str
    level: str
    level_group: str
    note: str | None
    source: Source


class ExitRequirement(BaseModel):
    req_id: str
    cohort: str | None
    group_text: str
    main_language: str | None
    degree_level: str | None
    requirement: str
    min_level_group: str | None
    note: str | None
    program_codes: list[str]
    meets: bool | None                 # B5-T5: chi tinh cho yeu cau don gian "tu Bac N tro len"
    source: Source


class CefrLevel(BaseModel):
    cert_code: str
    cert_name: str
    cert_value: str
    cefr_level: str | None
    knlnn_level: str | None
    source: Source


class CertificateData(BaseModel):
    cert_codes: list[str]
    matched: bool | None = None        # None khi khong neu value; False -> tra ca bang (B5-T8)
    conversions: list[CertConversion] = []
    exit_levels: list[ExitLevel] = []
    requirements: list[ExitRequirement] = []
    cefr: list[CefrLevel] = []
    notes: list[str] = []
