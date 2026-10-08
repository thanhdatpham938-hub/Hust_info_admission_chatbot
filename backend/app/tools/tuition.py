"""T4 tuition_fees: hoc phi va le phi tuyen sinh (PLAN - T4 T5 hoc phi va chung chi (v1), muc A).

Bon loai so lieu, moi loai co nam rieng:
  program    hoc phi theo nganh (trang nganh)            2026
  year_rule  hoc phi theo nhom, nam hoc 2024-2025          2024
  credit     hoc phi tin chi, theo tung nam hoc           2024, 2025, 2026 (nam hoc bat dau)
  fee        le phi tuyen sinh (phi thu tuc, khong phai hoc phi)   2024
Khong quy doi /hoc ky sang /nam (A5-T1), khong tinh chenh lech (A5-T3). Khong goi LLM (D1).
"""

from collections import defaultdict

from app.db.pool import fetch_all
from app.schemas.common import ErrorCode, Missing, Status, ToolResult, dedupe_sources
from app.schemas.tuition import AdmissionFee, ProgramTuition, TuitionData, TuitionInput, TuitionRule, UnitStat
from app.tools.common import (MAX_ENTITIES, TOO_MANY_MESSAGE, ambiguous_result, invalid_result, resolve_mentions,
                              row_source)
from app.tools.context import ToolContext, get_context

NEED_SCOPE_MESSAGE = "Cần nêu ngành hoặc nhóm ngành để tra học phí theo ngành / theo nhóm."
FLAT = "toàn bộ chương trình"          # TROY: thu tron goi theo hoc ky (A5-T10)
SCALE = (("triệu đồng", 1_000_000), ("nghìn đồng", 1_000), ("đồng", 1))

PROGRAM_SQL = """
SELECT t.program_code, p.program_name, p.program_group_code, t.year, t.amount_min, t.amount_max, t.unit,
       t.is_approximate, t.terms_per_year, t.amount_text, t.source, t.source_url, t.verification_status
FROM tuition_program t JOIN programs p USING (program_code)
WHERE t.program_code = ANY(%(codes)s) AND t.year = ANY(%(years)s)
ORDER BY t.program_code, t.year
"""
RULE_SQL = """
SELECT r.rule_id, r.rule_type, r.year, r.academic_year, r.group_text, r.course_type, r.cohort, r.applies_to_all,
       r.amount_min, r.amount_max, r.unit, r.note, r.source, r.source_url, r.verification_status,
       COALESCE(array_agg(m.program_code ORDER BY m.program_code) FILTER (WHERE m.program_code IS NOT NULL),
                '{}') AS members
FROM tuition_rules r LEFT JOIN tuition_rule_members m USING (rule_id)
WHERE r.rule_type = %(kind)s AND r.year = ANY(%(years)s)
GROUP BY r.rule_id
ORDER BY r.year, r.rule_id
"""
FEE_SQL = """
SELECT fee_type, year, amount, unit, note, source, source_url, verification_status
FROM admission_fees WHERE year = ANY(%(years)s) ORDER BY year, amount
"""


def to_vnd(amount: float, unit: str) -> tuple[int, str]:
    """Doi CAP TIEN ra dong (A5-T11): 26000 'nghìn đồng/học kỳ' -> 26_000_000 'đồng/học kỳ'. Khong doi ky han."""
    for prefix, factor in SCALE:
        if unit.startswith(prefix):
            return round(amount * factor), "đồng" + unit[len(prefix):]
    raise ValueError(f"Đơn vị tiền lạ: {unit!r}")


def _years(ctx: ToolContext, key: str, asked: list[int], what: str) -> tuple[list[int], list[Missing]]:
    have = ctx.coverage.years[key]
    ys = sorted(set(asked)) or [have[-1]]
    return [y for y in ys if y in have], [Missing(what=f"{what} năm {y}", reason="not_collected", available_years=have)
                                          for y in ys if y not in have]


def _rule(r: dict, codes: list[str] | None) -> TuitionRule:
    lo, unit_vnd = to_vnd(r["amount_min"], r["unit"])
    hi, _ = to_vnd(r["amount_max"], r["unit"])
    members = r["members"] if codes is None else [c for c in r["members"] if c in codes]
    return TuitionRule(rule_id=r["rule_id"], rule_type=r["rule_type"], year=r["year"],
                       academic_year=r["academic_year"], group_text=r["group_text"], course_type=r["course_type"],
                       cohort=r["cohort"], applies_to_all=bool(r["applies_to_all"]), amount_min=float(r["amount_min"]),
                       amount_max=float(r["amount_max"]), unit=r["unit"], amount_vnd_min=lo, amount_vnd_max=hi,
                       unit_vnd=unit_vnd, program_codes=members, note=r["note"] or None, source=row_source(r))


async def tuition_fees(inp: TuitionInput, ctx: ToolContext | None = None) -> ToolResult[TuitionData]:
    ctx = ctx or await get_context()
    kinds = set(inp.kinds) or {"program"}
    programs = list(dict.fromkeys(p.strip() for p in inp.programs if p.strip()))
    if len(programs) > MAX_ENTITIES or len(set(inp.years)) > MAX_ENTITIES:
        return invalid_result(TOO_MANY_MESSAGE)
    if kinds & {"program", "year_rule"} and not programs and not inp.program_group:
        return invalid_result(NEED_SCOPE_MESSAGE)

    # ---- pham vi nganh
    # Hoc phi tin chi / theo nhom ap dung cho SINH VIEN DANG HOC moi khoa, khong chi khoa tuyen nam do: EM4 ngung
    # tuyen tu 2026 nhung QD hoc phi 2026-2027 van ghi "Ke toan". Chi hoc phi theo nganh (trang nganh 2026) moi
    # loc theo nam tuyen sinh.
    years_for_resolve = (sorted(set(inp.years)) or None) if "program" in kinds \
        else ctx.coverage.years["program_years"]
    prog = resolve_mentions(ctx, programs, "program", years_for_resolve)
    if prog.clarifications:                      # A5-T7: tung nganh cu the -> hoi lai
        return ambiguous_result(prog.clarifications, prog.resolved)
    missing, resolved = list(prog.missing), list(prog.resolved)
    codes = list(prog.codes)
    is_group = bool(prog.groups)
    if inp.program_group:
        grp = resolve_mentions(ctx, [inp.program_group], "program", years_for_resolve, take_all_on_clarify=True)
        missing += grp.missing
        resolved += grp.resolved
        codes += [c for c in grp.codes if c not in codes]
        is_group = True                          # A5-T9: ca danh sach can hoi lai cung lay het
    scoped = bool(programs or inp.program_group)
    if scoped and not codes:
        code = ErrorCode.DATA_NOT_FOUND if any(m.reason == "program_not_open" for m in missing) \
            else ErrorCode.ENTITY_NOT_FOUND
        return ToolResult(status=Status.NOT_FOUND, error_code=code, missing=missing, resolved=resolved)

    data = TuitionData()
    rows_for_sources: list[dict] = []

    # ---- hoc phi theo nganh (2026)
    if "program" in kinds:
        ys, miss = _years(ctx, "tuition_program", inp.years, "học phí theo ngành")
        missing += miss
        if miss:
            data.notes.append("Học phí theo ngành chỉ có năm 2026. Có học phí tín chỉ (credit) các năm học "
                              "2024–2025 đến 2026–2027 và học phí theo nhóm năm học 2024–2025 (year_rule).")
        rows = await fetch_all(PROGRAM_SQL, {"codes": codes, "years": ys}) if ys else []
        rows_for_sources += rows
        for r in rows:
            lo, unit_vnd = to_vnd(r["amount_min"], r["unit"])
            hi, _ = to_vnd(r["amount_max"], r["unit"])
            data.programs.append(ProgramTuition(
                program_code=r["program_code"], program_name=r["program_name"],
                program_group_code=r["program_group_code"], year=r["year"], amount_min=float(r["amount_min"]),
                amount_max=float(r["amount_max"]), unit=r["unit"], per="học kỳ" if "học kỳ" in r["unit"] else "năm",
                terms_per_year=r["terms_per_year"], is_approximate=bool(r["is_approximate"]),
                amount_text=r["amount_text"], amount_vnd_min=lo, amount_vnd_max=hi, unit_vnd=unit_vnd,
                source=row_source(r)))
        have = {(r["program_code"], r["year"]) for r in rows}
        missing += [Missing(what=f"học phí theo ngành {c} năm {y}", reason="not_collected")
                    for c in codes for y in ys if (c, y) not in have and y in ctx.aliases.valid_years[c]]
        if is_group:                              # A5-T2: moi don vi mot dong
            by_unit = defaultdict(list)
            for p in data.programs:
                by_unit[p.unit].append(p)
            data.stats = [UnitStat(unit=u, count=len(ps), min=min(p.amount_min for p in ps),
                                   max=max(p.amount_max for p in ps), program_codes=[p.program_code for p in ps])
                          for u, ps in sorted(by_unit.items())]

    # ---- hoc phi theo nhom, nam hoc 2024-2025
    if "year_rule" in kinds:
        ys, miss = _years(ctx, "tuition_nam", inp.years, "học phí theo nhóm")
        missing += miss
        rows = await fetch_all(RULE_SQL, {"kind": "nam", "years": ys}) if ys else []
        rows = [r for r in rows if set(r["members"]) & set(codes)]
        rows_for_sources += rows
        data.year_rules = [_rule(r, codes) for r in rows]
        if data.year_rules:
            data.notes.append("Học phí theo nhóm của năm học 2024–2025.")

    # ---- hoc phi tin chi theo nam hoc (A5-T4)
    if "credit" in kinds:
        ys, miss = _years(ctx, "tuition_tin_chi", inp.years, "học phí tín chỉ")
        missing += miss
        rows = await fetch_all(RULE_SQL, {"kind": "tin_chi", "years": ys}) if ys else []
        picked = []
        for y in ys:
            mine = [r for r in rows if r["year"] == y]
            if not scoped:
                picked += mine
                continue
            own = [r for r in mine if set(r["members"]) & set(codes)]
            flat_only = bool(own) and all(r["course_type"] == FLAT for r in own)   # A5-T10: TROY
            picked += own + ([] if flat_only else [r for r in mine if r["applies_to_all"]])
            covered = {c for r in own for c in r["members"]}
            missing += [Missing(what=f"học phí tín chỉ {c} năm học {y}-{y + 1}", reason="not_collected")
                        for c in codes if c not in covered and y in ctx.aliases.valid_years[c]]
        rows_for_sources += picked
        data.credit_rules = [_rule(r, codes if scoped else None) for r in picked]
        for y in ys:
            data.notes.append(f"Học phí tín chỉ năm học {y}–{y + 1}, tính cho 2 học kỳ chính; học kỳ hè tính 1,5 lần.")
        if any(r.course_type == FLAT for r in data.credit_rules):
            data.notes.append("TROY thu trọn gói theo học kỳ theo khoá (không theo tín chỉ), một năm học có 3 học kỳ; "
                              "phí ghi danh của trường đối tác 1,7 triệu đồng đóng một lần.")

    # ---- le phi tuyen sinh (A5-T6, A5-T12)
    if "fee" in kinds:
        ys, miss = _years(ctx, "admission_fees", inp.years, "lệ phí tuyển sinh")
        missing += miss
        rows = await fetch_all(FEE_SQL, {"years": ys}) if ys else []
        rows_for_sources += rows
        data.fees = [AdmissionFee(fee_type=r["fee_type"], year=r["year"], amount=r["amount"], unit=r["unit"],
                                  note=r["note"] or None, source=row_source(r)) for r in rows]
        if data.fees:
            data.notes.append("Lệ phí tuyển sinh theo Đề án tuyển sinh 2024 (phí thủ tục khi đăng ký thi/xét tuyển, "
                              "không phải học phí).")

    sources = dedupe_sources([row_source(r) for r in rows_for_sources])
    if not (data.programs or data.year_rules or data.credit_rules or data.fees):
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data, missing=missing,
                          resolved=resolved, sources=sources)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=resolved, sources=sources)
