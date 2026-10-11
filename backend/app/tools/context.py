"""Du lieu cac tool nap MOT lan (PLAN - Entity Resolution + Admission Tool (v1), muc 1.2).

Hai cach dung, chung mot logic (K4):
  ToolContext.from_tables(build_db.build_rows())   -> test / validate_aliases.py, khong can DB
  await ToolContext.load()                         -> khi chay that, doc Postgres qua pool
"""

from collections import defaultdict
from dataclasses import dataclass, field

from app.db.pool import fetch_all
from app.entity_resolution.index import AliasIndex
from app.entity_resolution.resolver import Resolution, resolve
from app.entity_resolution.scan import Scanner

# Bang can cho alias + do phu nam. Bang nho (< 1000 dong) nen doc ca bang.
TABLES = ["programs", "program_years", "program_groups", "faculties", "certificates", "admission_methods",
          "entity_aliases", "admission_scores", "quotas", "program_methods", "program_combinations",
          "combinations", "tuition_program", "tuition_rules", "admission_fees"]
COVERAGE_TABLES = ["admission_scores", "quotas", "program_methods", "program_combinations", "program_years",
                   "tuition_program", "admission_fees"]


@dataclass
class Method:
    code: str
    name: str
    scale: int | None
    parent: str | None


@dataclass
class Coverage:
    years: dict[str, list[int]] = field(default_factory=dict)            # bang -> nam co du lieu
    score_years_by_method: dict[str, list[int]] = field(default_factory=dict)

    def latest(self, table: str) -> int:
        return self.years[table][-1]


class ToolContext:
    def __init__(self, T: dict[str, list[dict]]) -> None:
        self.aliases = AliasIndex.from_tables(T)
        self.scanner = Scanner(self.aliases)
        self.methods = {r["method_code"]: Method(r["method_code"], r["method_name"], r["scale"],
                                                 r["parent_method"] or None) for r in T["admission_methods"]}
        self.combinations = {r["combination_code"] for r in T["combinations"]}
        # (nganh, nam) -> phuong thuc: T3 gan cong thuc DGTD/XTTN theo phuong thuc cua nganh
        self.program_methods: dict[tuple[str, int], set[str]] = defaultdict(set)
        for r in T["program_methods"]:
            self.program_methods[(r["program_code"], int(r["year"]))].add(r["method_code"])
        self.coverage = Coverage(
            years={t: sorted({int(r["year"]) for r in T[t]}) for t in COVERAGE_TABLES})
        by_method = defaultdict(set)
        for r in T["admission_scores"]:
            by_method[r["method_code"]].add(int(r["year"]))
        self.coverage.score_years_by_method = {m: sorted(ys) for m, ys in by_method.items()}
        # Hoc phi theo nhom (nam) va theo tin chi (tin_chi) co nam rieng — T4
        for kind in ("nam", "tin_chi"):
            self.coverage.years[f"tuition_{kind}"] = sorted({int(r["year"]) for r in T["tuition_rules"]
                                                           if r["rule_type"] == kind})

    @classmethod
    def from_tables(cls, T: dict[str, list[dict]]) -> "ToolContext":
        return cls(T)

    @classmethod
    async def load(cls) -> "ToolContext":
        T = {}
        for t in TABLES:
            T[t] = await fetch_all(f"SELECT * FROM {t}")  # type: ignore[arg-type]  # ten bang co dinh o tren
        return cls(T)

    def resolve(self, mention: str, entity_type: str, years: list[int] | None = None) -> Resolution:
        return resolve(mention, entity_type, self.aliases, years)

    def expand_method(self, code: str) -> list[str]:
        """XTTN -> [XTTN_1.1, XTTN_1.2, XTTN_1.3]: bang diem chuan ghi theo ma con."""
        children = sorted(c for c, m in self.methods.items() if m.parent == code)
        return children or [code]


_ctx: ToolContext | None = None


async def get_context() -> ToolContext:
    global _ctx
    if _ctx is None:
        _ctx = await ToolContext.load()
    return _ctx
