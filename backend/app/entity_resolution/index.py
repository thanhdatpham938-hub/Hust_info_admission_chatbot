"""Bang tra thuc the theo khoa da chuan hoa (PLAN - Entity Resolution + Admission Tool (v1), muc 2.2).

Dung tu cac bang cua build_db (dict ten bang -> list dong): khi chay that doc tu Postgres
(ToolContext.load), khi test / validate_aliases.py doc thang build_db.build_rows() — cung mot logic.
"""

from collections import defaultdict
from dataclasses import dataclass

from app.entity_resolution.normalize import compact, normalize

# kind: alias_type cua entity_aliases, hoac "code" (ma) / "name" (ten chinh thuc)
EXACT_ONLY_KINDS = {"abbrev", "code"}       # quy tac 4 PRD: chi tham gia khop chinh xac

# entity_type -> (bang, cot ma, cot ten)
CATALOG = {
    "program": ("programs", "program_code", "program_name"),
    "program_group": ("program_groups", "program_group_code", "group_name"),
    "faculty": ("faculties", "faculty_code", "faculty_name"),
    "certificate": ("certificates", "cert_code", "cert_name"),
    "method": ("admission_methods", "method_code", "method_name"),
}


@dataclass(frozen=True)
class Entry:
    code: str
    entity_type: str
    resolution: str      # unique | clarify | group
    kind: str            # alias_type | "code" | "name"
    text: str            # chuoi goc (de scan khop viet tat tren cau goc)


class AliasIndex:
    def __init__(self) -> None:
        self.exact: dict[str, list[Entry]] = defaultdict(list)
        self.names: dict[tuple[str, str], str] = {}               # (entity_type, code) -> ten
        self.valid_years: dict[str, set[int]] = defaultdict(set)  # program_code -> nam co tuyen
        self.group_members: dict[str, set[str]] = defaultdict(set)
        self.latest_year: int = 0

    def _add(self, key: str, entry: Entry) -> None:
        if key and entry not in self.exact[key]:
            self.exact[key].append(entry)

    @classmethod
    def from_tables(cls, T: dict[str, list[dict]]) -> "AliasIndex":
        idx = cls()
        for etype, (table, code_col, name_col) in CATALOG.items():
            resolution = "group" if etype == "program_group" else "unique"
            for r in T[table]:
                code, name = r[code_col], r[name_col]
                idx.names[(etype, code)] = name
                # Ma nhom nganh (chuan/elitech/pfiev/lien_ket) la ma NOI BO tu dat (PLAN Data Linking R8),
                # nguoi dung khong go — dua vao khoa tra thi "pfiev" lan alias PFIEV da chot (3 nganh)
                if etype != "program_group":
                    idx._add(normalize(code), Entry(code, etype, resolution, "code", code))
                    idx._add(compact(code), Entry(code, etype, resolution, "code", code))
                idx._add(normalize(name), Entry(code, etype, resolution, "name", name))
        for r in T["entity_aliases"]:
            idx._add(normalize(r["alias"]), Entry(r["entity_code"], r["entity_type"], r["resolution"],
                                                 r["alias_type"], r["alias"]))
        for r in T["program_years"]:
            idx.valid_years[r["program_code"]].add(int(r["year"]))
        for r in T["programs"]:
            if r.get("program_group_code"):
                idx.group_members[r["program_group_code"]].add(r["program_code"])
        idx.latest_year = max(y for ys in idx.valid_years.values() for y in ys)
        return idx

    def substring_keys(self) -> dict[str, list[Entry]]:
        """Khoa duoc tham gia B3 (chuoi con / fuzzy): bo ma va viet tat."""
        out = {}
        for key, entries in self.exact.items():
            kept = [e for e in entries if e.kind not in EXACT_ONLY_KINDS]
            if kept:
                out[key] = kept
        return out

    def name(self, entity_type: str, code: str) -> str:
        return self.names.get((entity_type, code), code)
