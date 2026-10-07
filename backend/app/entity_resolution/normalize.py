"""Chuan hoa chuoi cho tra cuu thuc the (PRD 10.3, buoc Text Normalization).

Ban duy nhat cua ham nay: scripts/validate_aliases.py import tu day (PLAN ... muc 2.6).
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """Bo dau, ve chu thuong, gop khoang trang: "Khoa  học Máy tính" -> "khoa hoc may tinh"."""
    # "đ" khong phai to hop dau nen NFD khong tach; khong doi sang "d" truoc thi
    # buoc loc [^a-z0-9] se XOA han: "diem" -> "iem", "dang ky" -> "ang ky".
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def compact(text: str) -> str:
    """Dang bo het dau cach, dung cho MA: "IT-E10" / "it e10" / "ITE10" -> "ite10"."""
    return normalize(text).replace(" ", "")
