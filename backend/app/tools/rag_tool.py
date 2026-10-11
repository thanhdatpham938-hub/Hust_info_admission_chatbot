"""T7 rag_search: tim doan van ban quy che, de an, so tay, gioi thieu nganh/Truong (PLAN - T7 retrieval (v2)).

Phan giai nganh/Truong nhu T1-T6, goi Retriever, dong ToolResult. Khong goi LLM sinh chu; chi goi embedding.
"""

from app.rag.retriever import Retriever, SearchSpec
from app.schemas.common import ErrorCode, Source, Status, ToolResult, dedupe_sources
from app.schemas.rag import RagSearchData, RagSearchInput, RetrievedChunk
from app.tools.certificate import cohort_number
from app.tools.common import MAX_ENTITIES, TOO_MANY_MESSAGE, ambiguous_result, invalid_result, resolve_mentions
from app.tools.context import ToolContext, get_context

LOW_CONFIDENCE = 0.40          # R6: nguong TAM (anh duyet 2026-10-11), chot chinh thuc o Tuan 4
MAX_TOP_K = 10
FIRST_K71 = 71
GROUP_MESSAGE = "Câu hỏi theo cả nhóm ngành: hãy hỏi theo từng ngành cụ thể, hoặc bỏ lọc ngành."

_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def cohort_label(cohort: str | None) -> str | None:
    """'K71' / 'khoá 2026' -> 'K71+'; 'K70' / 'K68' -> '<=K70' (dung gia tri payload cohort)."""
    if not cohort:
        return None
    k = cohort_number(cohort)
    if k is None:
        return None
    return "K71+" if k >= FIRST_K71 else "<=K70"


def citation_of(p: dict) -> Source:
    """'Ten tai lieu — Dieu 15 khoan 2 — Trang 18' (van ban); 'Ten — <muc>' (trang web khong co so trang). PRD 12."""
    parts = [p["document_title"]]
    if p.get("dieu_no"):
        parts.append(f"Điều {p['dieu_no']}" + (f" khoản {p['khoan_no']}" if p.get("khoan_no") else ""))
    elif p.get("heading"):
        parts.append(p["heading"])
    if p.get("page_no"):
        parts.append(f"Trang {p['page_no']}")
    return Source(title=" — ".join(parts), url=p.get("source_url") or "", year=p.get("year"),
                  verification_status=p.get("verification_status"))


async def rag_search(inp: RagSearchInput, ctx: ToolContext | None = None,
                     retriever: Retriever | None = None) -> ToolResult[RagSearchData]:
    ctx = ctx or await get_context()
    retriever = retriever or get_retriever()
    if not inp.query.strip():
        return invalid_result("Câu hỏi rỗng.")
    if len(inp.programs) > MAX_ENTITIES or len(inp.faculties) > MAX_ENTITIES:
        return invalid_result(TOO_MANY_MESSAGE)
    if not 1 <= inp.top_k <= MAX_TOP_K:
        return invalid_result(f"top_k phải từ 1 đến {MAX_TOP_K}.")

    prog = resolve_mentions(ctx, inp.programs, "program", inp.years or None)
    if prog.clarifications:                                   # R7 (anh duyet): hoi lai
        return ambiguous_result(prog.clarifications, prog.resolved)
    if prog.groups:
        return invalid_result(GROUP_MESSAGE, resolved=prog.resolved)
    fac = resolve_mentions(ctx, inp.faculties, "faculty", None)
    if fac.clarifications:
        return ambiguous_result(fac.clarifications, prog.resolved + fac.resolved)
    resolved, missing = prog.resolved + fac.resolved, prog.missing + fac.missing

    cohort = cohort_label(inp.cohort)
    res = await retriever.search(SearchSpec(query=inp.query, years=inp.years, cohort=cohort,
                                            document_types=inp.document_types, program_codes=prog.codes,
                                            faculty_codes=fac.codes, top_k=inp.top_k))
    chunks = []
    for i, h in enumerate(res.hits, 1):
        p = h.payload
        chunks.append(RetrievedChunk(
            rank=i, chunk_id=p["chunk_id"], document_title=p["document_title"], document_type=p["document_type"],
            document_no=p.get("document_no") or None, year=p["year"], heading=p.get("heading") or "",
            chuong=p.get("chuong") or None, dieu_no=p.get("dieu_no") or None, khoan_no=p.get("khoan_no") or None,
            muc_no=p.get("muc_no") or None, page_no=str(p["page_no"]) if p.get("page_no") else None,
            source_url=p.get("source_url") or "", verification_status=p.get("verification_status") or "",
            cohort=p.get("cohort") or None, program_code=p.get("program_code") or None,
            faculty_code=p.get("faculty_code") or None, is_latest=bool(p.get("is_latest")),
            versioned=bool(p.get("versioned")), dense_score=round(h.dense_score, 4), text=p.get("text") or "",
            citation=citation_of(p)))

    data = RagSearchData(chunks=chunks, top_dense_score=round(res.top_dense_score, 4),
                         low_confidence=res.top_dense_score < LOW_CONFIDENCE,
                         phrases_used=[ph.shown for ph in res.phrases])
    found = sorted({c.cohort for c in chunks if c.cohort})
    if len(found) > 1 and not cohort:                         # R5
        data.cohorts_found = found
        data.notes.append("Kết quả có quy định của cả khoá K70 trở về trước và K71 trở về sau — cần hỏi người "
                          "dùng thuộc khoá nào trước khi trả lời.")
    sources = dedupe_sources([c.citation for c in chunks])
    if data.low_confidence:                                   # R6
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.LOW_RETRIEVAL_CONFIDENCE, data=data,
                          missing=missing, resolved=resolved, sources=sources)
    if not chunks:
        return ToolResult(status=Status.NOT_FOUND, error_code=ErrorCode.DATA_NOT_FOUND, data=data,
                          missing=missing, resolved=resolved)
    return ToolResult(status=Status.PARTIAL if missing else Status.OK, data=data, missing=missing,
                      resolved=resolved, sources=sources)
