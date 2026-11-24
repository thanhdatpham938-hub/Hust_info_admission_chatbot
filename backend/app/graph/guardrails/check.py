"""verify(): kiem cau tra loi bang CODE (PLAN - Synthesizer (v1), muc 4). Khong LLM.

Bat duoc: so khong co trong du lieu, [n] tro nguon khong ton tai, dung van ban ma khong trich dan, hoc phi thieu don
vi / nam. KHONG bat duoc: so dung nhung gan nham cho, hieu sai nghia van ban (xem PLAN Synthesizer, trao doi
2026-10-20) — phan do do bang tay o S5 va LLM judge Tuan 6.
"""

import re

from app.graph.guardrails.numbers import strange_numbers
from app.graph.render import sources_block

CITE = re.compile(r"\[(\d+)\]")
MONEY = re.compile(r"(triệu|nghìn|đồng|vnđ|vnd|million|dong)", re.I)
UNIT = re.compile(r"(/\s*năm|/\s*học kỳ|mỗi năm|mỗi học kỳ|một năm|một học kỳ|năm học|học kỳ|per year|per semester|"
                  r"/\s*year|/\s*semester|a year|a semester|per academic year|/\s*tín chỉ|per credit)", re.I)
YEAR = re.compile(r"(19|20)\d{2}")
# Buoc 2 (PLAN Sua loi): cau tieng Anh ma > 20% so tu co dau tieng Viet -> viet lai. Nguong 20% chua cho ten nganh,
# ten van ban tieng Viet (duoc phep xuat hien); phan trong ngoac / ngoac kep va ten da biet bi bo truoc khi dem.
VI_RATIO_MAX = 0.20
VI_MIN_WORDS = 8
VI_LETTERS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
WORD = re.compile(r"[^\W\d_]+")
QUOTED = re.compile(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”|\*\*[^*]*\*\*")


def vietnamese_ratio(text: str, known: list[str] = ()) -> tuple[float, int]:
    """(ti le tu co dau tieng Viet, so tu duoc dem) sau khi bo ten da biet, phan trong ngoac, bang, URL."""
    for name in sorted({k for k in known if k}, key=len, reverse=True):
        text = text.replace(name, " ")
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("|"))
    text = QUOTED.sub(" ", re.sub(r"https?://\S+", " ", text))
    words = WORD.findall(text)
    if not words:
        return 0.0, 0
    vi = sum(1 for w in words if VI_LETTERS & set(w.lower()))
    return vi / len(words), len(words)


def known_names(ev: dict) -> list[str]:
    """Ten duoc phep giu tieng Viet: ten van ban, ten nganh tieng Viet."""
    p = ev["payload"]
    out = [s["title"] for s in ev["sources"]]
    out += [ch.get("document") or "" for it in p["evidence"] for ch in it.get("chunks") or []]
    out += [v.get("vi") or "" for v in (p.get("program_names") or {}).values()]
    return out


def verify(text: str, ev: dict) -> tuple[str, list[str], set[int]]:
    """Tra (cau tra loi da xoa [n] sai, danh sach loi can viet lai, cac nguon duoc trich)."""
    valid = {s["n"] for s in ev["sources"]}
    cited = {int(n) for n in CITE.findall(text)}
    for n in cited - valid:                                 # [n] sai: xoa, khong tinh la loi (muc 4.2)
        text = text.replace(f"[{n}]", "")
    used = cited & valid
    issues = []
    rag_ids = {c["id"] for it in ev["payload"]["evidence"] for c in it.get("chunks") or []}
    if ev["rag_used"] and not used & rag_ids:
        issues.append("Thông tin lấy từ văn bản phải ghi trích dẫn [n] ngay sau câu, với n là id của đoạn văn bản "
                      "trong evidence.")
    bad = strange_numbers(text, set(ev["allowed"]))
    if bad:
        issues.append("Các số sau KHÔNG có trong dữ liệu, phải bỏ hoặc sửa đúng theo evidence: " + ", ".join(bad))
    if ev["tuition_used"] and MONEY.search(text) and not (UNIT.search(text) and YEAR.search(text)):
        issues.append("Học phí phải ghi rõ đơn vị (/năm hoặc /học kỳ) và năm áp dụng.")
    if ev["payload"].get("language") == "en":
        ratio, n = vietnamese_ratio(text, known_names(ev))
        if n >= VI_MIN_WORDS and ratio > VI_RATIO_MAX:
            issues.append("The question is in English: write the WHOLE answer in English (keep only program names "
                          "and document titles in Vietnamese).")
    return text, issues, used


def finalize(text: str, ev: dict, used: set[int], language: str) -> tuple[str, list[dict]]:
    """Ghep cau tra loi cuoi: van ban LLM + bang code dung + khoi nguon (dung tu metadata, PRD 12)."""
    keep = used | set(ev.get("table_source_ids") or [])
    citations = [s for s in ev["sources"] if s["n"] in keep]
    parts = [text.strip(), *(ev.get("tables") or []), sources_block(ev["sources"], keep, language)]
    return "\n\n".join(p for p in parts if p), citations
