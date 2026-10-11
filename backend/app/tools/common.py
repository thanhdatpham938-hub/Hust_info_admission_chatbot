"""Ham dung chung cua cac tool (PLAN - T3 program_info (v1), muc 7): phan giai cum tu nguoi dung go,
bao loi theo khuon ToolResult, chon nam theo do phu du lieu. Tach tu admission.py de T1-T6 dung mot ban.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas.common import (Candidate, Clarification, ErrorCode, Missing, Resolved, Source, Status,
                                ToolResult)
from app.tools.context import ToolContext

MAX_ENTITIES = 3
TOO_MANY_MESSAGE = "Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác."     # PRD 10.2


@dataclass
class Outcome:
    codes: list[str] = field(default_factory=list)
    per_mention: dict[str, list[str]] = field(default_factory=dict)   # cum -> ma (de bao missing theo cum)
    clarifications: list[Clarification] = field(default_factory=list)
    resolved: list[Resolved] = field(default_factory=list)
    missing: list[Missing] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)                    # cum tro toi nhom nganh


def resolve_mentions(ctx: ToolContext, mentions: list[str], etype: str, years: list[int] | None,
                     *, take_all_on_clarify: bool = False) -> Outcome:
    out = Outcome()
    for mention in dict.fromkeys(m.strip() for m in mentions if m and m.strip()):
        r = ctx.resolve(mention, etype, years)
        if r.status == "clarify" and not take_all_on_clarify:
            kind = "program" if etype == "program" else etype
            out.clarifications.append(Clarification(mention=mention, candidates=[
                Candidate(code=c, name=ctx.aliases.name(kind, c), entity_type=kind) for c in r.codes]))
            continue
        if r.status == "not_found":
            if r.other_years:
                for code, ys in r.other_years.items():
                    out.missing.append(Missing(what=f"{mention} ({code})", reason="program_not_open",
                                               available_years=ys))
            else:
                out.missing.append(Missing(what=mention, reason="entity_not_found"))
            continue
        if r.status == "group" and r.group_code:
            out.groups.append(r.group_code)
        out.per_mention[mention] = r.codes
        out.codes += [c for c in r.codes if c not in out.codes]
        out.resolved.append(Resolved(mention=mention, entity_type=etype, codes=r.codes,
                                     matched_by=r.matched_by or "exact"))
    return out


def row_source(r: dict) -> Source:
    return Source(title=r["source"] or "", url=r["source_url"] or "", year=r["year"],
                  verification_status=r["verification_status"])


def to_float(x: Decimal | float | int) -> float:
    return float(round(Decimal(x), 2))


def invalid_result(message: str, **kw) -> ToolResult:
    return ToolResult(status=Status.INVALID, error_code=ErrorCode.INVALID_REQUEST, message=message, **kw)


def ambiguous_result(clarifications: list[Clarification], resolved: list[Resolved]) -> ToolResult:
    # K1: co mot cum can hoi lai thi KHONG truy van gi
    return ToolResult(status=Status.AMBIGUOUS, error_code=ErrorCode.ENTITY_AMBIGUOUS,
                      clarifications=clarifications, resolved=resolved)


def pick_years(ctx: ToolContext, table: str, years: list[int]) -> tuple[list[int], list[Missing]]:
    have = ctx.coverage.years[table]
    asked = sorted(set(years)) or [have[-1]]          # anh chot: khong noi nam -> nam moi nhat
    missing = [Missing(what=f"năm {y}", reason="year_out_of_range", available_years=have)
               for y in asked if y not in have]
    return [y for y in asked if y in have], missing
