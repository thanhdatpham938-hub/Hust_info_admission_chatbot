"""Chay scan() + resolve() cua backend tren bo 120 cau, ghi bang "cau -> cum tim duoc -> ma" vao
docs/ghi_chu/ de DOC BANG MAT (PLAN - Entity Resolution + Admission Tool (v1), muc 5).

Day CHUA phai so do AC2/AC8: chua co bo ca co nhan (cho nguoi dung quyet o buoc 8 PLAN - Tools).

Dung: python scripts/eval_entity_scan.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
import build_db  # noqa: E402
from app.tools.context import ToolContext  # noqa: E402

EVAL = ROOT / "backend" / "tests" / "eval" / "120_question_check_data.md"
OUT = ROOT / "docs" / "ghi_chu" / f"{date.today()} - Ket qua entity resolution.md"


def main() -> int:
    ctx = ToolContext.from_tables(build_db.build_rows())
    rows = [line.split("|") for line in EVAL.read_text(encoding="utf-8").splitlines() if line.startswith("| **Q")]
    lines, n_found, status_count = [], 0, {}
    for r in rows:
        qid, question = r[1].strip().strip("*"), r[3].strip()
        scan = ctx.scanner.scan(question)
        years = [y for y in scan.years if 2000 <= y <= 2100] or None
        parts = []
        for m in scan.mentions:
            etype = "program" if "program" in m.entity_types or "program_group" in m.entity_types \
                else sorted(m.entity_types)[0]
            res = ctx.resolve(m.text, etype, years)
            status_count[res.status] = status_count.get(res.status, 0) + 1
            label = res.group_code or ", ".join(res.codes) or "—"
            parts.append(f"`{m.text}` → {etype}: **{res.status}** {label} ({res.matched_by or '-'})")
        n_found += bool(parts)
        lines.append(f"| {qid} | {question[:90]} | {'<br>'.join(parts) or '—'} | {', '.join(map(str, scan.years))} |")

    head = [f"# Kết quả Entity Resolution trên bộ 120 câu — {date.today()}", "",
            "Sinh bởi `scripts/eval_entity_scan.py`: `scan()` tìm cụm từ trong câu, `resolve()` đổi ra mã "
            "(năm lấy theo năm ghi trong câu, không có thì năm mới nhất). **Chưa phải số đo AC2/AC8** — "
            "chưa có bộ ca có nhãn; bảng này để đọc bằng mắt, tìm alias thiếu và chỉnh ngưỡng fuzzy.", "",
            f"- {len(rows)} câu, {n_found} câu tìm được ít nhất một cụm",
            "- Kết quả theo cụm: " + ", ".join(f"{k} = {v}" for k, v in sorted(status_count.items())), "",
            "| ID | Câu hỏi | Cụm → kết quả | Năm |", "|---|---|---|---|"]
    OUT.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(rows)} câu, {n_found} có cụm; {status_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
