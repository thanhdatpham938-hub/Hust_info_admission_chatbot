"""T3 program_info: thong tin nganh (PLAN - T3 program_info (v1)).

Tra loi "nganh X la gi, thuoc Truong nao, hoc tieng gi, may nam, tuyen bao nhieu, xet phuong thuc va
to hop nao, diem tinh the nao". KHONG tra diem chuan (T1), hoc phi (T4), lien he (T6) — P1.
Nhan dung chu nguoi dung go va tu goi Entity Resolution nhu T1 (D2). Khong goi LLM (D1).
"""

from app.db.pool import fetch_all
from app.schemas.common import ErrorCode, Missing, Source, Status, ToolResult, dedupe_sources
from app.schemas.program_info import (CombinationItem, FormulaItem, MethodItem, Overview, ProgramInfo,
                                      ProgramInfoData, ProgramInfoInput, QuotaItem)
from app.tools.common import (MAX_ENTITIES, TOO_MANY_MESSAGE, ambiguous_result, invalid_result, pick_years,
                              resolve_mentions, row_source)
from app.tools.context import ToolContext, get_context

ALL_SECTIONS = ("overview", "quota", "methods", "combinations")
OVERVIEW_YEAR = 2026            # P2: thong tin chung chi thu tu trang gioi thieu nganh nam 2026
OVERVIEW_LABELS = {"language": "ngôn ngữ đào tạo", "degree": "bằng tốt nghiệp", "duration": "thời gian đào tạo",
                   "curriculum_url": "link chương trình đào tạo", "short_description": "mô tả ngắn"}
PROGRAM_PAGE_TITLE = "Trang giới thiệu ngành trên ts.hust.edu.vn"

BASE_SQL = """
SELECT p.program_code, p.program_name, p.faculty_code, f.faculty_name, p.program_group_code,
       g.group_name, p.language, p.degree, p.duration, p.curriculum_url, p.short_description, p.program_page_url
FROM programs p
JOIN faculties f USING (faculty_code)
LEFT JOIN program_groups g USING (program_group_code)
WHERE p.program_code = ANY(%(codes)s)
"""
QUOTA_SQL = """
SELECT program_code, year, quota, quota_type, source, source_url, verification_status
FROM quotas WHERE program_code = ANY(%(codes)s) AND year = ANY(%(years)s) AND quota IS NOT NULL
ORDER BY program_code, year
"""
METHOD_SQL = """
SELECT pm.program_code, pm.year, pm.method_code, m.method_name, m.scale,
       pm.source, pm.source_url, pm.verification_status
FROM program_methods pm JOIN admission_methods m USING (method_code)
WHERE pm.program_code = ANY(%(codes)s) AND pm.year = ANY(%(years)s)
ORDER BY pm.program_code, pm.year, pm.method_code
"""
COMBO_SQL = """
SELECT pc.program_code, pc.year, pc.method_code, pc.combination_code, c.subjects, pc.main_subject,
       pc.formula_type, pc.source, pc.source_url, pc.verification_status
FROM program_combinations pc JOIN combinations c USING (combination_code)
WHERE pc.program_code = ANY(%(codes)s) AND pc.year = ANY(%(years)s)
ORDER BY pc.program_code, pc.year, pc.method_code, pc.combination_code
"""
FORMULA_SQL = """
SELECT formula_type, method_code, year, scale, formula, note, source, source_url, verification_status
FROM scoring_formulas WHERE year = ANY(%(years)s)
"""


async def program_info(inp: ProgramInfoInput, ctx: ToolContext | None = None) -> ToolResult[ProgramInfoData]:
    ctx = ctx or await get_context()
    programs = list(dict.fromkeys(p.strip() for p in inp.programs if p.strip()))
    if not programs:
        return invalid_result("Cần ít nhất một ngành.")
    if len(programs) > MAX_ENTITIES or len(set(inp.years)) > MAX_ENTITIES:
        return invalid_result(TOO_MANY_MESSAGE)
    sections = set(inp.fields) or set(ALL_SECTIONS)

    years, missing = pick_years(ctx, "program_years", inp.years)
    prog = resolve_mentions(ctx, programs, "program", years or None)
    if prog.clarifications:
        return ambiguous_result(prog.clarifications, prog.resolved)
    if prog.groups or len(prog.codes) > MAX_ENTITIES:       # P8
        return invalid_result(f"{TOO_MANY_MESSAGE} Câu hỏi theo cả nhóm ngành/Trường dùng list_programs.",
                              resolved=prog.resolved)
    missing += prog.missing
    if not prog.codes or not years:
        code = ErrorCode.ENTITY_NOT_FOUND if not prog.codes and not prog.missing else ErrorCode.DATA_NOT_FOUND
        return ToolResult(status=Status.NOT_FOUND, error_code=code, missing=missing, resolved=prog.resolved)

    codes = prog.codes
    params = {"codes": codes, "years": years}
    base = {r["program_code"]: r for r in await fetch_all(BASE_SQL, {"codes": codes})}
    quotas = await fetch_all(QUOTA_SQL, params) if "quota" in sections else []
    methods = await fetch_all(METHOD_SQL, params) if "methods" in sections else []
    combos = await fetch_all(COMBO_SQL, params) if "combinations" in sections else []
    formulas = await fetch_all(FORMULA_SQL, params) if "combinations" in sections else []
    formula_by_key = {(f["formula_type"], f["year"]): f for f in formulas}

    notes: list[str] = []
    cov = ctx.coverage.years
    out: list[ProgramInfo] = []
    for code in codes:
        b = base[code]
        name = b["program_name"]
        open_years = sorted(ctx.aliases.valid_years[code])
        asked_open = [y for y in years if y in open_years]
        for y in years:
            if y not in open_years:
                missing.append(Missing(what=f"{name} ({code}) năm {y}", reason="program_not_open",
                                       available_years=open_years))

        info = ProgramInfo(program_code=code, program_name=name, faculty_code=b["faculty_code"],
                           faculty_name=b["faculty_name"], program_group_code=b["program_group_code"],
                           program_group_name=b["group_name"], open_years=open_years)

        # ---- thong tin chung (P2, P7)
        if "overview" in sections:
            if b["program_page_url"]:
                info.overview = Overview(
                    **{k: (b[k] or None) for k in OVERVIEW_LABELS}, as_of_year=OVERVIEW_YEAR,
                    source=Source(title=PROGRAM_PAGE_TITLE, url=b["program_page_url"], year=OVERVIEW_YEAR,
                                  verification_status="web_extracted"))
                missing += [Missing(what=f"{label} {code}", reason="not_collected")
                            for k, label in OVERVIEW_LABELS.items() if not b[k]]
            else:
                missing.append(Missing(what=f"thông tin chung (trang giới thiệu ngành) của {name} ({code})",
                                       reason="not_collected"))

        # ---- chi tieu, phuong thuc (P6): co tu 2025
        for section, rows, table, label in (("quota", quotas, "quotas", "chỉ tiêu"),
                                            ("methods", methods, "program_methods", "phương thức xét tuyển")):
            if section not in sections:
                continue
            mine = [r for r in rows if r["program_code"] == code]
            have = {r["year"] for r in mine}
            for y in asked_open:
                if y not in have:
                    missing.append(Missing(what=f"{label} {code} năm {y}", reason="not_collected",
                                           available_years=[x for x in cov[table] if x in open_years]))
            if section == "quota":
                info.quotas = [QuotaItem(year=r["year"], quota=r["quota"], quota_type=r["quota_type"],
                                         source=row_source(r)) for r in mine]
            else:
                info.methods = [MethodItem(year=r["year"], method_code=r["method_code"], method_name=r["method_name"],
                                           scale=r["scale"], source=row_source(r)) for r in mine]

        # ---- to hop + cong thuc (P4, P5, P10, P11)
        if "combinations" in sections:
            mine = [r for r in combos if r["program_code"] == code]
            have = {r["year"] for r in mine}
            for y in asked_open:
                if y not in have:
                    missing.append(Missing(what=f"tổ hợp xét tuyển {code} năm {y}", reason="not_collected",
                                           available_years=cov["program_combinations"]))
                    note = (f"Năm {y} chưa có danh sách tổ hợp theo ngành; tổ hợp đại diện năm đó đi kèm "
                            "từng dòng điểm chuẩn (admission_scores).")
                    if note not in notes:
                        notes.append(note)
            info.combinations = [CombinationItem(
                year=r["year"], method_code=r["method_code"], combination_code=r["combination_code"],
                subjects=r["subjects"], main_subject=r["main_subject"] or None, formula_type=r["formula_type"],
                main_subject_known=r["formula_type"] != "chua_ro") for r in mine]
            # Cong thuc theo to hop (THPT) + theo phuong thuc cua nganh (DGTD, XTTN: P11) — moi cong thuc mot lan
            keys = list(dict.fromkeys((r["formula_type"], r["year"]) for r in mine))
            keys += [(m, y) for y in sorted(have) for m in sorted(ctx.program_methods.get((code, y), ()))
                     if (m, y) in formula_by_key and (m, y) not in keys]
            info.formulas = [_formula(formula_by_key[k]) for k in keys if k in formula_by_key]
        out.append(info)

    data = ProgramInfoData(programs=out, notes=notes)
    has_content = any(p.overview or p.quotas or p.methods or p.combinations for p in out)
    sources = dedupe_sources(
        [p.overview.source for p in out if p.overview]
        + [q.source for p in out for q in p.quotas] + [m.source for p in out for m in p.methods]
        + [row_source(r) for r in combos] + [f.source for p in out for f in p.formulas])
    if not has_content:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data,
                          missing=missing, resolved=prog.resolved, sources=sources)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=prog.resolved, sources=sources)


def _formula(r: dict) -> FormulaItem:
    return FormulaItem(formula_type=r["formula_type"], method_code=r["method_code"], year=r["year"],
                       scale=r["scale"], formula=r["formula"] or None, note=r["note"] or None, source=row_source(r))
