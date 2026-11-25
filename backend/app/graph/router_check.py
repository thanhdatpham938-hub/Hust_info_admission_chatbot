"""Bo quet truoc Router (goi y) va kiem sau Router (PLAN - Sua loi sau chay thu Synthesizer (v1), buoc 3).

Nguyen tac: Router chi CHEP NGUYEN chu nguoi dung go; kien thuc ve truong nam o tu dien alias va code nay, khong day
them Router bang prompt (prompt da ~10.300 token, gpt-4o-mini bo sot quy tac trong danh sach dai).

  hint_line()  truoc khi goi LLM: dong "Tu dien nhan ra trong cau" (Scanner co san, vai mili giay)
  reconcile()  sau khi LLM tra loi: moi gia tri nganh / nhom chuong trinh / Truong-Khoa Router dien
     1. "ten (MA)" nguoi dung go ca ten lan ma          -> doi thanh MA (S01, S09)
     2. ten goi CHINH TRUONG ("Bach khoa", "HUST") o o Truong/Khoa / nhom -> bo loc (S04: ca truong)
     3. co trong cau (sau chuan hoa)                     -> giu
     4. KHONG co trong cau (Router tu dich / doan):
        bo quet tim duoc cum CUNG LOAI chua dung        -> thay bang cum do (S08: "PFIEV" -> "SIE")
        khong tim duoc                                   -> GIU nguyen (do 2026-10-21: bo thi R151 "CNTT" ->
                                                            "Cong nghe Thong tin" mat nganh, S39 "standard program"
                                                            -> "chuong trinh chuan" mat nhom; giu thi tool tu phan giai)
  fix_academic_years()  hoc phi "nam hoc 2026-2027" -> years = [2026] (nam hoc bat dau, S39)
"""

import re

from app.entity_resolution.index import AliasIndex
from app.entity_resolution.normalize import compact, normalize
from app.entity_resolution.scan import Mention, ScanResult

TYPE_LABEL = {"program": "ngành", "program_group": "nhóm chương trình", "faculty": "Trường/Khoa",
              "method": "phương thức", "certificate": "chứng chỉ"}
# tham so -> loai thuc the duoc nhan. "programs" nhan ca nhom (tool tu tach nhom: resolve_mentions)
FIELDS = {"programs": {"program", "program_group"}, "program_group": {"program_group"},
          "faculty": {"faculty"}, "faculties": {"faculty"}}
# Ten goi chinh HUST: dien vao o Truong/Khoa hay nhom chuong trinh la hieu nham (S04 "thap nhat cua Bach khoa")
SELF_NAMES = {normalize(x) for x in (
    "Bách khoa", "Bách khoa Hà Nội", "ĐHBK", "ĐHBK Hà Nội", "ĐHBKHN", "BK", "HUST", "Đại học Bách khoa",
    "Đại học Bách khoa Hà Nội", "trường", "trường mình", "nhà trường", "Hanoi University of Science and Technology",
    "the university", "university")}
SELF_FIELDS = {"program_group", "faculty", "faculties"}
PAREN = re.compile(r"\(([^()]{1,40})\)")
ACADEMIC_YEAR = re.compile(r"(?<!\d)(20\d\d)\s*[-–/]\s*(20\d\d)(?!\d)")


def academic_years(question: str) -> list[tuple[int, int]]:
    """Cap "2026-2027" (nam sau = nam truoc + 1) trong cau: la MOT nam hoc, khong phai hai nam."""
    return [(int(a), int(b)) for a, b in ACADEMIC_YEAR.findall(question) if int(b) == int(a) + 1]


def hint_line(scan: ScanResult, question: str = "") -> str | None:
    """'# Tu dien nhan ra trong cau: "IT1" (nganh) · "diem thi THPT" (phuong thuc) · nam 2024, 2025'.
    "2026-2027" ghi "nam hoc 2026-2027 (nam bat dau 2026)": ghi "nam 2026, 2027" thi Router dien 2 nam (S39)."""
    parts = []
    for m in scan.mentions:
        kinds = " / ".join(TYPE_LABEL[t] for t in sorted(m.entity_types) if t in TYPE_LABEL)
        parts.append(f"\"{m.text}\" ({kinds})" if kinds else f"\"{m.text}\"")
    pairs = academic_years(question)
    in_pairs = {y for p in pairs for y in p}
    parts += [f"năm học {a}-{b} (năm bắt đầu {a})" for a, b in pairs]
    years = [y for y in scan.years if y not in in_pairs]
    if years:
        parts.append("năm " + ", ".join(map(str, years)))
    return "# Từ điển nhận ra trong câu: " + " · ".join(parts) if parts else None


def _code_types(token: str, aliases: AliasIndex) -> set[str]:
    return {e.entity_type for e in aliases.exact.get(normalize(token), []) if e.kind == "code"}


def paren_codes(question: str, aliases: AliasIndex) -> list[tuple[str, str, set[str]]]:
    """[(cum truoc ngoac da chuan hoa, MA, loai)] cho moi "ten (MA)" voi MA la ma hop le, mot ma trong ngoac."""
    out, prev = [], 0
    for m in PAREN.finditer(question):
        inner = m.group(1).strip()
        types = _code_types(inner, aliases)
        if types:
            out.append((normalize(question[prev:m.start()]), inner, types))
        prev = m.end()
    return out


def _pool(scan: ScanResult, question: str) -> list[Mention]:
    """Cum bo quet tim duoc; bo TEN dung ngay truoc "(MA)" — cap ten + ma chi lay ma."""
    ms = scan.mentions
    out = []
    for i, m in enumerate(ms):
        nxt = ms[i + 1] if i + 1 < len(ms) else None
        if nxt and question[m.end:nxt.start].strip() == "(":
            continue
        out.append(m)
    return out


def reconcile_args(args: dict, question: str, scan: ScanResult, aliases: AliasIndex,
                   used: set[str]) -> list[str]:
    """Sua TAI CHO args (dict cua mot lenh goi); tra danh sach thay doi de bao cao.

    Hai luot: (1) gia tri dung (co trong cau / doi ra ma / bo ten chinh truong) dua vao `used`; (2) gia tri Router tu
    dien moi lay cum bo quet CHUA dung — khong lay trung cum da co o tham so khac cua cung lenh goi.
    """
    qn = f" {normalize(question)} "
    pairs = paren_codes(question, aliases)
    scanned = {compact(m.text) for m in scan.mentions}
    pool = _pool(scan, question)
    fixes = []
    plan: dict[str, list[tuple[str, str | None, bool]]] = {}       # field -> [(goc, moi, can thay tu bo quet)]
    coded: dict[str, str] = {}                                      # doan truoc "(MA)" da doi ra ma -> tham so
    for field, accepted in FIELDS.items():
        value = args.get(field)
        values = value if isinstance(value, list) else ([value] if value else [])
        norms = [normalize(v) for v in values]
        rows = []
        for v, n in zip(values, norms):
            # N16 (S01 do 2026-11-26): Router chep CA CUM co ma "Khoa hoc may tinh (IT1)" -> lay ma trong ngoac,
            # neu dung loai. Ngoac khong phai ma ("(CT tien tien)") hoac ma sai loai thi bo qua
            own = next((m.group(1).strip() for m in PAREN.finditer(v)
                        if _code_types(m.group(1).strip(), aliases) & accepted), None)
            if own:
                for pre, c, _t in pairs:
                    if c == own:
                        coded[pre] = field
                rows.append((v, own, False))
                continue
            hit = next(((pre, c) for pre, c, t in pairs if t & accepted and n and (pre == n or pre.endswith(" " + n))),
                       None)
            if hit is None:
                # N3 (S37): ten nam TRONG doan truoc "(MA)" nhung khong sat ngoac ("Co dien tu hop tac voi DH Leibniz
                # Hannover (ME-LUH)"); chi doi khi la gia tri DUY NHAT cua tham so nay trong doan -> khong doi nham
                # "Co dien tu va Ky thuat O to (TE1)"
                hit = next(((pre, c) for pre, c, t in pairs if t & accepted and n and f" {n} " in f" {pre} "
                            and sum(f" {m} " in f" {pre} " for m in norms if m) == 1), None)
            if hit:
                coded[hit[0]] = field
                rows.append((v, hit[1], False))
            elif field in SELF_FIELDS and n in SELF_NAMES:
                rows.append((v, None, False))
            elif n and (f" {n} " in qn or compact(v) in scanned):
                rows.append((v, v, False))
            else:
                rows.append((v, None, True))
        plan[field] = rows
    # N3: gia tri o THAM SO KHAC nam trong doan da doi ra ma (S37 nhom "Leibniz") -> bo: nguoi dung da noi ro bang ma.
    # Cung tham so thi giu ("Co dien tu va Ky thuat O to (TE1)": "Co dien tu" la nganh khac)
    for field, rows in plan.items():
        plan[field] = [(v, None, False) if new == v and any(f" {normalize(v)} " in f" {pre} " and f != field
                                                            for pre, f in coded.items())
                       else (v, new, rep) for v, new, rep in rows]
        used |= {compact(new) for _, new, _ in plan[field] if new}
    for field, rows in plan.items():
        if not rows:
            continue
        kept: list[str] = []
        for v, new, replace in rows:
            if replace:
                cand = next((m for m in pool if m.entity_types & FIELDS[field] and compact(m.text) not in used), None)
                new = cand.text if cand else v
                used.add(compact(new))
            if new is not None and compact(new) not in {compact(k) for k in kept}:
                kept.append(new)
            if new != v:
                fixes.append(f"{field}: \"{v}\" → " + (f"\"{new}\"" if new else "bỏ"))
            elif replace:                  # dem chi so "Router dien chu khong co trong cau" (khong sua)
                fixes.append(f"{field}: \"{v}\" không có trong câu, bộ quét không thấy cụm cùng loại → giữ")
        args[field] = kept if isinstance(args[field], list) else (kept[0] if kept else None)
    return fixes


def reconcile(calls: list, question: str, scan: ScanResult, aliases: AliasIndex) -> list[str]:
    """Sua args cua cac lenh goi (pydantic *Input) tai cho. Tra danh sach thay doi."""
    fixes, used = [], set()
    for c in calls:
        args = {f: getattr(c.args, f) for f in FIELDS if hasattr(c.args, f)}
        got = reconcile_args(args, question, scan, aliases, used)
        for f, v in args.items():
            setattr(c.args, f, v)
        fixes += [f"{c.tool}.{x}" for x in got]
        used.clear()                       # lenh goi khac duoc dung lai cung cum (vd hoc phi + diem chuan cung nganh)
    return fixes + fix_academic_years(calls, question)


def fix_academic_years(calls: list, question: str) -> list[str]:
    """Hoc phi: years la "nam hoc bat dau" (TuitionInput). Cau "nam hoc 2026-2027" ma Router dien [2026, 2027]
    -> [2026]; khong thi tool bao thieu nam 2027 (S39)."""
    out = []
    for a, b in academic_years(question):
        for c in calls:
            if c.tool == "tuition_fees" and a in c.args.years and b in c.args.years:
                c.args.years = [y for y in c.args.years if y != b]
                out.append(f"tuition_fees.years: bỏ {b} (năm học {a}-{b})")
    return out
