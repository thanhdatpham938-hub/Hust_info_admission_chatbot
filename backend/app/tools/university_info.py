"""T6 university_info: thong tin Truong/Khoa (PLAN - T6 university_info (v1)).

Lien he, kenh thong tin chinh thuc (AC9: cau hoi thong bao chi tra link nay), don vi truc thuoc, danh sach nganh
theo nam, ten cu. Hoi theo nganh -> Truong/Khoa quan ly. Lien he chi lay tu bang, khong qua RAG (U1).
Khong goi LLM (D1).
"""

from app.db.pool import fetch_all
from app.schemas.common import Candidate, Clarification, ErrorCode, Missing, Resolved, Source, Status, ToolResult, \
    dedupe_sources
from app.schemas.university_info import (Contact, FacultyInfo, ProgramRef, Unit, UniversityInfoData,
                                         UniversityInfoInput)
from app.tools.common import MAX_ENTITIES, TOO_MANY_MESSAGE, ambiguous_result, invalid_result, resolve_mentions
from app.tools.context import ToolContext, get_context

ALL_SECTIONS = ("contact", "channel", "units", "programs")
UNIT_LABELS = {"khoa": "Khoa", "bo_mon": "Bộ môn", "trung_tam": "Trung tâm"}      # U10
GROUP_MESSAGE = "Nhóm ngành gồm nhiều ngành thuộc nhiều Trường/Khoa; hãy hỏi theo từng ngành cụ thể."
CONTACT_TITLE = "Mục \"Đơn vị quản lý\" trên trang giới thiệu ngành (ts.hust.edu.vn)"

# contact_note la ghi chu NOI BO ve cho lech nguon — khong lay ra (U7)
FAC_SQL = """
SELECT faculty_code, faculty_name, official_channel_url, phone, email, address, contact_source_url,
       verification_status
FROM faculties WHERE %(codes)s::text[] IS NULL OR faculty_code = ANY(%(codes)s) ORDER BY faculty_code
"""
UNIT_SQL = """
SELECT faculty_code, unit_name, unit_type, source_url, verification_status
FROM faculty_units WHERE faculty_code = ANY(%(codes)s) ORDER BY faculty_code, unit_type, unit_name
"""
PROG_SQL = """
SELECT p.program_code, p.program_name, p.program_group_code, p.faculty_code
FROM programs p JOIN program_years y USING (program_code)
WHERE p.faculty_code = ANY(%(codes)s) AND y.year = %(year)s ORDER BY p.program_code
"""
FACULTY_OF_SQL = "SELECT program_code, faculty_code FROM programs WHERE program_code = ANY(%(codes)s)"
OLD_NAME_SQL = """
SELECT entity_code, alias FROM entity_aliases
WHERE entity_type = 'faculty' AND alias_type = 'old_name' AND entity_code = ANY(%(codes)s) ORDER BY alias
"""


async def university_info(inp: UniversityInfoInput, ctx: ToolContext | None = None
                          ) -> ToolResult[UniversityInfoData]:
    ctx = ctx or await get_context()
    faculties = list(dict.fromkeys(f.strip() for f in inp.faculties if f.strip()))
    programs = list(dict.fromkeys(p.strip() for p in inp.programs if p.strip()))
    if len(faculties) > MAX_ENTITIES or len(programs) > MAX_ENTITIES:
        return invalid_result(TOO_MANY_MESSAGE)
    sections = set(inp.fields) or set(ALL_SECTIONS)
    have_years = ctx.coverage.years["program_years"]
    year = inp.year or have_years[-1]
    missing: list[Missing] = []
    if year not in have_years:
        missing.append(Missing(what=f"danh sách ngành năm {year}", reason="year_out_of_range",
                               available_years=have_years))

    # ---- Truong/Khoa neu truc tiep
    fac = resolve_mentions(ctx, faculties, "faculty", None)
    if fac.clarifications:
        return ambiguous_result(fac.clarifications, fac.resolved)
    missing += fac.missing
    resolved = list(fac.resolved)
    codes = list(fac.codes)

    # ---- nganh -> Truong/Khoa quan ly (U4, U5)
    asked: dict[str, list[str]] = {}            # faculty_code -> nganh nguoi dung hoi
    clarifications: list[Clarification] = []
    prog_years = [year] if year in have_years else None
    for mention in programs:
        r = ctx.resolve(mention, "program", prog_years)
        if r.status == "group":
            return invalid_result(GROUP_MESSAGE, resolved=resolved)
        if r.status == "not_found":
            reason = "program_not_open" if r.other_years else "entity_not_found"
            missing.append(Missing(what=mention, reason=reason,
                                   available_years=sorted({y for ys in r.other_years.values() for y in ys})))
            continue
        fac_of = {x["program_code"]: x["faculty_code"] for x in await fetch_all(FACULTY_OF_SQL, {"codes": r.codes})}
        if r.status == "clarify" and len(set(fac_of.values())) > 1:
            clarifications.append(Clarification(mention=mention, candidates=[
                Candidate(code=c, name=f"{ctx.aliases.name('program', c)} ({ctx.aliases.name('faculty', fac_of[c])})",
                          entity_type="program") for c in r.codes]))
            continue
        # unique, hoac mo ho nhung moi ung vien cung mot Truong/Khoa -> tra luon (U4)
        resolved.append(Resolved(mention=mention, entity_type="program", codes=r.codes,
                                 matched_by=r.matched_by or "exact"))
        for c in r.codes:
            f = fac_of[c]
            asked.setdefault(f, [])
            if c not in asked[f]:
                asked[f].append(c)
            if f not in codes:
                codes.append(f)
    if clarifications:
        return ambiguous_result(clarifications, resolved)

    if (faculties or programs) and not codes:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.ENTITY_NOT_FOUND, missing=missing,
                          resolved=resolved)

    # ---- lay du lieu
    rows = await fetch_all(FAC_SQL, {"codes": codes or None})
    order = {c: i for i, c in enumerate(codes)}
    rows.sort(key=lambda r: order.get(r["faculty_code"], len(order) + 1))
    all_codes = [r["faculty_code"] for r in rows]
    units = await fetch_all(UNIT_SQL, {"codes": all_codes}) if "units" in sections else []
    progs = await fetch_all(PROG_SQL, {"codes": all_codes, "year": year}) \
        if "programs" in sections and year in have_years else []
    old = await fetch_all(OLD_NAME_SQL, {"codes": all_codes})

    out, sources = [], []
    for r in rows:
        code = r["faculty_code"]
        info = FacultyInfo(faculty_code=code, faculty_name=r["faculty_name"],
                           former_names=[o["alias"] for o in old if o["entity_code"] == code],
                           asked_programs=sorted(asked.get(code, [])))
        if "channel" in sections:
            info.official_channel_url = r["official_channel_url"] or None
            if info.official_channel_url:
                sources.append(Source(title=f"Website chính thức {r['faculty_name']}", url=r["official_channel_url"],
                                      verification_status=r["verification_status"]))
            else:
                missing.append(Missing(what=f"kênh thông tin chính thức {code}", reason="not_collected"))
        if "contact" in sections:
            src = Source(title=CONTACT_TITLE, url=r["contact_source_url"] or "",
                         verification_status=r["verification_status"])
            info.contact = Contact(phones=[p.strip() for p in (r["phone"] or "").split(";") if p.strip()],
                                   email=r["email"] or None, address=r["address"] or None, source=src)
            sources.append(src)
            for label, value in (("điện thoại", r["phone"]), ("email", r["email"]), ("địa chỉ", r["address"])):
                if not value:
                    missing.append(Missing(what=f"{label} {code}", reason="not_collected"))
        if "units" in sections:
            mine = [u for u in units if u["faculty_code"] == code]
            info.units = [Unit(unit_name=u["unit_name"], unit_type=u["unit_type"],
                               unit_type_label=UNIT_LABELS.get(u["unit_type"], u["unit_type"])) for u in mine]
            sources += [Source(title=f"Cơ cấu tổ chức {r['faculty_name']}", url=u["source_url"],
                               verification_status=u["verification_status"]) for u in mine if u["source_url"]]
            if not mine:                                       # U9
                missing.append(Missing(what=f"đơn vị trực thuộc {code}", reason="not_collected"))
        if "programs" in sections and year in have_years:      # U8
            info.programs_year = year
            info.programs = [ProgramRef(program_code=p["program_code"], program_name=p["program_name"],
                                        program_group_code=p["program_group_code"])
                             for p in progs if p["faculty_code"] == code]
        out.append(info)

    data = UniversityInfoData(faculties=out)
    if not out:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data, missing=missing,
                          resolved=resolved)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=resolved, sources=dedupe_sources(sources))
