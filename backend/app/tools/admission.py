"""Admission Tool (PLAN - Entity Resolution + Admission Tool (v1), muc 3 va 4).

T1 admission_scores: diem chuan cua 1-3 nganh (PRD 10.2), co chenh lech do tool tinh.
T2 list_programs:    xep hang / ca bang / loc theo Truong-Khoa, nhom nganh, to hop; diem hoac chi tieu.

Tool nhan dung chu nguoi dung go va TU goi Entity Resolution (D2): LLM khong co duong nao bo qua
4 quy tac khop hay tu bia ma nganh. Khong goi LLM (D1).
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import combinations as pairs

from app.db.pool import fetch_all
from app.schemas.admission import (AdmissionScoresData, AdmissionScoresInput, Delta, GroupStat, ListProgramsData,
                                   ListProgramsInput, ListRow, ScoreRow)
from app.schemas.common import (Candidate, Clarification, ErrorCode, Missing, Resolved, Source, Status,
                                ToolResult, dedupe_sources)
from app.tools.context import ToolContext, get_context

MAX_ENTITIES = 3
MAX_LIMIT = 100
TOO_MANY_MESSAGE = "Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác."     # PRD 10.2
GROUP_LABELS = {      # A2: hai nhan sau theo dung cach goi trong score_note (bai cong bo diem chuan)
    "tat_ca": "mọi tổ hợp",
    "ky_thuat": "tổ hợp khối ngành kỹ thuật",
    "kinh_te_gd_nn": "tổ hợp khối ngành kinh tế, giáo dục, ngoại ngữ",
}


# ================================================================ phan giai cum tu (dung chung T1/T2)
@dataclass
class _Outcome:
    codes: list[str] = field(default_factory=list)
    per_mention: dict[str, list[str]] = field(default_factory=dict)   # cum -> ma (de bao missing theo cum)
    clarifications: list[Clarification] = field(default_factory=list)
    resolved: list[Resolved] = field(default_factory=list)
    missing: list[Missing] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)                    # cum tro toi nhom nganh


def _resolve_all(ctx: ToolContext, mentions: list[str], etype: str, years: list[int] | None,
                 *, take_all_on_clarify: bool = False) -> _Outcome:
    out = _Outcome()
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


def _source(r: dict) -> Source:
    return Source(title=r["source"] or "", url=r["source_url"] or "", year=r["year"],
                  verification_status=r["verification_status"])


def _f(x: Decimal | float | int) -> float:
    return float(round(Decimal(x), 2))


def _year_deltas(rows: list[dict], value_key: str) -> list[Delta]:
    """Cung nganh + phuong thuc + nhom to hop, cac nam lien ke (A1: khong so khac thang/khac khoi)."""
    by = defaultdict(list)
    for r in rows:
        by[(r["program_code"], r.get("method_code"), r.get("combination_group"))].append(r)
    out = []
    for (code, method, group), rs in by.items():
        rs.sort(key=lambda r: r["year"])
        for x, y in zip(rs, rs[1:]):
            out.append(Delta(kind="year", program_code=code, method_code=method, combination_group=group,
                             a=str(x["year"]), b=str(y["year"]), value_a=_f(x[value_key]),
                             value_b=_f(y[value_key]), diff=_f(Decimal(y[value_key]) - Decimal(x[value_key]))))
    return out


def _invalid(message: str, **kw) -> ToolResult:
    return ToolResult(status=Status.INVALID, error_code=ErrorCode.INVALID_REQUEST, message=message, **kw)


def _ambiguous(clarifications: list[Clarification], resolved: list[Resolved]) -> ToolResult:
    # K1: co mot cum can hoi lai thi KHONG truy van gi
    return ToolResult(status=Status.AMBIGUOUS, error_code=ErrorCode.ENTITY_AMBIGUOUS,
                      clarifications=clarifications, resolved=resolved)


def _years(ctx: ToolContext, table: str, years: list[int]) -> tuple[list[int], list[Missing]]:
    have = ctx.coverage.years[table]
    asked = sorted(set(years)) or [have[-1]]          # anh chot: khong noi nam -> nam moi nhat
    missing = [Missing(what=f"năm {y}", reason="year_out_of_range", available_years=have)
               for y in asked if y not in have]
    return [y for y in asked if y in have], missing


# ================================================================ T1 admission_scores
T1_SQL = """
SELECT s.program_code, p.program_name, s.year, s.method_code, m.method_name, s.combination_group,
       s.subject_combinations, s.score, s.scale, s.score_note, s.source, s.source_url, s.verification_status
FROM admission_scores s
JOIN programs p USING (program_code)
JOIN admission_methods m USING (method_code)
WHERE s.program_code = ANY(%(codes)s)
  AND s.year = ANY(%(years)s)
  AND (%(methods)s::text[] IS NULL OR s.method_code = ANY(%(methods)s))
ORDER BY s.program_code, s.year, s.method_code, s.combination_group
"""


async def admission_scores(inp: AdmissionScoresInput, ctx: ToolContext | None = None
                           ) -> ToolResult[AdmissionScoresData]:
    ctx = ctx or await get_context()
    programs = list(dict.fromkeys(p.strip() for p in inp.programs if p.strip()))
    if not programs:
        return _invalid("Cần ít nhất một ngành.")
    if max(len(programs), len(set(inp.years)), len(set(inp.methods))) > MAX_ENTITIES:
        return _invalid(TOO_MANY_MESSAGE)

    years, missing = _years(ctx, "admission_scores", inp.years)
    meth = _resolve_all(ctx, inp.methods, "method", None)
    prog = _resolve_all(ctx, programs, "program", years or None)
    resolved = prog.resolved + meth.resolved
    if prog.clarifications or meth.clarifications:
        return _ambiguous(prog.clarifications + meth.clarifications, resolved)
    if prog.groups or len(prog.codes) > MAX_ENTITIES:
        return _invalid(f"{TOO_MANY_MESSAGE} Câu hỏi theo cả nhóm ngành/Trường dùng list_programs.",
                        resolved=resolved)
    missing += prog.missing + meth.missing
    if not prog.codes or not years:
        code = ErrorCode.ENTITY_NOT_FOUND if not prog.codes else ErrorCode.DATA_NOT_FOUND
        return ToolResult(status=Status.NOT_FOUND, error_code=code, missing=missing, resolved=resolved)

    # Phuong thuc nguoi dung hoi -> ma trong bang diem (XTTN -> XTTN_1.1/1.2/1.3)
    method_sets = {m: sorted({x for c in codes for x in ctx.expand_method(c)}) for m, codes in meth.per_mention.items()}
    method_codes = sorted({x for v in method_sets.values() for x in v}) or None
    rows = await fetch_all(T1_SQL, {"codes": prog.codes, "years": years, "methods": method_codes})

    # Missing theo tung (nganh x nam [x phuong thuc]) da hoi (muc 3.2 buoc 6)
    have = {(r["program_code"], r["year"], r["method_code"]) for r in rows}
    for code in prog.codes:
        name = ctx.aliases.name("program", code)
        open_years = ctx.aliases.valid_years[code]
        for y in years:
            if y not in open_years:
                missing.append(Missing(what=f"{name} ({code}) năm {y}", reason="program_not_open",
                                       available_years=sorted(open_years)))
                continue
            for label, mcodes in (method_sets.items() or [("", None)]):
                if any((code, y, m) in have for m in (mcodes or [k[2] for k in have])):
                    continue
                what = f"điểm chuẩn {name} ({code}) năm {y}" + (f" phương thức {label}" if label else "")
                score_years = sorted({yy for m in (mcodes or []) for yy in ctx.coverage.score_years_by_method.get(m, [])})
                if mcodes and y not in score_years:
                    missing.append(Missing(what=what, reason="method_no_score", available_years=score_years))
                else:
                    missing.append(Missing(what=what, reason="not_collected"))

    data_rows = [ScoreRow(
        program_code=r["program_code"], program_name=r["program_name"], year=r["year"],
        method_code=r["method_code"], method_name=r["method_name"], combination_group=r["combination_group"],
        combination_group_label=GROUP_LABELS.get(r["combination_group"], r["combination_group"]),
        subject_combinations=[c for c in (r["subject_combinations"] or "").split(";") if c],
        score=_f(r["score"]), scale=r["scale"], score_note=r["score_note"] or None,
        is_rule_derived=r["verification_status"] == "rule_derived", source=_source(r)) for r in rows]

    deltas = _year_deltas(rows, "score")
    by_slot = defaultdict(dict)                # (nam, phuong thuc, khoi) -> {nganh: dong}
    for r in rows:
        by_slot[(r["year"], r["method_code"], r["combination_group"])][r["program_code"]] = r
    for (y, method, group), per in by_slot.items():
        ordered = [c for c in prog.codes if c in per]
        for a, b in pairs(ordered, 2):
            deltas.append(Delta(kind="program", method_code=method, combination_group=group, a=a, b=b,
                                value_a=_f(per[a]["score"]), value_b=_f(per[b]["score"]),
                                diff=_f(Decimal(per[b]["score"]) - Decimal(per[a]["score"]))))

    if not rows:
        status, err = Status.NOT_FOUND, ErrorCode.DATA_NOT_FOUND
    else:
        status, err = (Status.PARTIAL if missing else Status.OK), None
    return ToolResult(status=status, error_code=err, data=AdmissionScoresData(rows=data_rows, deltas=deltas),
                      missing=missing, resolved=resolved,
                      sources=dedupe_sources([row.source for row in data_rows]))


# ================================================================ T2 list_programs
# Chieu sap xep khong truyen bang tham so duoc -> hai cau SQL viet san, chon theo `order` (muc 4.2)
_SCORE_HEAD = """
SELECT * FROM (
  SELECT s.program_code, p.program_name, p.faculty_code, fa.faculty_name, p.program_group_code,
         s.year, s.method_code, s.combination_group, s.score AS value, s.scale,
         s.source, s.source_url, s.verification_status,
         RANK()   OVER (PARTITION BY s.year, s.method_code ORDER BY s.score """
_SCORE_TAIL = """) AS rnk,
         COUNT(*) OVER (PARTITION BY s.year, s.method_code) AS n,
         MIN(s.score) OVER (PARTITION BY s.year, s.method_code) AS vmin,
         MAX(s.score) OVER (PARTITION BY s.year, s.method_code) AS vmax
  FROM admission_scores s
  JOIN programs p USING (program_code)
  JOIN faculties fa USING (faculty_code)
  WHERE s.year = ANY(%(years)s) AND s.method_code = ANY(%(methods)s)
    AND (%(faculty)s::text IS NULL OR p.faculty_code = %(faculty)s)
    AND (%(grp)s::text IS NULL OR p.program_group_code = %(grp)s)
    AND (%(codes)s::text[] IS NULL OR s.program_code = ANY(%(codes)s))
    AND (%(combo)s::text IS NULL OR %(combo)s = ANY(string_to_array(s.subject_combinations, ';')))
    AND (%(without)s::text IS NULL OR NOT EXISTS (
          SELECT 1 FROM program_methods pm
          WHERE pm.program_code = s.program_code AND pm.year = s.year AND pm.method_code = %(without)s))
    AND (%(smin)s::numeric IS NULL OR s.score >= %(smin)s)
    AND (%(smax)s::numeric IS NULL OR s.score <= %(smax)s)
) t
WHERE %(limit)s::int IS NULL OR rnk <= %(limit)s
ORDER BY year, method_code, rnk, program_code, combination_group
"""
SCORE_SQL = {"desc": _SCORE_HEAD + "DESC" + _SCORE_TAIL, "asc": _SCORE_HEAD + "ASC" + _SCORE_TAIL}

_QUOTA_HEAD = """
SELECT * FROM (
  SELECT q.program_code, p.program_name, p.faculty_code, fa.faculty_name, p.program_group_code,
         q.year, q.quota AS value, q.source, q.source_url, q.verification_status,
         RANK()   OVER (PARTITION BY q.year ORDER BY q.quota """
_QUOTA_TAIL = """) AS rnk,
         COUNT(*) OVER (PARTITION BY q.year) AS n,
         MIN(q.quota) OVER (PARTITION BY q.year) AS vmin,
         MAX(q.quota) OVER (PARTITION BY q.year) AS vmax,
         SUM(q.quota) OVER (PARTITION BY q.year) AS vsum
  FROM quotas q
  JOIN programs p USING (program_code)
  JOIN faculties fa USING (faculty_code)
  WHERE q.year = ANY(%(years)s) AND q.quota IS NOT NULL
    AND (%(faculty)s::text IS NULL OR p.faculty_code = %(faculty)s)
    AND (%(grp)s::text IS NULL OR p.program_group_code = %(grp)s)
    AND (%(codes)s::text[] IS NULL OR q.program_code = ANY(%(codes)s))
    AND (%(combo)s::text IS NULL OR EXISTS (
          SELECT 1 FROM program_combinations pc
          WHERE pc.program_code = q.program_code AND pc.year = q.year AND pc.combination_code = %(combo)s))
    AND (%(without)s::text IS NULL OR NOT EXISTS (
          SELECT 1 FROM program_methods pm
          WHERE pm.program_code = q.program_code AND pm.year = q.year AND pm.method_code = %(without)s))
) t
WHERE %(limit)s::int IS NULL OR rnk <= %(limit)s
ORDER BY year, rnk, program_code
"""
QUOTA_SQL = {"desc": _QUOTA_HEAD + "DESC" + _QUOTA_TAIL, "asc": _QUOTA_HEAD + "ASC" + _QUOTA_TAIL}


async def list_programs(inp: ListProgramsInput, ctx: ToolContext | None = None) -> ToolResult[ListProgramsData]:
    ctx = ctx or await get_context()
    if len(set(inp.years)) > MAX_ENTITIES:
        return _invalid(TOO_MANY_MESSAGE)
    if inp.limit is not None and not 1 <= inp.limit <= MAX_LIMIT:
        return _invalid(f"limit phải từ 1 đến {MAX_LIMIT}, hoặc bỏ trống để lấy cả bảng.")

    table = "admission_scores" if inp.metric == "score" else "quotas"
    years, missing = _years(ctx, table, inp.years)
    notes: list[str] = []
    resolved: list[Resolved] = []
    clar: list[Clarification] = []

    # ---- phuong thuc
    methods: list[str] = []
    if inp.method:
        m = _resolve_all(ctx, [inp.method], "method", None)
        clar += m.clarifications; resolved += m.resolved; missing += m.missing
        methods = sorted({x for c in m.codes for x in ctx.expand_method(c)})
        if inp.metric == "quota" and m.codes:
            # T2-5: chi co chi tieu tong nganh (quota_type = tong_nganh)
            missing.append(Missing(what=f"chỉ tiêu theo phương thức {inp.method}", reason="not_collected"))
    if inp.metric == "score" and not methods:
        methods = sorted(m for m, ys in ctx.coverage.score_years_by_method.items() if set(ys) & set(years))

    # ---- pham vi: Truong/Khoa, nhom nganh, nganh (T2-3: alias mo ho -> lay het ung vien)
    faculty = grp = None
    if inp.faculty:
        f = _resolve_all(ctx, [inp.faculty], "faculty", None)
        clar += f.clarifications; resolved += f.resolved; missing += f.missing
        faculty = f.codes[0] if f.codes else None
        if not f.codes and not f.clarifications:
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.ENTITY_NOT_FOUND,
                              missing=missing, resolved=resolved)
    codes: list[str] = []
    if inp.program_group:
        g = _resolve_all(ctx, [inp.program_group], "program", years or None, take_all_on_clarify=True)
        resolved += g.resolved; missing += g.missing
        if g.groups:
            grp = g.groups[0]
        else:
            codes += g.codes
    if inp.programs:
        pr = _resolve_all(ctx, inp.programs, "program", years or None, take_all_on_clarify=True)
        resolved += pr.resolved; missing += pr.missing
        codes += [c for c in pr.codes if c not in codes]
        if not pr.codes:
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.ENTITY_NOT_FOUND,
                              missing=missing, resolved=resolved)
    if clar:
        return _ambiguous(clar, resolved)

    # ---- to hop, phuong thuc loai tru
    combo = inp.combination.strip().upper() if inp.combination else None
    if combo and combo not in ctx.combinations:
        missing.append(Missing(what=f"tổ hợp {inp.combination}", reason="entity_not_found"))
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.ENTITY_NOT_FOUND, missing=missing,
                          resolved=resolved)
    if combo and inp.metric == "score" and 2024 in years:
        notes.append("Năm 2024 chỉ có tổ hợp đại diện đi kèm từng dòng điểm chuẩn, chưa có danh sách tổ hợp "
                     "đầy đủ theo ngành.")              # T2-4, PRD 13.2
    without = None
    if inp.without_method:
        w = _resolve_all(ctx, [inp.without_method], "method", None)
        resolved += w.resolved; missing += w.missing
        if w.codes:
            # program_methods ghi theo ma cha (XTTN), khong theo XTTN_1.x
            without = ctx.methods[w.codes[0]].parent or w.codes[0]
            no_cov = [y for y in years if y not in ctx.coverage.years["program_methods"]]
            if no_cov:
                missing.append(Missing(what=f"danh sách phương thức theo ngành năm {', '.join(map(str, no_cov))}",
                                       reason="not_collected", available_years=ctx.coverage.years["program_methods"]))

    if not years:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, missing=missing,
                          resolved=resolved)

    params = {"years": years, "methods": methods, "faculty": faculty, "grp": grp, "codes": codes or None,
              "combo": combo, "without": without, "smin": inp.score_min, "smax": inp.score_max, "limit": inp.limit}
    sql = SCORE_SQL[inp.order] if inp.metric == "score" else QUOTA_SQL[inp.order]
    rows = await fetch_all(sql, params)

    out_rows = [ListRow(
        rank=r["rnk"], program_code=r["program_code"], program_name=r["program_name"],
        faculty_code=r["faculty_code"], faculty_name=r["faculty_name"], program_group_code=r["program_group_code"],
        year=r["year"], method_code=r.get("method_code"), combination_group=r.get("combination_group"),
        combination_group_label=GROUP_LABELS.get(r.get("combination_group") or "", None),
        value=_f(r["value"]), scale=r.get("scale"), is_rule_derived=r["verification_status"] == "rule_derived",
        source=_source(r)) for r in rows]

    stats, seen = [], set()
    for r in rows:
        k = (r["year"], r.get("method_code"))
        if k not in seen:
            seen.add(k)
            stats.append(GroupStat(year=r["year"], method_code=r.get("method_code"), count=r["n"],
                                   min=_f(r["vmin"]), max=_f(r["vmax"]),
                                   total=_f(r["vsum"]) if "vsum" in r else None))
    total_rows = sum(s.count for s in stats)

    deltas = _year_deltas(rows, "value") if len(years) > 1 else []
    if inp.metric == "quota" and len(stats) > 1:
        for a, b in zip(stats, stats[1:]):
            deltas.append(Delta(kind="total", a=str(a.year), b=str(b.year), value_a=a.total, value_b=b.total,
                                diff=_f(Decimal(str(b.total)) - Decimal(str(a.total)))))

    data = ListProgramsData(rows=out_rows, stats=stats, deltas=deltas, total_rows=total_rows,
                            truncated=len(out_rows) < total_rows, notes=notes)
    if not rows:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data,
                          missing=missing, resolved=resolved)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=resolved, sources=dedupe_sources([r.source for r in out_rows]))
