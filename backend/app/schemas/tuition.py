"""Dau vao / dau ra cua T4 tuition_fees (PLAN - T4 T5 hoc phi va chung chi (v1), muc A2-A3)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source

Kind = Literal["program", "year_rule", "credit", "fee"]


class TuitionInput(BaseModel):
    programs: list[str] = Field(default=[], description="0–3 ngành (cụm người dùng gõ hoặc mã)")
    program_group: str | None = Field(default=None, description="Cả nhóm: Elitech, chương trình chuẩn, PFIEV...")
    years: list[int] = Field(default=[], description="Năm tuyển sinh / năm học bắt đầu, 0–3; rỗng = mới nhất")
    kinds: list[Kind] = Field(default=[], description="program | year_rule | credit | fee (lệ phí tuyển sinh); "
                                                      "rỗng = program")


class ProgramTuition(BaseModel):
    program_code: str
    program_name: str
    program_group_code: str | None
    year: int
    amount_min: float
    amount_max: float
    unit: str                      # "triệu đồng/năm" | "triệu đồng/học kỳ"
    per: Literal["năm", "học kỳ"]
    terms_per_year: int | None     # chi TROY-IT co (3); KHONG tu quy doi hoc ky -> nam (A5-T1)
    is_approximate: bool
    amount_text: str               # nguyen van trang nganh, giu "~" (A5-T8)
    amount_vnd_min: int            # A5-T11: doi cap tien ra dong
    amount_vnd_max: int
    unit_vnd: str
    source: Source


class TuitionRule(BaseModel):
    rule_id: str
    rule_type: Literal["nam", "tin_chi"]
    year: int
    academic_year: str
    group_text: str
    course_type: str | None
    cohort: str | None
    applies_to_all: bool
    amount_min: float
    amount_max: float
    unit: str
    amount_vnd_min: int
    amount_vnd_max: int
    unit_vnd: str
    program_codes: list[str]       # nganh (trong pham vi hoi) ap dung muc nay
    note: str | None
    source: Source


class AdmissionFee(BaseModel):
    """Le phi tuyen sinh: phi thu tuc khi dang ky thi / xet tuyen, KHONG phai hoc phi (A5-T12)."""
    fee_type: str
    year: int
    amount: int
    unit: str
    note: str | None
    source: Source


class UnitStat(BaseModel):
    """Hoi theo nhom: moi DON VI mot dong, khong gop /nam voi /hoc ky (A5-T2)."""
    unit: str
    count: int
    min: float
    max: float
    program_codes: list[str]


class TuitionData(BaseModel):
    programs: list[ProgramTuition] = []
    year_rules: list[TuitionRule] = []
    credit_rules: list[TuitionRule] = []
    fees: list[AdmissionFee] = []
    stats: list[UnitStat] = []
    notes: list[str] = []
