"""Tim cac cum tu chi thuc the trong ca cau hoi (PLAN - Entity Resolution + Admission Tool (v1), muc 2.4).

Chi TIM cum tu, khong goi resolve() (E7): Router (Tuan 4) quyet dinh cum nao dua vao tham so nao.

  1. Ma (IT1, IT-E10, SOICT, THPT...): ma co chu so/gach noi khop KHONG phan biet hoa/thuong;
     ma toan chu cai (SOICT, THPT, DGTD) phan biet hoa/thuong — "sem" khong phai ma SEM
  2. Alias viet tat (BA, SIE, TSA): khop tren CAU GOC, phan biet hoa/thuong (E8: "ba nam" != "BA")
  3. Ten va alias con lai (>= 4 ky tu): khop tren cau da chuan hoa, nguyen tu
  Cum dai thang truoc, khong chong lan (E9: "Ky thuat O to" la mot cum).
"""

import re
import unicodedata
from dataclasses import dataclass

from app.entity_resolution.index import AliasIndex

MIN_PHRASE_LEN = 4
YEAR_RE = re.compile(r"(?<!\d)(20\d\d)(?!\d)")


@dataclass(frozen=True)
class Mention:
    text: str                       # cum goc trong cau hoi
    start: int
    end: int
    entity_types: frozenset[str]    # cac loai thuc the khoa nay co the tro toi


@dataclass
class ScanResult:
    mentions: list[Mention]
    years: list[int]


def _normalized_with_map(text: str) -> tuple[str, list[int]]:
    """Giong normalize() nhung giu vi tri: out[i] ung voi ky tu goc text[pos[i]]."""
    out, pos = [], []
    for i, ch in enumerate(text):
        base = unicodedata.normalize("NFD", ch.lower().replace("đ", "d"))
        base = "".join(c for c in base if unicodedata.category(c) != "Mn")
        c = base if len(base) == 1 and ("a" <= base <= "z" or "0" <= base <= "9") else " "
        if c == " " and (not out or out[-1] == " "):
            continue
        out.append(c)
        pos.append(i)
    return "".join(out), pos


class Scanner:
    """Dung mot lan tu AliasIndex (bien dich regex), goi scan() cho tung cau hoi."""

    def __init__(self, idx: AliasIndex) -> None:
        exact_codes, ci_codes, abbrevs = {}, {}, {}
        self.phrases: dict[str, frozenset[str]] = {}
        for key, entries in idx.exact.items():
            for e in entries:
                if e.kind == "code":
                    target = ci_codes if re.search(r"[\d\-_.]", e.text) else exact_codes
                    # "ITE10" / "ite10": nguoi dung hay bo gach noi trong ma
                    for form in {e.text, e.text.replace("-", "")}:
                        target.setdefault(form, set()).add(e.entity_type)
                elif e.kind == "abbrev":
                    abbrevs.setdefault(e.text, set()).add(e.entity_type)
            types = frozenset(e.entity_type for e in entries if e.kind not in ("code", "abbrev"))
            if types and len(key) >= MIN_PHRASE_LEN:
                self.phrases[key] = types
        self.case_sensitive = {**exact_codes, **abbrevs}
        self.case_insensitive = ci_codes
        self._cs_re = self._compile(self.case_sensitive, 0)
        self._ci_re = self._compile(self.case_insensitive, re.IGNORECASE)
        self._ci_lookup = {k.lower(): v for k, v in ci_codes.items()}

    @staticmethod
    def _compile(words: dict, flags: int) -> re.Pattern | None:
        if not words:
            return None
        alts = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        return re.compile(rf"(?<![\w-])(?:{alts})(?![\w-])", flags)

    def scan(self, question: str) -> ScanResult:
        spans: list[tuple[int, int, frozenset[str]]] = []
        if self._cs_re:
            spans += [(m.start(), m.end(), frozenset(self.case_sensitive[m.group()]))
                      for m in self._cs_re.finditer(question)]
        if self._ci_re:
            spans += [(m.start(), m.end(), frozenset(self._ci_lookup[m.group().lower()]))
                      for m in self._ci_re.finditer(question)]

        qn, pos = _normalized_with_map(question)
        padded = f" {qn} "
        for key, types in self.phrases.items():
            start = padded.find(f" {key} ")
            while start != -1:
                a, b = start, start + len(key) - 1          # chi so trong qn (padded lech 1)
                spans.append((pos[a], pos[b] + 1, types))
                start = padded.find(f" {key} ", start + 1)

        chosen: list[tuple[int, int, frozenset[str]]] = []
        for s in sorted(spans, key=lambda s: (-(s[1] - s[0]), s[0])):
            if all(s[1] <= c[0] or s[0] >= c[1] for c in chosen):
                chosen.append(s)
        mentions = [Mention(question[a:b], a, b, t) for a, b, t in sorted(chosen)]
        years = sorted({int(y) for y in YEAR_RE.findall(question)})
        return ScanResult(mentions, years)
