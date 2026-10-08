"""Tra mot cum tu nguoi dung go ra ma thuc the — 4 quy tac PRD 10.3, dung thu tu
(PLAN - Entity Resolution + Admission Tool (v1), muc 2.3):

  B1 loc nam (theo program_years cua MA nganh, khong theo cot year cua alias — E1)
  B2 khop chinh xac  -> co ket qua sau loc nam thi DUNG
  B3a chuoi con      -> chi khi B2 truot; bo ma va alias abbrev
  B3b fuzzy          -> chi khi B3a truot; rapidfuzz fuzz.ratio theo cua so tu (window_ratio)
  doc resolution: unique -> 1 ma; clarify -> KHONG tu chon; group -> cac nganh cua nhom
"""

from dataclasses import dataclass, field
from typing import Literal

from rapidfuzz import fuzz, process

from app.entity_resolution.index import AliasIndex, Entry
from app.entity_resolution.normalize import normalize

MIN_SUBSTRING_LEN = 3       # E5: "co" la chuoi con cua hang chuc ten nganh
MIN_FUZZY_LEN = 4
FUZZY_CUTOFF = 85           # E5: nguong khoi diem, chinh sau khi do tren bo 120 cau
FUZZY_MARGIN = 10           # top-1 hon top-2 it nhat chung nay diem moi TU CHON 1 nganh (AC8)
CLOSE_MARGIN = 5            # ung vien cach top-1 duoi chung nay diem moi dua vao danh sach hoi lai
MAX_UNDECLARED = 3          # anh chot: ung vien KHONG khai bao (chuoi con/fuzzy) cat con 3
# Chu dau chung bo khoi CA HAI phia truoc khi cham fuzzy. Do 2026-10-09: "truong y" duoc 86 diem voi moi
# "truong ..." (chi nho chu "truong"); "truong luat" bi doan thanh Truong Vat lieu ("luat" ~ "lieu").
GENERIC_LEADS = {"truong", "khoa", "vien", "nganh"}


def core(text: str) -> str:
    """'truong vat lieu' -> 'vat lieu'; 'khoa hoc may tinh' -> 'hoc may tinh' (ap dung deu hai phia nen nhat quan)."""
    tokens = text.split()
    while len(tokens) > 1 and tokens[0] in GENERIC_LEADS:
        tokens = tokens[1:]
    return " ".join(tokens) if tokens and tokens[0] not in GENERIC_LEADS else ""

Status = Literal["unique", "clarify", "group", "not_found"]
MatchedBy = Literal["exact", "substring", "fuzzy"]


@dataclass
class Resolution:
    mention: str
    entity_type: str
    status: Status
    codes: list[str] = field(default_factory=list)      # unique: 1 ma; clarify: cac ung vien; group: thanh vien
    matched_by: MatchedBy | None = None
    group_code: str | None = None
    other_years: dict[str, list[int]] = field(default_factory=dict)   # khop duoc nhung bi B1 loai


def window_ratio(query: str, key: str, **_) -> float:
    """fuzz.ratio cua `query` voi doan TU lien tiep tot nhat trong `key` (dai n-1..n+1 tu).

    Vi sao khong dung partial_ratio/WRatio: do 2026-10-07, ca hai cho "hoa hoc" 100 diem voi cau go
    "Khoa hoc may tihn" (khop nham theo ky tu). Con fuzz.ratio ca chuoi thi truot khi cum go sai chi
    la MOT PHAN cua ten dai ("khoa hoc may tihn" vs "cntt khoa hoc may tinh": 82). So theo cua so tu
    giu duoc ca hai. Cum 1 tu chi so ca chuoi: "tinh" khong duoc khop "tin" trong "toan tin".
    """
    best = fuzz.ratio(query, key)
    qn, kt = len(query.split()), key.split()
    if qn < 2 or len(kt) <= qn:
        return best
    for n in (qn - 1, qn, qn + 1):
        for i in range(len(kt) - n + 1):
            best = max(best, fuzz.ratio(query, " ".join(kt[i:i + n])))
    return best


def _types_for(entity_type: str) -> set[str]:
    # Hoi nganh thi xet ca nhom nganh, de "Elitech" ra nhom
    return {"program", "program_group"} if entity_type == "program" else {entity_type}


def resolve(mention: str, entity_type: str, idx: AliasIndex, years: list[int] | None = None) -> Resolution:
    ys = set(years) if years else {idx.latest_year}
    key = normalize(mention)
    res = Resolution(mention, entity_type, "not_found")
    if not key:
        return res
    types = _types_for(entity_type)

    def alive(e: Entry) -> bool:
        return e.entity_type != "program" or bool(idx.valid_years[e.code] & ys)

    def stage(hits: list[tuple[Entry, float]]) -> list[tuple[Entry, float]]:
        hits = [(e, s) for e, s in hits if e.entity_type in types]
        ok = [(e, s) for e, s in hits if alive(e)]
        if hits and not ok and not res.other_years:
            res.other_years = {e.code: sorted(idx.valid_years[e.code]) for e, _ in hits}
        return ok

    # B2 khop chinh xac
    hits = stage([(e, 100.0) for e in idx.exact.get(key, [])])
    if hits:
        return _decide(res, hits, "exact", idx, ys)
    # Khop CHINH XAC mot ma nhung ma do khong tuyen nam dang hoi -> nguoi dung go dung ten that, khong go
    # sai. Van cho B3a (chuoi con: "Accounting" -> "Accounting (Advanced Program)" EM-E17) nhung KHONG doan
    # bang fuzzy: do 2026-10-08, "Tieng Han KH&CN" nam 2025 bi fuzzy doan sang FL3 (Tieng Trung KH&CN).
    exact_but_closed = bool(res.other_years)

    sub_index = idx.substring_keys()
    # B3a chuoi con (nguoi dung go mot phan cua ten/alias) — khop NGUYEN TU: "tinh" khong duoc
    # khop vao giua tu khac; go thieu chu ("kinh doan") de B3b fuzzy bat
    if len(key) >= MIN_SUBSTRING_LEN:
        padded = f" {key} "
        hits = stage([(e, fuzz.ratio(key, k)) for k, es in sub_index.items() if padded in f" {k} " for e in es])
        if hits:
            return _decide(res, hits, "substring", idx, ys)

    # B3b fuzzy (go sai chinh ta) — cham tren phan loi sau khi bo chu dau chung (GENERIC_LEADS)
    qcore = core(key)
    if len(qcore) >= MIN_FUZZY_LEN and not exact_but_closed:
        by_core: dict[str, list[str]] = {}
        for k in sub_index:
            if c := core(k):
                by_core.setdefault(c, []).append(k)
        found = process.extract(qcore, list(by_core), scorer=window_ratio, score_cutoff=FUZZY_CUTOFF, limit=None)
        hits = stage([(e, score) for c, score, _ in found for k in by_core[c] for e in sub_index[k]])
        if hits:
            return _decide(res, hits, "fuzzy", idx, ys)

    return res


def _decide(res: Resolution, hits: list[tuple[Entry, float]], how: MatchedBy, idx: AliasIndex,
            ys: set[int]) -> Resolution:
    res.matched_by = how
    res.other_years = {}
    groups = [e for e, _ in hits if e.resolution == "group"]
    if groups and groups[0].entity_type == "program_group":
        g = groups[0].code
        res.status, res.group_code = "group", g
        res.codes = sorted(c for c in idx.group_members[g] if idx.valid_years[c] & ys)
        return res
    if groups:
        # Loai khac (vd chung chi TOEIC = ca 4 ky nang): "group" = dung TAT CA ma da khai bao
        res.status, res.codes = "group", sorted({e.code for e in groups})
        return res

    best: dict[str, float] = {}
    for e, score in hits:
        best[e.code] = max(best.get(e.code, 0.0), score)
    ranked = sorted(best, key=lambda c: (-best[c], c))

    if len(ranked) == 1:
        res.status, res.codes = "unique", ranked
    elif how == "exact":
        # E4: nhieu ma cung mot khoa -> luon hoi lai; anh chot: alias da khai bao thi liet ke DU
        res.status, res.codes = "clarify", sorted(ranked)
    elif how == "fuzzy" and best[ranked[0]] - best[ranked[1]] >= FUZZY_MARGIN:
        res.status, res.codes = "unique", ranked[:1]
    elif how == "fuzzy":
        # Chi hoi lai giua cac ung vien SAT diem top-1 (AC8): do 2026-10-08, "ky thuat oto" keo them
        # ME-E1 diem thap hon han vao danh sach hoi lai TE1/TE-E2
        # ("ky thuat oto": TE1/TE-E2 96 diem, ME-E1 87 -> chi hoi TE1/TE-E2)
        close = [c for c in ranked if best[ranked[0]] - best[c] < CLOSE_MARGIN]
        res.status, res.codes = "clarify", close[:MAX_UNDECLARED]
    else:
        res.status, res.codes = "clarify", ranked[:MAX_UNDECLARED]
    return res
