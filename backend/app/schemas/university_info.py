"""Dau vao / dau ra cua T6 university_info (PLAN - T6 university_info (v1), muc 3-4)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Source

Section = Literal["contact", "channel", "units", "programs"]


class UniversityInfoInput(BaseModel):
    faculties: list[str] = Field(default=[], description="0–3 Trường/Khoa: tên, mã, tên cũ")
    programs: list[str] = Field(default=[], description="0–3 ngành -> Trường/Khoa quản lý")
    fields: list[Section] = Field(default=[], description="contact | channel | units | programs; rỗng = tất cả")
    year: int | None = Field(default=None, description="Năm của danh sách ngành; rỗng = năm mới nhất")


class Contact(BaseModel):
    phones: list[str]          # U2: tach theo ";", giu du so va chu thich trong ngoac
    email: str | None
    address: str | None
    source: Source


class Unit(BaseModel):
    unit_name: str
    unit_type: str
    unit_type_label: str       # U10


class ProgramRef(BaseModel):
    program_code: str
    program_name: str
    program_group_code: str | None


class FacultyInfo(BaseModel):
    faculty_code: str
    faculty_name: str
    former_names: list[str] = []            # U6: alias old_name
    official_channel_url: str | None = None  # U3, AC9
    contact: Contact | None = None
    units: list[Unit] = []
    programs_year: int | None = None
    programs: list[ProgramRef] = []
    asked_programs: list[str] = []          # nganh nguoi dung hoi ma thuoc Truong/Khoa nay


class UniversityInfoData(BaseModel):
    faculties: list[FacultyInfo]
    notes: list[str] = []
