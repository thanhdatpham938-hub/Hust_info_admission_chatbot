"""Cham Entity Resolution tren bo ca co nhan backend/tests/eval/entity_cases.csv -> so do AC2, AC8 (PRD 21).

  AC2: ca unique / group / not_found — dung trang thai VA dung tap ma
  AC8: ca clarify (phai hoi lai) — bao 2 so:
         nghiem: hoi lai VA dung tap ung vien
         long:   co hoi lai (khong tu chon), du tap ung vien lech

Nhan do tro ly soan nhap, NGUOI DUNG soat (cot `duyet`). Ca lech KHONG duoc sua nhan cho khop code:
hoac code sai (sua code/alias), hoac nhan sai (nguoi dung sua nhan).

Dung: python scripts/eval_entity_cases.py      -> in so do + ghi docs/ghi_chu/<ngay> - Do AC2 AC8.md
"""

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
import build_db  # noqa: E402
from app.tools.context import ToolContext  # noqa: E402

CASES = ROOT / "backend" / "tests" / "eval" / "entity_cases.csv"
OUT = ROOT / "docs" / "ghi_chu" / f"{date.today()} - Do AC2 AC8.md"


def main() -> int:
    ctx = ToolContext.from_tables(build_db.build_rows())
    rows = list(csv.DictReader(CASES.open(encoding="utf-8-sig", newline="")))
    results = []
    for r in rows:
        years = [int(r["year"])] if r["year"] else None
        res = ctx.resolve(r["mention"], r["entity_type"], years)
        got_codes = {res.group_code} if res.group_code else set(res.codes)
        want_codes = {c for c in r["expected_codes"].split(";") if c}
        status_ok = res.status == r["expected_status"]
        results.append({**r, "got_status": res.status, "got_codes": ";".join(sorted(got_codes)),
                        "matched_by": res.matched_by or "-",
                        "ok": status_ok and got_codes == want_codes, "asked": res.status == "clarify"})

    ac2 = [x for x in results if x["ac"] == "AC2"]
    ac8 = [x for x in results if x["ac"] == "AC8"]
    pct = lambda n, d: f"{n}/{d} = {100 * n / d:.1f}%" if d else "—"
    ac2_line = pct(sum(x["ok"] for x in ac2), len(ac2))
    ac8_strict = pct(sum(x["ok"] for x in ac8), len(ac8))
    ac8_loose = pct(sum(x["asked"] for x in ac8), len(ac8))
    reviewed = sum(1 for r in rows if r["duyet"].strip())

    lines = [f"# Đo AC2 / AC8 trên bộ ca có nhãn — {date.today()}", "",
             f"Sinh bởi `scripts/eval_entity_cases.py` từ `backend/tests/eval/entity_cases.csv` ({len(rows)} ca).", "",
             f"**Nhãn đã được duyệt: {reviewed}/{len(rows)} ca.**" + (
                 " Nhãn do trợ lý soạn nháp, CHƯA được người dùng soát — số dưới đây là số tạm." if reviewed < len(rows) else ""),
             "", "| Chỉ số | Kết quả | Mục tiêu PRD |", "|---|---|---|",
             f"| AC2 — nhận đúng thực thể | {ac2_line} | ≥ 95% |",
             f"| AC8 — hỏi lại khi mơ hồ (nghiêm: đúng tập ứng viên) | {ac8_strict} | ≥ 95% |",
             f"| AC8 — có hỏi lại, không tự chọn (lỏng) | {ac8_loose} | — |", "",
             "## Ca lệch", "",
             "Mỗi ca lệch hoặc là **code/alias sai** (sửa code hoặc thêm alias), hoặc là **nhãn sai** (anh sửa nhãn). "
             "Không sửa nhãn cho khớp code.", "",
             "| ID | AC | Gõ | Năm | Nhãn | Code trả | Khớp bằng | Ghi chú nhãn |", "|---|---|---|---|---|---|---|---|"]
    for x in results:
        if not x["ok"]:
            lines.append(f"| {x['id']} | {x['ac']} | `{x['mention']}` ({x['entity_type']}) | {x['year'] or '—'} | "
                         f"{x['expected_status']} {x['expected_codes'] or '—'} | {x['got_status']} {x['got_codes'] or '—'} | "
                         f"{x['matched_by']} | {x['note']} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"AC2 {ac2_line} | AC8 nghiêm {ac8_strict} | AC8 lỏng {ac8_loose} | đã duyệt {reviewed}/{len(rows)}")
    print(f"-> {OUT.relative_to(ROOT)}")
    for x in results:
        if not x["ok"]:
            print(f"  {x['id']} {x['mention']!r} {x['year']}: nhãn {x['expected_status']} {x['expected_codes']} | "
                  f"code {x['got_status']} {x['got_codes']} ({x['matched_by']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
