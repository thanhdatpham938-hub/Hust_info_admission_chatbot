"""T5 certificate_lookup: chung chi ngoai ngu (PLAN - T4 T5 hoc phi va chung chi (v1), muc B).

Ba muc dich KHONG duoc dung lan (PRD 15.1):
  xet_tuyen     cert_bonus: diem thuong + diem quy doi mon tieng Anh (2024 tach 2 bang, 2025-2026 bang chung)
  chuan_dau_ra  cert_output (bac) + language_requirements (yeu cau theo nganh) — chi co khoa K71 tro ve sau
  khung_cefr    cert_cefr: chung chi -> CEFR / bac KNLNN
Muc dich trong -> hoi lai (B5-T1); chuan dau ra khong noi khoa -> hoi lai (B5-T2). Khong goi LLM (D1).
"""

import re

from app.db.pool import fetch_all
from app.entity_resolution.normalize import normalize
from app.schemas.certificate import (CefrLevel, CertConversion, CertificateData, CertificateInput, ExitLevel,
                                     ExitRequirement)
from app.schemas.common import Candidate, Clarification, ErrorCode, Missing, Status, ToolResult, dedupe_sources
from app.tools.common import MAX_ENTITIES, TOO_MANY_MESSAGE, ambiguous_result, invalid_result, resolve_mentions, \
    row_source
from app.tools.context import ToolContext, get_context

FIRST_K71_YEAR = 2026          # khoa K = nam nhap hoc - 1955: K71 nhap hoc 2026
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
SIMPLE_REQ = re.compile(r"Có chứng chỉ .* từ Bậc (\d) trở lên")

PURPOSE_CANDIDATES = [Candidate(code="xet_tuyen", name="Quy đổi điểm / điểm thưởng khi xét tuyển", entity_type="purpose"),
                      Candidate(code="chuan_dau_ra", name="Chuẩn đầu ra ngoại ngữ khi tốt nghiệp", entity_type="purpose")]
COHORT_CANDIDATES = [Candidate(code="K71+", name="Khoá 71 trở về sau (nhập học từ 2026)", entity_type="cohort"),
                     Candidate(code="K70-", name="Khoá 70 trở về trước", entity_type="cohort")]

CERT_SQL = "SELECT cert_code, cert_name, language FROM certificates WHERE cert_code = ANY(%(codes)s)"
BONUS_SQL = """
SELECT cert_code, cert_value, table_purpose, year, value_min, value_max, bonus_point, converted_score_10, note,
       source, source_url, verification_status
FROM cert_bonus WHERE cert_code = ANY(%(codes)s) ORDER BY cert_code, year, table_purpose, value_min NULLS LAST, cert_value
"""
OUTPUT_SQL = """
SELECT cert_code, cert_value, level, level_group, year, value_min, value_max, note, source, source_url, verification_status
FROM cert_output WHERE cert_code = ANY(%(codes)s) ORDER BY cert_code, level, value_min NULLS LAST
"""
CEFR_SQL = """
SELECT cert_code, cert_value, year, value_min, value_max, cefr_level, knlnn_level, source, source_url, verification_status
FROM cert_cefr WHERE cert_code = ANY(%(codes)s) ORDER BY cert_code, value_min NULLS LAST
"""
REQ_SQL = """
SELECT r.req_id, r.year, r.cohort, r.group_text, r.main_language, r.degree_level, r.requirement, r.min_level_group,
       r.note, r.source, r.source_url, r.verification_status,
       array_agg(m.program_code ORDER BY m.program_code) AS members
FROM language_requirements r JOIN language_req_members m USING (req_id)
WHERE m.program_code = ANY(%(codes)s)
GROUP BY r.req_id ORDER BY r.req_id
"""


def match_value(rows: list[dict], value: str | None) -> tuple[list[dict], bool | None]:
    """So (6.5, 300) -> dong co value_min <= v <= value_max; chu (N3, B2, 275-395) -> cert_value chua chu do.
    Khong khop dong nao -> tra CA BANG, matched=False (B5-T8)."""
    if value is None or not value.strip():
        return rows, None
    v = value.strip()
    if NUMBER.fullmatch(v):
        x = float(v.replace(",", "."))
        hit = [r for r in rows if r["value_min"] is not None and x >= float(r["value_min"])
               and (r["value_max"] is None or x <= float(r["value_max"]))]
    else:
        key = normalize(v)
        hit = [r for r in rows if key and key in normalize(r["cert_value"])]
    return (hit, True) if hit else (rows, False)


def cohort_number(cohort: str) -> int | None:
    """'K71' / 'khoá 71' / '71' -> 71; 'khoá 2026' / '2026' -> 71 (nam nhap hoc - 1955)."""
    m = re.search(r"\d+", cohort)
    if not m:
        return None
    n = int(m.group())
    return n - 1955 if n >= 1956 else n


def level_number(level_group: str | None) -> int | None:
    m = re.search(r"\d", level_group or "")
    return int(m.group()) if m else None


async def certificate_lookup(inp: CertificateInput, ctx: ToolContext | None = None) -> ToolResult[CertificateData]:
    ctx = ctx or await get_context()
    if inp.purpose is None:                                   # B5-T1
        return ambiguous_result([Clarification(mention="mục đích tra chứng chỉ", candidates=PURPOSE_CANDIDATES)], [])
    if len(inp.programs) > MAX_ENTITIES:
        return invalid_result(TOO_MANY_MESSAGE)

    cert = resolve_mentions(ctx, [inp.certificate], "certificate", None)
    if cert.clarifications:                                   # TOEFL -> iBT / ITP
        return ambiguous_result(cert.clarifications, cert.resolved)
    if not cert.codes:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.ENTITY_NOT_FOUND, missing=cert.missing,
                          resolved=cert.resolved)
    codes = cert.codes                                        # TOEIC -> 4 ky nang
    names = {r["cert_code"]: r for r in await fetch_all(CERT_SQL, {"codes": codes})}
    data = CertificateData(cert_codes=codes)
    missing: list[Missing] = []
    resolved = list(cert.resolved)
    rows_for_sources: list[dict] = []
    if any(c.startswith("TOEIC") for c in codes):            # B5-T3
        data.notes.append("TOEIC tra theo từng kỹ năng (Nghe, Đọc, Nói, Viết; Nói/Viết thang 200). Khi xét tuyển, "
                          "điểm thưởng và điểm quy đổi là trung bình cộng 4 kỹ năng.")

    # ---------------------------------------------------------------- xet tuyen
    if inp.purpose == "xet_tuyen":
        rows = await fetch_all(BONUS_SQL, {"codes": codes})
        have = sorted({r["year"] for r in rows})
        year = inp.year or (have[-1] if have else None)
        if year not in have:
            missing.append(Missing(what=f"bảng quy đổi chứng chỉ {inp.certificate} khi xét tuyển năm {year}",
                                   reason="not_collected", available_years=have))
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data, missing=missing,
                              resolved=resolved)
        mine, data.matched = match_value([r for r in rows if r["year"] == year], inp.value)
        rows_for_sources += mine
        data.conversions = [CertConversion(
            cert_code=r["cert_code"], cert_name=names[r["cert_code"]]["cert_name"], cert_value=r["cert_value"],
            year=r["year"], table=r["table_purpose"], bonus_point=r["bonus_point"],
            converted_score_10=float(r["converted_score_10"]) if r["converted_score_10"] is not None else None,
            note=r["note"] or None, source=row_source(r)) for r in mine]
        if {r["table_purpose"] for r in mine} >= {"quy_doi", "diem_thuong"}:      # B5-T4
            data.notes.append(f"Năm {year} có hai bảng riêng: bảng quy đổi điểm môn tiếng Anh và bảng điểm thưởng "
                              "(ranh giới mức khác nhau).")

    # ---------------------------------------------------------------- chuan dau ra
    elif inp.purpose == "chuan_dau_ra":
        if not inp.cohort:                                    # B5-T2
            return ambiguous_result([Clarification(mention="khoá học", candidates=COHORT_CANDIDATES)], resolved)
        k = cohort_number(inp.cohort)
        if k is None:
            return invalid_result(f"Không hiểu khoá {inp.cohort!r}; ghi dạng K71 hoặc năm nhập học.")
        if k < FIRST_K71_YEAR - 1955:
            missing.append(Missing(what=f"bảng chuẩn đầu ra ngoại ngữ khoá K{k}", reason="not_collected"))
            data.notes.append("Bảng số chỉ có khoá K71 trở về sau (Quy định 10828/QĐ-ĐHBK). Khoá K70 trở về trước "
                              "theo Quy định 10728/QĐ-ĐHBK ngày 26/9/2025 — tra văn bản (RAG).")
            return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data, missing=missing,
                              resolved=resolved)
        levels, data.matched = match_value(await fetch_all(OUTPUT_SQL, {"codes": codes}), inp.value)
        rows_for_sources += levels
        data.exit_levels = [ExitLevel(cert_code=r["cert_code"], cert_name=names[r["cert_code"]]["cert_name"],
                                      cert_value=r["cert_value"], level=r["level"], level_group=r["level_group"],
                                      note=r["note"] or None, source=row_source(r)) for r in levels]
        if inp.programs:
            prog = resolve_mentions(ctx, inp.programs, "program", None)
            if prog.clarifications:
                return ambiguous_result(prog.clarifications, resolved + prog.resolved)
            resolved += prog.resolved
            missing += prog.missing
            reqs = await fetch_all(REQ_SQL, {"codes": prog.codes}) if prog.codes else []
            rows_for_sources += reqs
            reached = [level_number(x.level_group) for x in data.exit_levels] if data.matched else []
            languages = {names[c]["language"] for c in codes}
            for r in reqs:
                data.requirements.append(ExitRequirement(
                    req_id=r["req_id"], cohort=r["cohort"], group_text=r["group_text"], main_language=r["main_language"],
                    degree_level=r["degree_level"], requirement=r["requirement"], min_level_group=r["min_level_group"],
                    note=r["note"] or None, program_codes=[c for c in r["members"] if c in prog.codes],
                    meets=_meets(r, reached, languages), source=row_source(r)))
            missing += [Missing(what=f"yêu cầu chuẩn đầu ra ngoại ngữ của {c}", reason="not_collected")
                        for c in prog.codes if not any(c in r["members"] for r in reqs)]

    # ---------------------------------------------------------------- khung CEFR
    else:
        cefr, data.matched = match_value(await fetch_all(CEFR_SQL, {"codes": codes}), inp.value)
        rows_for_sources += cefr
        data.cefr = [CefrLevel(cert_code=r["cert_code"], cert_name=names[r["cert_code"]]["cert_name"],
                               cert_value=r["cert_value"], cefr_level=r["cefr_level"], knlnn_level=r["knlnn_level"],
                               source=row_source(r)) for r in cefr]

    sources = dedupe_sources([row_source(r) for r in rows_for_sources])
    if not (data.conversions or data.exit_levels or data.cefr or data.requirements):
        missing.append(Missing(what=f"{inp.certificate} cho mục đích {inp.purpose}", reason="not_collected"))
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data, missing=missing,
                          resolved=resolved, sources=sources)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=resolved, sources=sources)


def _meets(req: dict, reached: list[int | None], languages: set[str]) -> bool | None:
    """B5-T5: chi ket luan khi yeu cau dang "Co chung chi ... tu Bac N tro len", cung ngon ngu, khong phai yeu cau
    dau khoa, va da biet bac cua chung chi. Con lai None — bot dua nguyen van yeu cau."""
    m = SIMPLE_REQ.fullmatch((req["requirement"] or "").strip())
    if not m or ";" in req["requirement"] or req["main_language"] not in languages:
        return None
    if "đầu kh" in (req["degree_level"] or "").lower() or "ĐẦU KHÓA" in (req["note"] or ""):
        return None
    got = [x for x in reached if x is not None]
    if not got:
        return None
    return min(got) >= int(m.group(1))
