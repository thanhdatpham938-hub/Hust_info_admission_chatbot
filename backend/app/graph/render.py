"""Dung bang va cau tra loi bang CODE (PLAN - Synthesizer (v1), muc 2 va 5).

- Bang dai (> LONG_TABLE dong): code dung, LLM chi viet cau dan -> khong chep sai so, khong ton token ra.
- template_answer: ban du phong khi LLM viet sai 3 lan (Q7): dung chung cho moi tool (Q4), kem nguon va phan thieu.
"""

import re

from app.graph import templates as T

LONG_TABLE = 15          # nguoi dung chot 2026-10-20
# Cot noi bo hoac da the hien o cho khac (nguon in rieng, ma nhom to hop da co nhan)
HIDDEN = {"source", "sources", "citation", "verification_status", "combination_group", "faculty_code",
          "program_group_code", "is_latest", "versioned", "dense_score", "chunk_id", "source_url", "rank",
          "rule_id", "applies_to_all", "amount_vnd_min", "amount_vnd_max", "unit_vnd",
          # N6 (S09): `per` trung voi cot Don vi, `amount_text` trung voi Tu/Den
          "per", "amount_text"}
SOURCE_GROUP_MAX = 5     # N6: hon 5 nguon cung loai (trang tung nganh) -> gop mot dong
TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")
HEADERS = {
    "vi": {"program_code": "Mã ngành", "program_name": "Tên ngành", "year": "Năm", "method_code": "Mã PT",
           "method_name": "Phương thức", "combination_group_label": "Nhóm tổ hợp", "subject_combinations": "Tổ hợp",
           "score": "Điểm", "value": "Giá trị", "scale": "Thang", "score_note": "Ghi chú",
           "is_rule_derived": "Tính theo quy tắc", "faculty_name": "Trường/Khoa",
           # deltas (buoc 1: khong de ten cot tho kind / value_a)
           "kind": "So sánh", "a": "A", "b": "B", "value_a": "Giá trị A", "value_b": "Giá trị B",
           "diff": "Chênh lệch (B − A)",
           "group_text": "Chương trình", "ap_dung_cho": "Áp dụng cho", "course_type": "Loại học phần",
           "academic_year": "Năm học", "amount_min": "Từ", "amount_max": "Đến", "unit": "Đơn vị"},
    "en": {"program_code": "Code", "program_name": "Program", "year": "Year", "method_code": "Method code",
           "method_name": "Method", "combination_group_label": "Subject group", "subject_combinations": "Combinations",
           "score": "Score", "value": "Value", "scale": "Scale", "score_note": "Note",
           "is_rule_derived": "Rule-derived", "faculty_name": "School/Faculty",
           "kind": "Comparison", "a": "A", "b": "B", "value_a": "Value A", "value_b": "Value B",
           "diff": "Difference (B − A)",
           "group_text": "Program group", "ap_dung_cho": "Applies to", "course_type": "Course type",
           "academic_year": "Academic year", "amount_min": "From", "amount_max": "To", "unit": "Unit"},
}
KIND_LABELS = {"vi": {"year": "giữa các năm", "program": "giữa các ngành", "total": "tổng chỉ tiêu"},
               "en": {"year": "between years", "program": "between programs", "total": "total quota"}}


def fmt(v, language: str) -> str:
    if isinstance(v, bool):
        return ("có" if v else "") if language != "en" else ("yes" if v else "")
    if isinstance(v, float):
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return s.replace(".", ",") if language != "en" else s
    if isinstance(v, list):
        return ", ".join(fmt(x, language) for x in v)
    return "" if v is None else str(v)


TIE_KEYS = {"so_nganh_cung_hang", "vi_du", "con_lai"}


def tie_text(r: dict, language: str) -> str:
    """Dong gop hoa hang (synthesizer._collapse_ties) -> "16 ngành cùng mức: A, B, … và 11 ngành khác"."""
    names = ", ".join(r.get("vi_du") or [])
    if language == "en":
        return f"{r['so_nganh_cung_hang']} programs tied: {names}" + (
            f" and {r['con_lai']} more" if r.get("con_lai") else "")
    return f"{r['so_nganh_cung_hang']} ngành cùng mức: {names}" + (
        f" và {r['con_lai']} ngành khác" if r.get("con_lai") else "")


def md_table(rows: list[dict], language: str) -> str:
    keys = list(dict.fromkeys(k for r in rows for k in r))          # hop cot moi dong (dong gop hoa hang khac cot)
    if any("so_nganh_cung_hang" in r for r in rows) and "program_name" not in keys:
        keys.insert(0, "program_name")
    cols = [k for k in keys if k not in HIDDEN | TIE_KEYS and not any(isinstance(r.get(k), dict) for r in rows)
            and any(r.get(k) not in (None, "", [], False) or (k == "program_name" and "so_nganh_cung_hang" in r)
                    for r in rows)]
    lang = "en" if language == "en" else "vi"
    head = HEADERS[lang]

    def cell(r: dict, c: str) -> str:
        if c == "program_name" and "so_nganh_cung_hang" in r:
            return tie_text(r, language)
        v = r.get(c)
        return KIND_LABELS[lang].get(v, fmt(v, language)) if c == "kind" else fmt(v, language)
    lines = ["| " + " | ".join(head.get(c, c) for c in cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(cell(r, c) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def sources_block(sources: list[dict], used: set[int] | None, language: str) -> str:
    keep = [s for s in sources if used is None or s["n"] in used]
    if not keep:
        return ""
    title = "Nguồn" if language != "en" else "Sources"
    lines = [f"{title}:"]
    # N6 (S09): nhieu nguon cung loai, chi khac ma nganh trong ngoac -> mot dong "[1]–[38] ... (38 trang)".
    # Danh sach trich dan day du van nam trong `citations` cua API (PRD 12); chi phan hien thi duoc gop.
    groups: dict[str, list[dict]] = {}
    for s in keep:
        groups.setdefault(TRAILING_PAREN.sub("", s["title"]) if not s.get("location") else s["title"], []).append(s)
    done: set[int] = set()
    for s in keep:
        if s["n"] in done:
            continue
        base = TRAILING_PAREN.sub("", s["title"]) if not s.get("location") else s["title"]
        grp = groups[base]
        if len(grp) > SOURCE_GROUP_MAX:
            pages = "pages" if language == "en" else "trang"
            lines.append(f"[{grp[0]['n']}]–[{grp[-1]['n']}] {base} ({len(grp)} {pages}) — {grp[0]['url']}")
            done |= {x["n"] for x in grp}
            continue
        loc = f" — {s['location']}" if s.get("location") else ""
        lines.append(f"[{s['n']}] {s['title']}{loc} — {s['url']}")
        done.add(s["n"])
    return "\n".join(lines)


def template_answer(ev: dict, results: list[dict], language: str) -> str:
    """Ban dung tu du lieu tho: khong LLM, khong the sai so."""
    lang = "en" if language == "en" else "vi"
    parts = ["Here is the data I found:" if lang == "en" else "Dưới đây là dữ liệu tra được:"]
    for item in ev["payload"]["evidence"]:
        data = item.get("data") or {}
        tables = {k: v for k, v in (data.items() if isinstance(data, dict) else [])
                  if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)}
        if len(tables) > 1:                    # N9: da co bang chinh thi bo bang thong ke tho (count/min/max)
            tables.pop("stats", None)
        parts += [md_table(v, lang) for v in tables.values()]
        for ch in item.get("chunks") or []:
            excerpt = ch["text"][:300].rstrip() + ("…" if len(ch["text"]) > 300 else "")
            parts.append(f"**{ch['heading']}** [{ch['id']}]\n{excerpt}")
    parts += ev.get("tables") or []
    what, avail = T.missing_parts(results, lang)
    if any(r.get("missing") for r in results):
        parts.append(("Chưa có dữ liệu: " if lang == "vi" else "Missing data: ") + what + "." + avail)
    src = sources_block(ev["sources"], None, lang)
    return "\n\n".join(p for p in parts + [src] if p)
