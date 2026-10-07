"""Dau vao / dau ra cua Admission Tool: T1 admission_scores, T2 list_programs
(PLAN - Entity Resolution + Admission Tool (v1), muc 3.1 va 4.1)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source


# ---------------------------------------------------------------- dung chung
class Delta(BaseModel):
    """Chenh lech do TOOL tinh (PRD 10.2: khong de LLM tu tinh). diff = value_b - value_a."""
    kind: Literal["year", "program", "total"]   # cung nganh qua cac nam / giua cac nganh / tong chi tieu
    program_code: str | None = None             # kind=year: nganh dang so
    method_code: str | None = None
    combination_group: str | None = None
    a: str
    b: str
    value_a: float
    value_b: float
    diff: float


# ---------------------------------------------------------------- T1
class AdmissionScoresInput(BaseModel):
    programs: list[str] = Field(description="Cụm người dùng gõ hoặc mã ngành; tối đa 3")
    years: list[int] = Field(default=[], description="Tối đa 3; rỗng = năm mới nhất có điểm chuẩn")
    methods: list[str] = Field(default=[], description="Tối đa 3; rỗng = mọi phương thức")


class ScoreRow(BaseModel):
    program_code: str
    program_name: str
    year: int
    method_code: str
    method_name: str
    combination_group: str
    combination_group_label: str
    subject_combinations: list[str]
    score: float
    scale: int | None
    score_note: str | None
    is_rule_derived: bool        # A3: 27 dong tinh theo quy tac +0,5, khong co tren bang cong bo
    source: Source


class AdmissionScoresData(BaseModel):
    rows: list[ScoreRow]
    deltas: list[Delta]


# ---------------------------------------------------------------- T2
class ListProgramsInput(BaseModel):
    metric: Literal["score", "quota"]
    years: list[int] = Field(default=[], description="Tối đa 3; rỗng = năm mới nhất của bảng tương ứng")
    method: str | None = Field(default=None, description="metric=score; bỏ trống = xếp riêng từng phương thức")
    faculty: str | None = Field(default=None, description="Tên/mã Trường-Khoa")
    program_group: str | None = Field(default=None, description="Nhóm ngành: Elitech, PFIEV, chương trình chuẩn...")
    programs: list[str] = Field(default=[], description="Cụm tên ngành; không giới hạn 3")
    combination: str | None = Field(default=None, description="Mã tổ hợp, vd D01")
    without_method: str | None = Field(default=None, description="Chỉ lấy ngành KHÔNG xét phương thức này")
    score_min: float | None = None
    score_max: float | None = None
    order: Literal["desc", "asc"] = "desc"
    limit: int | None = Field(default=10, description="Số dòng mỗi (năm, phương thức); None = cả bảng; tối đa 100")


class ListRow(BaseModel):
    rank: int
    program_code: str
    program_name: str
    faculty_code: str
    faculty_name: str
    program_group_code: str | None
    year: int
    method_code: str | None = None
    combination_group: str | None = None
    combination_group_label: str | None = None
    value: float
    scale: int | None = None
    is_rule_derived: bool = False
    source: Source


class GroupStat(BaseModel):
    """Moi (nam, phuong thuc) voi diem; moi nam voi chi tieu. Tinh tren TOAN BO dong khop loc (truoc limit)."""
    year: int
    method_code: str | None = None
    count: int
    min: float
    max: float
    total: float | None = None      # chi cho chi tieu


class ListProgramsData(BaseModel):
    rows: list[ListRow]
    stats: list[GroupStat]
    deltas: list[Delta]
    total_rows: int
    truncated: bool
    notes: list[str] = []
