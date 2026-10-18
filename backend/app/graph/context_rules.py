"""Quy tac ngu canh nhieu luot (PRD 14) — PLAN - State va Context Rules (v1), muc 3-4.

Ham thuan: khong LLM, khong DB, khong sua dau vao (tra ban moi). Router chi bao `refers_to_context`,
`pick_status`, `picked`; viec dien tham so tu ngu canh do code o day lam de AC6 do duoc.

  merge_context   C1-C3: dien o trong cua lenh goi tu ngu canh luot truoc
  pick_choice     C4 duong tat khong LLM: nut bam / khop chu, chi khi tin nhan khong con phan thua
  merge_pick      C4 khi Router xu ly cau chon: khoa ma da chon, ghep voi lenh goi dang cho
  build_pending   dung cau hoi lai tu ket qua tool `ambiguous`
  update_context  save_context: gom ma da xac nhan, dat/xoa pending
  register_unclear  dem `unclear` lien tiep, den gioi han thi tha pending
"""

import copy
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.entity_resolution.normalize import compact, normalize
from app.graph.state import MAX_UNCLEAR, ConvContext, Pending, ToolCall
from app.tools.certificate import cohort_number

MAX_ENTITIES = 3
LIST_CONCEPTS = ("programs", "years", "methods", "faculties")
ALL_CONCEPTS = (*LIST_CONCEPTS, "cohort")
ENTITY_CONCEPTS = ("programs", "faculties")     # C3: khac tool chi mang nganh / Truong (PRD 14 dong 2)

# ---------------------------------------------------------------- 4.1 khai niem -> tham so tung tool
# (ten tham so, nhan nhieu gia tri?). Khong co dong = tool khong co tham so do -> khong dien.
PARAMS: dict[str, dict[str, tuple[str, bool]]] = {
    "admission_scores": {"programs": ("programs", True), "years": ("years", True), "methods": ("methods", True)},
    "list_programs": {"programs": ("programs", True), "years": ("years", True), "methods": ("method", False),
                      "faculties": ("faculty", False)},
    "program_info": {"programs": ("programs", True), "years": ("years", True)},
    "tuition_fees": {"programs": ("programs", True), "years": ("years", True)},
    "certificate_lookup": {"programs": ("programs", True), "years": ("year", False), "cohort": ("cohort", False)},
    "university_info": {"programs": ("programs", True), "years": ("year", False),
                        "faculties": ("faculties", True)},
    "rag_search": {"programs": ("programs", True), "years": ("years", True), "faculties": ("faculties", True),
                   "cohort": ("cohort", False)},
}

# entity_type cua Candidate/Resolved -> khai niem/tham so can thay khi nguoi dung chon
FIELD_OF_ENTITY = {"program": "programs", "program_group": "programs", "faculty": "faculties",
                   "method": "methods", "certificate": "certificate", "cohort": "cohort", "purpose": "purpose"}
# cum T5 tu dat ("khoá học"), khong nam trong tham so -> gan thang vao lenh goi da hoi
SET_ON_ASKING_CALL = {"cohort", "purpose"}


def _blank(v) -> bool:
    return v is None or v == "" or v == []


def _as_list(v) -> list:
    if _blank(v):
        return []
    return list(v) if isinstance(v, list | tuple) else [v]


def concept_value(call: ToolCall, concept: str):
    """Doc gia tri khai niem tu lenh goi, chuan ve list (cohort: chuoi hoac None)."""
    spec = PARAMS.get(call["tool"], {}).get(concept)
    if not spec:
        return None if concept == "cohort" else []
    v = call["args"].get(spec[0])
    if concept == "cohort":
        return None if _blank(v) else v
    return _as_list(v)


def _fill(call: ToolCall, values: Mapping, concepts: Iterable[str]) -> ToolCall:
    """Dien o TRONG cua lenh goi tu `values`; khong bao gio ghi de gia tri cau hoi da neu."""
    out = copy.deepcopy(call)
    spec = PARAMS.get(out["tool"], {})
    for c in concepts:
        if c not in spec or _blank(values.get(c)):
            continue
        param, multi = spec[c]
        if not _blank(out["args"].get(param)):
            continue
        v = values[c]
        if c == "cohort":
            out["args"][param] = v
        elif multi:
            out["args"][param] = list(v)
        elif len(v) == 1:                 # tool nhan 1 gia tri ma ngu canh co nhieu -> khong doan (M12)
            out["args"][param] = v[0]
    return out


# ---------------------------------------------------------------- C1-C3
def merge_context(calls: list[ToolCall], refers: bool, ctx: ConvContext) -> list[ToolCall]:
    """C1: khong tham chieu -> khong mang gi. C2: cung `last_tool` -> dien moi khai niem con trong.
    C3: khac tool -> chi nganh va Truong/Khoa."""
    if not refers:
        return [copy.deepcopy(c) for c in calls]
    last_tool = ctx.get("last_tool")
    return [_fill(c, ctx, ALL_CONCEPTS if c["tool"] == last_tool else ENTITY_CONCEPTS) for c in calls]


# ---------------------------------------------------------------- pending
def build_pending(calls: list[ToolCall], results: list[dict]) -> Pending | None:
    """Lay cum mo ho DAU TIEN (muc 2 (3)); ket qua lenh khac giu vao `done` de khoi chay lai."""
    for i, r in enumerate(results):
        if r.get("status") != "ambiguous" or not r.get("clarifications"):
            continue
        cl = r["clarifications"][0]
        etype = cl["candidates"][0]["entity_type"] if cl["candidates"] else "program"
        kept = []
        for j, (c, rj) in enumerate(zip(calls, results)):
            item = ToolCall(tool=c["tool"], args=copy.deepcopy(c["args"]))
            item["done"] = None if (j == i or rj.get("status") == "ambiguous") else rj
            kept.append(item)
        return Pending(calls=kept, index=i, mention=cl["mention"], field=FIELD_OF_ENTITY.get(etype, "programs"),
                       entity_type=etype, candidates=[{"code": x["code"], "name": x["name"]} for x in cl["candidates"]],
                       retries=0)
    return None


def _replace_in_list(values: list, mention: str, codes: list[str]) -> tuple[list, bool]:
    key = normalize(mention)
    out, hit = [], False
    for v in values:
        if isinstance(v, str) and normalize(v) == key:
            out += [c for c in codes if c not in out]
            hit = True
        elif v not in out:
            out.append(v)
    return out, hit


def substitute(pending: Pending, codes: list[str]) -> list[ToolCall]:
    """Thay cum mo ho bang ma da chon trong moi lenh goi (giu vi tri, giu phan tu khac). Lenh goi nao doi
    tham so thi bo `done` de chay lai."""
    out = []
    for i, c in enumerate(pending["calls"]):
        new = ToolCall(tool=c["tool"], args=copy.deepcopy(c["args"]), done=c.get("done"))
        changed = False
        if pending["field"] in SET_ON_ASKING_CALL:
            if i == pending["index"]:
                new["args"][pending["field"]] = codes[0]
                changed = True
        else:
            spec = PARAMS.get(c["tool"], {}).get(pending["field"])
            param = spec[0] if spec else pending["field"]          # certificate: tham so cung ten
            v = new["args"].get(param)
            if isinstance(v, list):
                new["args"][param], changed = _replace_in_list(v, pending["mention"], codes)
            elif isinstance(v, str) and normalize(v) == normalize(pending["mention"]):
                new["args"][param], changed = codes[0], True
        if changed:
            new["done"] = None
        out.append(new)
    return out


# ---------------------------------------------------------------- 4.3 pick_choice
# Tu dem: bo di ma tin nhan khong con gi -> chon xong, khong can Router (4.3b)
# Tieng Anh (PLAN - Router (v1) muc 10.2, R1c): nguoi hoi tieng Anh tra loi cau hoi lai bang tieng Anh
FILLERS = set("""nhe nha a oi cai he nganh chuong trinh chon lay di thoi so thu minh em toi
cho la nay do ay kia voi va vay the ok oke uh u um vang da
one please i d like would want choose pick take option program yes""".split())
ALL_PHRASES = ("ca hai", "ca 2", "ca ba", "ca 3", "tat ca", "lay het", "both", "all of them", "all")
# Khong co "nhat" dung rieng: "Việt Nhật" se thanh "thu nhat". Them nua, tu nao nam trong TEN lua chon thi
# khong duoc tinh la so thu tu (xem _match_ordinal).
ORDINALS = {"1": 1, "mot": 1, "thu nhat": 1, "dau tien": 1, "dau": 1, "2": 2, "hai": 2, "3": 3, "ba": 3,
            "4": 4, "5": 5, "6": 6, "7": 7,
            "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}
LAST_WORDS = ("cuoi cung", "cuoi", "last")
MAX_ORDINAL_WORDS = 6               # buoc 4: chi xet so thu tu khi tin nhan ngan
# 5b: tu dong nghia -> program_group_code (bang `programs`). Khong co "chat luong cao" (trung nghia PFIEV/ELITECH)
GROUP_SYNONYMS = {"chuan": "chuan", "dai tra": "chuan", "thuong": "chuan", "tien tien": "elitech",
                  "elitech": "elitech", "pfiev": "pfiev", "viet phap": "pfiev", "lien ket": "lien_ket",
                  "hop tac quoc te": "lien_ket",
                  "standard": "chuan", "regular": "chuan", "advanced": "elitech", "joint program": "lien_ket"}
# 5a: tu chung khong dung de phan biet lua chon
NAME_STOPWORDS = {"va", "voi", "cua", "cac", "dh", "dhcn", "ct", "chuong", "trinh", "nganh", "ky", "thuat",
                  "hop", "tac", "chlb"}


def _has_phrase(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


@dataclass
class PickOutcome:
    """Ket qua duong tat. `calls` co gia tri = chon xong; `too_many` = "tat ca" ma danh sach > 3."""
    calls: list[ToolCall] | None = None
    too_many: bool = False
    codes: list[str] = field(default_factory=list)


def _match_codes(tokens: list[str], cands: list[dict]) -> tuple[list[str], set[str]]:
    """Buoc 1: n-gram (1-3 tu) cua tin nhan trung compact(ma). "te e2", "TE-E2", "tee2" deu ra TE-E2."""
    by_key = {compact(c["code"]): c["code"] for c in cands}
    hits, used = [], set()
    for n in (3, 2, 1):
        for i in range(len(tokens) - n + 1):
            key = "".join(tokens[i:i + n])
            if key in by_key and by_key[key] not in hits:
                hits.append(by_key[key])
                used.update(tokens[i:i + n])
    return hits, used


def _match_cohort(text: str, cands: list[dict]) -> list[str]:
    """Buoc 2: "K70", "khoá 69", "nam 2025" -> K70- / K71+ (cung cach hieu voi T5)."""
    n = cohort_number(text)
    if n is None:
        return []
    want = "K71+" if n >= 71 else "K70-"
    return [want] if want in {c["code"] for c in cands} else []


def _match_ordinal(text: str, tokens: list[str], cands: list[dict]) -> tuple[list[str], set[str]]:
    """Buoc 4: "cái thứ hai", "số 2", "đầu tiên", "cái cuối"; chi khi tin nhan ngan va DUNG MOT so."""
    if len(tokens) > MAX_ORDINAL_WORDS:
        return [], set()
    name_words = {w for c in cands for w in normalize(c["name"]).split()}
    found: dict[int, set[str]] = {}
    for w in LAST_WORDS:
        if _has_phrase(text, w) and not set(w.split()) & name_words:
            found[len(cands)] = set(w.split())
            break
    for w, k in ORDINALS.items():
        if _has_phrase(text, w) and not set(w.split()) & name_words:
            found.setdefault(k, set()).update(w.split())
    if len(found) != 1:
        return [], set()
    k, used = next(iter(found.items()))
    return ([cands[k - 1]["code"]], used) if 1 <= k <= len(cands) else ([], set())


def _match_distinct_words(tokens: list[str], cands: list[dict]) -> list[str]:
    """Buoc 5a: tu CHI co trong ten mot lua chon (vd "Việt Nhật" -> IT-E6). Dung mot lua chon moi nhan."""
    words = [set(normalize(c["name"]).split()) - NAME_STOPWORDS for c in cands]
    msg = set(tokens)
    hits = []
    for i, c in enumerate(cands):
        others = set().union(*(w for j, w in enumerate(words) if j != i))
        if (words[i] - others) & msg:
            hits.append(c["code"])
    return hits if len(hits) == 1 else []


def _match_group(text: str, cands: list[dict], groups: Mapping[str, str]) -> tuple[list[str], set[str]]:
    """Buoc 5b: "hệ chuẩn" / "Elitech" -> nhom chuong trinh (cot programs.program_group_code)."""
    for phrase, g in GROUP_SYNONYMS.items():
        if _has_phrase(text, phrase):
            hits = [c["code"] for c in cands if groups.get(c["code"]) == g]
            return (hits, set(phrase.split())) if len(hits) == 1 else ([], set())
    return [], set()


def pick_choice(text: str, pending: Pending, choice: str | None = None,
                groups: Mapping[str, str] | None = None) -> PickOutcome:
    """Duong tat khong LLM (4.3, 4.3b). Tra PickOutcome rong (calls=None) = de Router xu ly ca cau."""
    cands = pending["candidates"]
    valid = {c["code"] for c in cands}
    if choice and choice in valid:                                       # buoc 0: nut bam
        return PickOutcome(calls=substitute(pending, [choice]), codes=[choice])

    text_n = normalize(text)
    tokens = text_n.split()
    codes, used = _match_codes(tokens, cands)                            # buoc 1
    if not codes and pending["entity_type"] == "cohort":                 # buoc 2
        codes = _match_cohort(text, cands)
        used = {t for t in tokens if t in ("k", "khoa", "nam") or re.fullmatch(r"k?\d+", t)}
    if not codes:                                                        # buoc 3: "cả hai" / "tất cả"
        phrase = next((w for w in ALL_PHRASES if _has_phrase(text_n, w)), None)
        if phrase:
            if len(cands) > MAX_ENTITIES:
                return PickOutcome(too_many=True)
            codes, used = [c["code"] for c in cands], set(phrase.split())
    if not codes:                                                        # buoc 4
        codes, used = _match_ordinal(text_n, tokens, cands)
    if not codes:                                                        # buoc 5a
        codes = _match_distinct_words(tokens, cands)
    if not codes and groups:                                             # buoc 5b
        codes, used = _match_group(text_n, cands, groups)
    if not codes or len(codes) > MAX_ENTITIES:
        return PickOutcome()
    codes = [c["code"] for c in cands if c["code"] in codes]            # theo thu tu hien thi cho nguoi dung

    # Chi tu trong ten lua chon DA chon moi tinh la "da dung": "Khoa học máy tính với Việt Nhật" khop IT-E6 nhung
    # "khoa hoc may tinh" la ten lua chon KHAC -> con phan thua -> Router chon ca hai (P015)
    name_words = {w for c in cands if c["code"] in codes for w in normalize(c["name"]).split()}
    leftover = [t for t in tokens if t not in used and t not in FILLERS and t not in name_words]
    if leftover:                                                         # con phan thua -> Router (4.3b)
        return PickOutcome()
    return PickOutcome(calls=substitute(pending, codes), codes=codes)


# ---------------------------------------------------------------- 4.3b merge_pick
def merge_pick(pending: Pending, picked: list[str], router_calls: list[ToolCall]) -> list[ToolCall] | None:
    """Router da xu ly ca cau chon. None = `picked` khong hop le -> coi nhu cau moi (C5).

    Xung dot 2: gia tri vua noi thang (nam/phuong thuc/khoa ap cho moi lenh goi goc co tham so do), o trong lay
                tu lenh cu; khac tool -> chi mang nganh / Truong.
    Xung dot 3: lenh goi goc LUON chay, them lenh goi moi, tong <= 3.
    Xung dot 4: dung lai `done` chi khi tham so giong het.
    Ma da chon bi KHOA: khong lenh goi nao bo duoc no; Router chi them nganh nguoi dung vua go.
    """
    valid = {c["code"] for c in pending["candidates"]}
    picked = list(dict.fromkeys(picked))
    if not picked or len(picked) > MAX_ENTITIES or any(p not in valid for p in picked):
        return None
    base = substitute(pending, picked)
    originals = [c["args"] for c in pending["calls"]]
    # Router co the chep lai cum mo ho -> thay luon, de luot chay lai khong hoi lai thanh vong lap
    news = [ToolCall(tool=c["tool"], args=copy.deepcopy(c["args"])) for c in router_calls]
    if pending["field"] not in SET_ON_ASKING_CALL:
        news = substitute(Pending(**{**pending, "calls": news, "index": -1}), picked)

    # gia tri nguoi dung vua noi (khong tinh nganh/Truong: hai cai nay gop, khong ghi de)
    stated: dict = {}
    for c in news:
        for concept in ("years", "methods", "cohort"):
            v = concept_value(c, concept)
            if not _blank(v) and concept not in stated:
                stated[concept] = v

    merged: list[ToolCall] = []
    used_news: set[int] = set()
    for b in base:
        out = copy.deepcopy(b)
        spec = PARAMS.get(out["tool"], {})
        for concept, v in stated.items():                                  # doi nam/phuong thuc/khoa
            if concept in spec:
                param, multi = spec[concept]
                if concept == "cohort" or multi:
                    out["args"][param] = v if concept == "cohort" else list(v)
                elif len(v) == 1:
                    out["args"][param] = v[0]
        same = next((k for k, n in enumerate(news) if k not in used_news and n["tool"] == out["tool"]), None)
        if same is not None:                                               # cung tool: gia tri vua noi thang
            used_news.add(same)
            for k, v in news[same]["args"].items():
                if _blank(v):
                    continue
                if isinstance(v, list) and isinstance(out["args"].get(k), list) and \
                        k in ("programs", "faculties"):                    # khoa ma da chon: gop, khong thay
                    out["args"][k] = list(dict.fromkeys(out["args"][k] + v))
                else:
                    out["args"][k] = v
        merged.append(out)

    carry = {c: concept_value(base[pending["index"]], c) for c in ENTITY_CONCEPTS}
    for k, n in enumerate(news):                                           # tool moi: chi mang nganh / Truong
        if k not in used_news:
            merged.append(_fill(n, carry, ENTITY_CONCEPTS))

    for c, orig in zip(merged, originals):                                 # xung dot 4
        if c.get("done") is not None and c["args"] != orig:
            c["done"] = None
    for c in merged[len(originals):]:
        c["done"] = None
    return merged[:MAX_ENTITIES]


# ---------------------------------------------------------------- 4.4 update_context
UpdateKind = Literal["answered", "clarify", "refused", "cancel"]


def _confirmed(results: list[dict], etypes: tuple[str, ...]) -> list[str]:
    """Ma tool da xac nhan (Resolved). Nhom nganh ra nhieu hon 3 ma thi khong luu (mang sang se thanh invalid)."""
    for r in results:
        if r.get("status") not in ("ok", "partial", "not_found"):
            continue
        codes = [c for x in r.get("resolved", []) if x["entity_type"] in etypes for c in x["codes"]]
        codes = list(dict.fromkeys(codes))
        if codes:
            return codes if len(codes) <= MAX_ENTITIES else []
    return []


def update_context(ctx: ConvContext, kind: UpdateKind, calls: Sequence[ToolCall] = (), results: Sequence[dict] = (),
                   intent: str | None = None, pending: Pending | None = None) -> ConvContext:
    """save_context. answered: ghi de tung o bang gia tri luot nay neu/xac nhan, o khong nhac thi GIU.
    clarify: dat pending moi, ngu canh giu nguyen. refused: khong doi gi (M10). cancel: chi bo pending."""
    out: ConvContext = copy.deepcopy(ctx)
    if kind == "refused":
        return out
    if kind == "cancel":
        out["pending"] = None
        return out
    if kind == "clarify":
        out["pending"] = pending
        out["last_intent"] = "CLARIFICATION_NEEDED"
        return out

    answered = [(c, r) for c, r in zip(calls, results) if r.get("status") in ("ok", "partial", "not_found")]
    new = {"programs": _confirmed([r for _, r in answered], ("program", "program_group")),
           "faculties": _confirmed([r for _, r in answered], ("faculty",)),
           "methods": _confirmed([r for _, r in answered], ("method",))}
    for c, _ in answered:                                  # nam/khoa: lay tu tham so (thu nguoi dung NOI ra)
        for concept in ("years", "cohort"):
            v = concept_value(c, concept)
            if concept not in new and not _blank(v):
                new[concept] = v
    for concept, v in new.items():
        if not _blank(v):
            out[concept] = v
    if answered:
        out["last_tool"] = answered[0][0]["tool"]
    out["last_intent"] = intent
    out["pending"] = None
    return out


def register_unclear(ctx: ConvContext) -> tuple[ConvContext, bool]:
    """Router xep `unclear` (4.3c). Tra (ngu canh moi, da_tha). Den MAX_UNCLEAR thi tha pending."""
    out: ConvContext = copy.deepcopy(ctx)
    p = out.get("pending")
    if not p:
        return out, False
    p["retries"] = p.get("retries", 0) + 1
    if p["retries"] >= MAX_UNCLEAR:
        out["pending"] = None
        return out, True
    return out, False
