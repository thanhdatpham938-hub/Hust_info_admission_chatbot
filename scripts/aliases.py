"""Chuan hoa ma nganh ve dang canonical.

Cac nguon chinh thuc cua HUST ghi ma khac nhau (TEEP vs TE-EP), nen moi script
build deu phai di qua day truoc khi ghi ra data/processed.
"""

import csv
from pathlib import Path

ALIAS_CSV = Path(__file__).resolve().parent.parent / "data" / "processed" / "program_aliases.csv"


def load(year: int | None = None) -> dict[str, str]:
    """Tra ve {alias_da_bo_khoang_trang: canonical_code} cho nam chi dinh."""
    if not ALIAS_CSV.exists():
        return {}
    with ALIAS_CSV.open(encoding="utf-8", newline="") as f:
        return {
            r["alias"].replace(" ", ""): r["canonical_code"]
            for r in csv.DictReader(f)
            if year is None or int(r["year"]) == year
        }


def canonical(code: str, aliases: dict[str, str]) -> str:
    clean = code.replace(" ", "").strip()
    return aliases.get(clean, clean)
