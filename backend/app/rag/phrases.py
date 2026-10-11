"""Cum tu chuyen nganh + tu dien cach goi tuong duong cho nhanh loc chu (PLAN - T7 retrieval (v2), R3).

Nhanh nay chi CONG PHIEU trong RRF, khong loai chunk nao — cum tu khong co trong tai lieu cung khong lam mat
ket qua. Mo rong danh sach khi do (scripts/eval_retrieval.py) cho thay cau truot vi khac cach goi.
"""

import re
from dataclasses import dataclass

from app.entity_resolution.normalize import normalize

# Cum tu xuat hien NGUYEN VAN trong van ban (giu dau: chi muc full-text cua Qdrant khong bo dau).
# KHONG co "hệ số" don le: chu nay co trong quy dinh XTTN (he so quy doi chung chi) va lam Q10 lech tai lieu.
PHRASES = [
    "môn chính", "điểm sàn", "điểm ưu tiên", "điểm thưởng", "cảnh báo học tập", "buộc thôi học",
    "học bổng", "học kỳ hè", "học lại", "bảo lưu", "chuẩn đầu ra", "ngưỡng đảm bảo", "lệ phí",
    "điểm rèn luyện", "học cải thiện", "song bằng", "chuyển ngành", "tốt nghiệp sớm", "ký túc xá",
]
# Cach nguoi dung noi -> cach van ban viet (R3). Khoa so khop tren chuoi da chuan hoa (khong dau).
SYNONYMS = {
    "học bạ": ["TBC", "điểm trung bình chung"],
    "điểm cộng": ["điểm thưởng"],
    "rớt môn": ["học lại"],
    "trượt môn": ["học lại"],
    "đình chỉ": ["buộc thôi học"],
    "đuổi học": ["buộc thôi học"],
    "hệ số 2": ["môn chính"],
    "kí túc xá": ["ký túc xá"],
}
CODE_RE = re.compile(r"\b(?:[A-D]\d{2}|K0\d|DD2)\b")
DIEU_RE = re.compile(r"\bđiều\s+(\d{1,2})\b", re.IGNORECASE)


@dataclass(frozen=True)
class Phrase:
    shown: str      # cum tu de bao lai (phrases_used)
    match: str      # chuoi dua vao MatchText (giu dau, viet nhu van ban)


def extract_phrases(query: str) -> list[Phrase]:
    """Tim cum tu chuyen nganh trong cau hoi: so tren chuoi da chuan hoa, nguyen tu."""
    q = f" {normalize(query)} "
    out: list[Phrase] = []
    for p in PHRASES:
        if f" {normalize(p)} " in q:
            out.append(Phrase(p, p))
    for said, written in SYNONYMS.items():
        if f" {normalize(said)} " in q:
            out += [Phrase(w, w) for w in written]
    out += [Phrase(m, m) for m in dict.fromkeys(CODE_RE.findall(query))]
    out += [Phrase(f"Điều {m}", f"Điều {m}") for m in dict.fromkeys(DIEU_RE.findall(query))]
    seen, uniq = set(), []
    for p in out:
        if p.match not in seen:
            seen.add(p.match)
            uniq.append(p)
    return uniq
