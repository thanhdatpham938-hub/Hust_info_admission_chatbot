"""Dau vao / dau ra cua T3 program_info (PLAN - T3 program_info (v1), muc 2 va 3)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source

Section = Literal["overview", "quota", "methods", "combinations"]


class ProgramInfoInput(BaseModel):
    programs: list[str] = Field(description="Cụm người dùng gõ hoặc mã ngành; tối đa 3")
    years: list[int] = Field(default=[], description="Tối đa 3; rỗng = năm mới nhất")
    fields: list[Section] = Field(default=[], description="Chỉ lấy phần cần; rỗng = tất cả (P9)")


class Overview(BaseModel):
    """Thong tin chung theo trang gioi thieu nganh — chi thu tu trang nam 2026 (P2)."""
    language: str | None
    degree: str | None
    duration: str | None
    curriculum_url: str | None
    short_description: str | None
    as_of_year: int
    source: Source


class QuotaItem(BaseModel):
    year: int
    quota: int
    quota_type: str          # hien chi co tong_nganh: khong co chi tieu theo phuong thuc
    source: Source


class MethodItem(BaseModel):
    year: int
    method_code: str         # theo program_methods: XTTN, khong tach 1.1/1.2/1.3 (P12)
    method_name: str
    scale: int | None
    source: Source


class CombinationItem(BaseModel):
    year: int
    method_code: str
    combination_code: str
    subjects: str
    main_subject: str | None
    formula_type: str
    main_subject_known: bool  # False khi formula_type = chua_ro (P4): bot phai noi "chua xac dinh"


class FormulaItem(BaseModel):
    formula_type: str
    method_code: str
    year: int
    scale: int | None
    formula: str | None       # None khi chua_ro
    note: str | None
    source: Source            # bai cong bo diem chuan — nguon chinh thuc cua mon chinh/cong thuc (P3)


class ProgramInfo(BaseModel):
    program_code: str
    program_name: str
    faculty_code: str
    faculty_name: str
    program_group_code: str | None
    program_group_name: str | None
    open_years: list[int]
    overview: Overview | None = None
    quotas: list[QuotaItem] = []
    methods: list[MethodItem] = []
    combinations: list[CombinationItem] = []
    formulas: list[FormulaItem] = []    # moi cong thuc mot lan (P10)


class ProgramInfoData(BaseModel):
    programs: list[ProgramInfo]
    notes: list[str] = []
