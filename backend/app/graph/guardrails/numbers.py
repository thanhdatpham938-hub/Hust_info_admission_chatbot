"""Kiem so trong cau tra loi (PLAN - Synthesizer (v1), muc 4.1; AC5).

Moi so trong cau tra loi phai co trong du lieu tool (hoac la nam / diem nguoi dung tu neu khi xin tu van).
Dau phay / dau cham mo ho giua hai ngon ngu ("82,10" vi = "82.10" en; "26.000.000" vi = "26,000,000" en) nen moi so
thu CA HAI cach doc, mot cach khop la dat. "26 triệu" / "26 million" nhan them 10^6.
"""

import re
from collections.abc import Iterable

NUM = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)*)(?![\w])")
SCALE = re.compile(r"^\s*(triệu|tr\b|million|tỷ|billion|nghìn|ngàn|thousand)", re.I)
SCALES = {"triệu": 1e6, "tr": 1e6, "million": 1e6, "tỷ": 1e9, "billion": 1e9, "nghìn": 1e3, "ngàn": 1e3,
          "thousand": 1e3}
CITATION = re.compile(r"\[\d+\]")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)
URL = re.compile(r"https?://\S+")
SMALL_INT_MAX = 10       # so dem trong cau ("3 phuong thuc", "2 bang") khong bat buoc co trong du lieu


def readings(token: str) -> set[float]:
    """Moi cach doc hop ly cua mot chuoi so."""
    seps = [c for c in token if c in ".,"]
    if not seps:
        return {float(token)}
    out = set()
    parts = re.split(r"[.,]", token)
    if len(seps) == 1:
        a, b = parts
        out.add(float(f"{a}.{b}"))                          # dau la thap phan
        if len(b) == 3:
            out.add(float(a + b))                           # dau la phan cach nghin
        return out
    last = token[max(token.rfind("."), token.rfind(","))]
    if all(len(p) == 3 for p in parts[1:]):
        out.add(float("".join(parts)))                      # 26.000.000 / 26,000,000
    if len(set(seps)) == 2 and seps[-1] == last:            # 1.234,5 hoac 1,234.5
        out.add(float("".join(parts[:-1]) + "." + parts[-1]))
    return out or {float("".join(parts))}


def extract(text: str) -> list[tuple[str, set[float]]]:
    """[(chuoi goc, cac gia tri co the)] — bo [n], dau dong danh sach, URL."""
    text = URL.sub(" ", CITATION.sub(" ", LIST_MARKER.sub(" ", text)))
    out = []
    for m in NUM.finditer(text):
        vals = readings(m.group(1))
        sc = SCALE.match(text[m.end():])
        if sc:
            k = SCALES[sc.group(1).lower()]
            vals = vals | {v * k for v in vals}
        out.append((m.group(1), vals))
    return out


def numbers_in(obj) -> set[float]:
    """Moi so o BAT KY DAU trong du lieu (so, va so nam trong chuoi: "4 - 5,5 năm", so trang, so Dieu)."""
    found: set[float] = set()

    def walk(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, int | float):
            found.add(float(x))
            found.add(abs(float(x)))         # chenh lech -0,36: "IT1 cao hon 0,36" la dung (PLAN Sua loi, buoc 1)
        elif isinstance(x, str):
            for _, vals in extract(x):
                found.update(vals)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list | tuple):
            for v in x:
                walk(v)
    walk(obj)
    return found


def _close(a: float, pool: Iterable[float]) -> bool:
    return any(abs(a - b) <= max(1e-6, 1e-9 * abs(b)) or round(a, 2) == round(b, 2) for b in pool)


def question_numbers(question: str, advice: bool) -> set[float]:
    """So duoc lay tu cau hoi (va lo hong R159): chi NAM; them diem nguoi dung tu neu khi xin tu van."""
    vals = set()
    for _, vs in extract(question):
        for v in vs:
            if v.is_integer() and 1990 <= v <= 2100:
                vals.add(v)
            elif advice:
                vals.add(v)
    return vals


def strange_numbers(answer: str, allowed: set[float]) -> list[str]:
    """So trong cau tra loi khong co trong tap duoc phep (bo qua so dem nho)."""
    bad = []
    for raw, vals in extract(answer):
        if any(v.is_integer() and 0 <= v <= SMALL_INT_MAX for v in vals):
            continue
        if not any(_close(v, allowed) for v in vals):
            bad.append(raw)
    return bad
