"""Synthesizer (PLAN - Synthesizer (v1), muc 2-3): goi ket qua tool thanh "bang chung" danh so, LLM viet cau tra loi.

LLM chi ghi [n]; code dung trich dan tu metadata (PRD 12). Bang dai do code dung (render.LONG_TABLE). Ten nganh cho cau
tieng Anh do code chon (Q6 = C), LLM chi chep.
"""

import json
import re
from collections.abc import Mapping
from datetime import date
from functools import lru_cache
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.llm import get_llm
from app.entity_resolution.normalize import normalize
from app.graph.guardrails.numbers import numbers_in, question_numbers
from app.graph.render import LONG_TABLE, md_table

PROMPT_PATH = Path(__file__).parent / "prompts" / "synthesizer.md"
SYNTH_TEMPERATURE = 0.2          # PRD 17
SYNTH_MAX_TOKENS = 1000
TABLE_TOOLS = {"admission_scores", "list_programs", "program_info", "tuition_fees", "certificate_lookup",
               "university_info"}
DROP = {"source", "sources", "citation", "dense_score", "chunk_id", "verification_status", "is_latest", "versioned",
        "rank", "phrases_used", "cohorts_found", "top_dense_score", "low_confidence", "source_url", "collection_date",
        "dataset_version", "combination_group", "faculty_code", "program_group_code", "document_type",
        "program_code_filter", "rule_id"}


class SynthError(RuntimeError):
    pass


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items() if k not in DROP and v not in (None, [], {}, "")}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def _location(ch: dict, language: str) -> str:
    en = language == "en"
    parts = []
    if ch.get("dieu_no"):
        parts.append(f"{'Article' if en else 'Điều'} {ch['dieu_no']}")
    if ch.get("khoan_no"):
        parts.append(f"{'clause' if en else 'khoản'} {ch['khoan_no']}")
    if ch.get("page_no"):
        parts.append(f"{'page' if en else 'trang'} {ch['page_no']}")
    return ", ".join(parts) or ch.get("heading", "")


INTERNAL_GROUP = re.compile(r"\s*-\s*nhóm\s+\d+\s*$", re.I)


def _name_tuition_rules(data: dict, language: str, names: Mapping[str, tuple[str, str | None]]) -> None:
    """Buoc 5 (PLAN Sua loi, S07): moi muc hoc phi nhom / tin chi kem `ap_dung_cho` = "ten nganh (MA)" thay cho ma tho;
    bo nhan noi bo "nhóm 620" (du an tu dat theo so tien khi boc bang, nguoi doc khong hieu)."""
    for key in ("year_rules", "credit_rules"):
        for rule in data.get(key) or []:
            if rule.get("group_text"):
                rule["group_text"] = INTERNAL_GROUP.sub("", rule["group_text"])
            codes = rule.pop("program_codes", None) or []
            if codes:
                rule["ap_dung_cho"] = [_program_label(c, language, names) for c in codes]


# N10 (S09): hoi CA NHOM ma khong co y liet ke -> chi gui ban tom tat cua tool (stats), khong noi bang 38 dong va 38
# nguon. Bang du chi khi cau co y liet ke. Quyet dinh bang code de tat dinh.
LIST_WORDS = re.compile(r"\b(liet ke|danh sach|tung nganh|cac nganh nao|nhung nganh nao|nganh nao|bang hoc phi|"
                        r"list|each program|every program|all programs|which programs)\b")
PROGRAM_INDEX_URL = "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc"   # trang danh muc 68 nganh (da crawl)
GROUP_SOURCE_TITLE = {False: "Trang giới thiệu ngành trên ts.hust.edu.vn, mục Thông tin nhanh ({n} ngành)",
                      True: "Program pages on ts.hust.edu.vn, Quick facts section ({n} programs)"}


def wants_list(question: str) -> bool:
    return bool(LIST_WORDS.search(normalize(question)))


def _summarize_group(call: dict, data: dict, question: str) -> int:
    """Tra so nganh neu da thay bang chi tiet bang ban tom tat; 0 neu giu nguyen."""
    progs = data.get("programs") or []
    if not call["args"].get("program_group") or len(progs) <= TIE_MAX or not data.get("stats")             or wants_list(question):
        return 0
    data.pop("programs")
    for st in data["stats"]:
        st.pop("program_codes", None)
    return len(progs)


TIE_MAX = 3            # hon 3 nganh cung hang -> gop mot dong
TIE_EXAMPLES = 5


def _collapse_ties(rows: list[dict], language: str, names: Mapping[str, tuple[str, str | None]]) -> list[dict]:
    """N9 (S04): xep hang co nhieu nganh BANG DIEM (XTTN 1.2: 16 nganh cung 55) -> mot dong "16 nganh cung muc",
    kem 5 ten. Hoi "nganh thap nhat" thi moi phuong thuc mot dong, khong phai 34 dong. Giu thu tu tool tra."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r.get("year"), r.get("method_code"), r.get("combination_group"), r.get("rank")), []).append(r)
    out = []
    for grp in groups.values():
        if len(grp) <= TIE_MAX:
            out += grp
            continue
        first = grp[0]
        labels = [f"{(names.get(r['program_code']) or (None, None))[1] or r['program_name']} ({r['program_code']})"
                  if language == "en" else f"{r['program_name']} ({r['program_code']})" for r in grp]
        out.append({k: first.get(k) for k in ("rank", "year", "method_code", "combination_group_label", "value",
                                              "scale")}
                   | {"so_nganh_cung_hang": len(grp), "vi_du": labels[:TIE_EXAMPLES],
                      "con_lai": max(0, len(grp) - TIE_EXAMPLES), "source": first.get("source")})
    return out


TOTAL_QUOTA_NOTE = ("Đây là TỔNG chỉ tiêu của ngành cho mọi phương thức; dữ liệu chưa có chỉ tiêu theo từng "
                    "phương thức.")


def _label_quotas(data: dict) -> None:
    """N1 (S06, S32): chi tieu `tong_nganh` doi ten thanh `tong_chi_tieu_nganh` kem ghi chu. Quy tac prompt "ghi dung
    loai so lieu" khong du (2/2 cau van goi tong chi tieu la chi tieu theo phuong thuc); de chinh du lieu tu noi loai."""
    for prog in data.get("programs") or []:
        for q in prog.get("quotas") or []:
            if q.get("quota_type") == "tong_nganh" and "quota" in q:
                q["tong_chi_tieu_nganh"] = q.pop("quota")
                q.pop("quota_type")
                q["ghi_chu"] = TOTAL_QUOTA_NOTE


def _program_label(code: str, language: str, names: Mapping[str, tuple[str, str | None]]) -> str:
    vi, en = names.get(code, (None, None))
    name = (en or vi) if language == "en" else vi
    return f"{name} ({code})" if name else code


def _codes(result: dict) -> list[str]:
    return [c for r in result.get("resolved") or [] if r.get("entity_type") in ("program", "program_group")
            for c in r.get("codes") or []]


def build_evidence(question: str, intent: str, language: str, scope_note: str | None, calls: list[dict],
                   results: list[dict], program_names: Mapping[str, tuple[str, str | None]] | None = None,
                   today: date | None = None) -> dict:
    """Tra dict (luu duoc vao checkpoint): payload cho LLM, sources danh so, bang da dung, tap so duoc phep."""
    sources: list[dict] = []
    by_key: dict[tuple, int] = {}
    tables: list[str] = []
    evidence = []
    rag_used = tuition_used = False

    def source_id(title: str, url: str, location: str = "") -> int:
        key = (url, location)
        if key not in by_key:
            by_key[key] = len(sources) + 1
            sources.append({"n": by_key[key], "title": title, "url": url, "location": location})
        return by_key[key]

    codes: list[str] = []
    for call, res in zip(calls, results):
        if res.get("status") not in ("ok", "partial", "not_found"):
            continue
        item = {"tool": call["tool"], "status": res["status"]}
        if call["tool"] == "rag_search":
            chunks = (res.get("data") or {}).get("chunks") or []
            if res["status"] in ("ok", "partial") and chunks:
                rag_used = True
            # Ten tai lieu + vi tri tach rieng: citation.title cua T7 da gom vi tri, ghep them thi in lap (buoc 1)
            # rank 1 = lien quan nhat (buoc 5): giup LLM uu tien doan dung (S12 dung nham Dieu 12 thay Dieu 19)
            item["chunks"] = [{"id": source_id(ch.get("document_title") or ch["citation"]["title"],
                                               ch["citation"]["url"], _location(ch, language)),
                               "rank": i, "document": ch.get("document_title"), "heading": ch.get("heading"),
                               "year": ch.get("year"), "cohort": ch.get("cohort"), "text": ch.get("text")}
                              for i, ch in enumerate(chunks, 1)]
        else:
            raw = res.get("data") or {}
            if call["tool"] == "list_programs" and isinstance(raw, dict) and raw.get("rows"):
                raw = {**raw, "rows": _collapse_ties(raw["rows"], language, program_names or {})}
            data = _clean(raw)
            group_summary = (call["tool"] == "tuition_fees" and isinstance(data, dict)
                             and _summarize_group(call, data, question))
            if call["tool"] == "tuition_fees" and isinstance(data, dict):
                _name_tuition_rules(data, language, program_names or {})
            if call["tool"] == "program_info" and isinstance(data, dict):
                _label_quotas(data)
            if isinstance(data, dict):
                for k, v in list(data.items()):
                    if isinstance(v, list) and len(v) > LONG_TABLE and all(isinstance(x, dict) for x in v):
                        tables.append(md_table(v, language))
                        data[k] = {"bang_da_hien_thi": len(tables), "so_dong": len(v)}
            item["data"] = data
            if group_summary:
                item["source_ids"] = [source_id(GROUP_SOURCE_TITLE[language == "en"].format(n=group_summary),
                                                PROGRAM_INDEX_URL)]
            else:
                item["source_ids"] = [source_id(s.get("title", ""), s["url"]) for s in res.get("sources") or []
                                      if s.get("url")]
            if call["tool"] == "tuition_fees" and res["status"] in ("ok", "partial"):
                tuition_used = True
        if res.get("missing"):
            item["missing"] = res["missing"]
        evidence.append(item)
        codes += [c for c in _codes(res) if c not in codes]

    payload = {"question": question, "intent": intent, "language": language, "scope_note": scope_note,
               "evidence": evidence,
               "sources": {str(s["n"]): f"{s['title']}" + (f" — {s['location']}" if s["location"] else "")
                           for s in sources}}
    if tables:
        payload["tables_note"] = (f"Đã có {len(tables)} bảng do hệ thống dựng sẵn và sẽ hiển thị ngay sau câu trả lời. "
                                  "KHÔNG chép lại các bảng đó; chỉ viết câu dẫn và nhận xét ngắn.")
    if today:                    # N8: khong co thi LLM tu hieu "nam ngoai" theo kien thuc cu (S04 ghi 2024)
        payload["hom_nay"] = {"ngay": today.isoformat(), "nam_nay": today.year, "nam_ngoai": today.year - 1}
    if language == "en" and program_names:
        payload["program_names"] = {c: {"en": program_names[c][1], "vi": program_names[c][0]}
                                    for c in codes if c in program_names}
    allowed = numbers_in([r.get("data") for r in results] + [r.get("missing") for r in results]
                         + [s["location"] for s in sources] + tables)
    allowed |= question_numbers(question, advice=scope_note == "advice")
    if today:
        allowed |= {float(today.year), float(today.year - 1)}
    return {"payload": payload, "sources": sources, "tables": tables, "allowed": sorted(allowed),
            "rag_used": rag_used, "tuition_used": tuition_used,
            "table_source_ids": sorted({n for it in evidence for n in it.get("source_ids", [])})}


@lru_cache
def system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


LANGUAGE_REMINDER = {"en": "Write the answer in ENGLISH.", "vi": "Viết câu trả lời bằng tiếng Việt."}


def build_messages(payload: dict, issues: list[str] | None = None) -> list[dict]:
    # Nhac ngon ngu NGAY SAU du lieu (buoc 2): du lieu gan nhu toan tieng Viet lan at quy tac o prompt he thong
    reminder = LANGUAGE_REMINDER["en" if payload.get("language") == "en" else "vi"]
    msgs = [{"role": "system", "content": system_prompt()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False) + "\n\n" + reminder}]
    if issues:
        msgs.append({"role": "user", "content": "Câu trả lời trước có lỗi, hãy viết lại và sửa đúng các lỗi sau:\n- "
                                                + "\n- ".join(issues)})
    return msgs


async def generate(payload: dict, issues: list[str] | None = None, client: AsyncOpenAI | None = None,
                   model: str | None = None) -> str:
    client = client or get_llm()
    model = model or get_settings().chat_model
    try:
        r = await client.chat.completions.create(model=model, temperature=SYNTH_TEMPERATURE,
                                                 max_tokens=SYNTH_MAX_TOKENS, messages=build_messages(payload, issues))
    except Exception as e:                                       # noqa: BLE001 — loi mang/timeout
        raise SynthError(str(e)) from e
    text = (r.choices[0].message.content or "").strip()
    if not text:
        raise SynthError("Synthesizer trả rỗng")
    return text
