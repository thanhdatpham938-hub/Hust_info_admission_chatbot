"""Kiem tra data/processed/entity_aliases.csv truoc khi dung lam tu dien tra cuu.

Bat cac loi de xay ra khi soan tay:
  - alias tro toi ma nganh khong ton tai o bat ky nam nao
  - alias tro toi nhieu ma nhung lai danh dau 'unique' (bot se chon bua mot ma)
  - alias danh dau 'clarify' nhung chi co mot ma (bot se hoi lai vo ich)
  - trung dong (alias, entity_code)
  - alias trung nhau sau khi chuan hoa (khac hoa/thuong, khac dau cach)
  - alias trung voi chinh program_name da co -> thua, gay nhieu
  - alias qua ngan de khop nham trong van ban

Dung: python scripts/validate_aliases.py
"""

import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
ALIAS_CSV = PROCESSED / "entity_aliases.csv"

VALID_TYPES = {"program", "program_group"}
VALID_ALIAS_TYPES = {"en", "colloquial", "abbrev", "code_variant"}
VALID_RESOLUTIONS = {"unique", "clarify", "group"}
MIN_ALIAS_LEN = 2


def normalize(text: str) -> str:
    """Bo dau, ve chu thuong, gop khoang trang — dung de bat alias trung nhau."""
    # "đ" khong phai to hop dau nen NFD khong tach; khong doi sang "d" truoc thi
    # buoc loc [^a-z0-9] se XOA han: "diem" -> "iem", "dang ky" -> "ang ky".
    # Nguoi dung go khong dau se khong khop duoc ten nganh — dung pham vi PRD 3.B.
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def load_known() -> tuple[dict[str, str], set[str]]:
    """Ma nganh hop le = hop cua MOI nam, vi co nganh chi tuyen den 2025 (TROY-BA, EM4)."""
    codes, groups = {}, set()
    for path in sorted(PROCESSED.glob("programs_*.csv")):
        year = path.stem.split("_")[-1]
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            codes.setdefault(row["program_code"], year)
            codes[row["program_code"]] = max(codes[row["program_code"]], year)
    for path in sorted(PROCESSED.glob("quotas_*.csv")):
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            if row.get("program_group"):
                groups.add(row["program_group"])
    return codes, groups


def load_program_names() -> dict[str, str]:
    names = {}
    for path in sorted(PROCESSED.glob("programs_*.csv")):
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            names[normalize(row["program_name"])] = row["program_code"]
    return names


def simulate_lookup(rows: list[dict]) -> list[str]:
    """Go thu tung alias vao dung thuat toan tra cuu cua bot, xem co ra dung khong.

    Bat loai loi ma cac phep kiem o tren khong thay: alias dung cu phap, tro dung ma,
    nhung khi TRA CUU THAT lai ra thua hoac thieu ma vi bi ten ngành/alias khac nuot.
    Vi du da gap: 'Chemistry' bi 'Cosmetic Chemistry' nuot; 'Ky thuat O to' chi ra TE1
    vi khop chinh xac dung lai truoc khi kip goi y TE-E2.

    Ba quy tac khop (phai cai dat y het o tang tra cuu cua bot):
      1) khop chinh xac tren chuoi da chuan hoa -> tra ve ngay
      2) khong co thi moi lui ve khop chuoi con
      3) alias_type='abbrev' CHI tham gia buoc 1 (viet tat 2-3 ky tu nhu 'BA' neu cho
         khop chuoi con se dinh hang chuc nganh)
    """
    program_names = {}
    for path in sorted(PROCESSED.glob("programs_*.csv")):
        for row in csv.DictReader(path.open(encoding="utf-8", newline="")):
            program_names.setdefault(normalize(row["program_name"]), set()).add(row["program_code"])

    declared, exact, substring = defaultdict(set), defaultdict(set), defaultdict(set)
    for row in rows:
        if row["entity_type"].strip() != "program":
            continue
        key = normalize(row["alias"])
        declared[key].add(row["entity_code"].strip())
        exact[key].add(row["entity_code"].strip())
        if row["alias_type"].strip() != "abbrev":
            substring[key].add(row["entity_code"].strip())
    for name, codes in program_names.items():
        exact[name] |= codes
        substring[name] |= codes

    def resolve(query: str) -> set[str]:
        key = normalize(query)
        if key in exact:
            return exact[key]
        return {c for k, codes in substring.items() if key in k for c in codes}

    out = []
    for alias, want in sorted(declared.items()):
        got = resolve(alias)
        if got != want:
            out.append(
                f"gõ '{alias}' sẽ ra {sorted(got) or 'KHÔNG GÌ CẢ'} trong khi file khai "
                f"báo {sorted(want)} — kiểm tra lại (thừa {sorted(got - want)}, "
                f"thiếu {sorted(want - got)})"
            )
    return out


def check_shape(rows: list[dict]) -> list[str]:
    """Bat dong tran cot: note co dau phay ma khong dat trong nguoc kep.

    csv.DictReader nhet phan thua vao khoa None nen doc theo ten cot van thay binh
    thuong — da gap that khi them 14 dong Nhom 2, note co dau phay giua cau.
    """
    return [
        f"dòng {i}: thừa cột — note chứa dấu phẩy mà không đặt trong ngoặc kép: {row[None]}"
        for i, row in enumerate(rows, start=2) if None in row
    ] + [
        # DictReader luon tra du khoa theo dong tieu de; dong thieu o thi gia tri la None.
        # (Ban truoc so len(row) voi so co dinh 7 -> vua khong bat duoc dong thieu o, vua
        # bao sai toan bo khi bang them cot dataset_version.)
        f"dòng {i}: thiếu cột (ô cuối trống do dòng ngắn hơn tiêu đề)"
        for i, row in enumerate(rows, start=2) if None not in row and any(v is None for v in row.values())
    ]


def main() -> int:
    rows = list(csv.DictReader(ALIAS_CSV.open(encoding="utf-8", newline="")))
    shape_errors = check_shape(rows)
    # dong lech cot da bao loi o tren; cac buoc sau chi xet dong nguyen ven (neu khong se
    # crash o chuoi None — phat hien khi thu nguoc 2026-09-27)
    rows = [r for r in rows if None not in r and all(v is not None for v in r.values())]
    known_codes, known_groups = load_known()
    program_names = load_program_names()

    errors, warnings = list(shape_errors), []
    by_alias = defaultdict(list)
    seen_pairs = set()

    for i, row in enumerate(rows, start=2):  # dong 1 la header
        # dong lech cot da duoc check_shape bao loi; bo qua o day de khong crash vi o None
        if None in row or any(v is None for v in row.values()):
            continue
        alias = row["alias"].strip()
        code = row["entity_code"].strip()
        etype = row["entity_type"].strip()

        if not alias:
            errors.append(f"dòng {i}: alias rỗng")
            continue
        if len(alias) < MIN_ALIAS_LEN:
            errors.append(f"dòng {i}: alias '{alias}' quá ngắn (<{MIN_ALIAS_LEN} ký tự)")
        if etype not in VALID_TYPES:
            errors.append(f"dòng {i}: entity_type '{etype}' không hợp lệ")
        if row["alias_type"].strip() not in VALID_ALIAS_TYPES:
            errors.append(f"dòng {i}: alias_type '{row['alias_type']}' không hợp lệ")
        if row["resolution"].strip() not in VALID_RESOLUTIONS:
            errors.append(f"dòng {i}: resolution '{row['resolution']}' không hợp lệ")

        if etype == "program" and code not in known_codes:
            errors.append(f"dòng {i}: alias '{alias}' trỏ tới mã ngành '{code}' không tồn tại ở năm nào")
        if etype == "program_group" and code not in known_groups:
            errors.append(f"dòng {i}: alias '{alias}' trỏ tới nhóm '{code}' không có trong quotas_*.csv")

        if (normalize(alias), code) in seen_pairs:
            errors.append(f"dòng {i}: trùng dòng ({alias}, {code})")
        seen_pairs.add((normalize(alias), code))

        by_alias[normalize(alias)].append((i, alias, code, row["resolution"].strip()))

        # Alias trung y het ten nganh chi thua khi no tro DUNG mot ma: luc do khop
        # chuoi thong thuong da ra ket qua. Neu la 'clarify' thi BAT BUOC phai khai
        # bao, vi quy tac khop chinh xac se dung lai o ma hệ chuẩn va bo qua hoi lai.
        if (row["alias_type"].strip() not in ("code_variant",)
                and row["resolution"].strip() == "unique"
                and normalize(alias) in program_names):
            target = program_names[normalize(alias)]
            warnings.append(
                f"dòng {i}: alias '{alias}' trùng y hệt tên ngành {target} đã có trong "
                f"programs_*.csv — khớp chuỗi thường đã ra kết quả, dòng này có thể thừa"
            )

    # resolution phai khop voi so ma that su tro toi
    for key, items in by_alias.items():
        codes = {c for _, _, c, _ in items}
        resolutions = {r for _, _, _, r in items}
        display = items[0][1]
        if len(codes) > 1 and "unique" in resolutions:
            lines = [str(i) for i, _, _, r in items if r == "unique"]
            errors.append(
                f"alias '{display}' trỏ tới {len(codes)} mã ({', '.join(sorted(codes))}) "
                f"nhưng dòng {', '.join(lines)} đánh dấu 'unique' -> bot sẽ chọn bừa một mã"
            )
        if len(codes) == 1 and resolutions == {"clarify"}:
            warnings.append(
                f"alias '{display}' chỉ trỏ tới 1 mã ({codes.pop()}) nhưng đánh dấu "
                f"'clarify' -> bot sẽ hỏi lại thừa"
            )
        if len(resolutions) > 1 and resolutions != {"unique"}:
            warnings.append(f"alias '{display}' có resolution không nhất quán: {sorted(resolutions)}")

    warnings += simulate_lookup(rows)

    # thong ke
    per_type = defaultdict(int)
    for row in rows:
        per_type[row["alias_type"].strip()] += 1
    covered = {r["entity_code"] for r in rows if r["entity_type"].strip() == "program"}
    programs_2026 = {
        r["program_code"]
        for r in csv.DictReader((PROCESSED / "programs_2026.csv").open(encoding="utf-8", newline=""))
    }
    missing = sorted(programs_2026 - covered)

    print(f"{ALIAS_CSV.name}: {len(rows)} dòng, {len(by_alias)} alias khác nhau, "
          f"{len(covered)} mã ngành được trỏ tới")
    print("  theo loại: " + ", ".join(f"{k}={v}" for k, v in sorted(per_type.items())))
    print(f"  phủ {len(programs_2026) - len(missing)}/{len(programs_2026)} ngành năm 2026")
    if missing:
        print(f"  [CHƯA CÓ ALIAS] {', '.join(missing)}")

    for w in warnings:
        print(f"  [CẢNH BÁO] {w}")
    for e in errors:
        print(f"  [LỖI] {e}")
    print(f"\n{len(errors)} lỗi, {len(warnings)} cảnh báo")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
