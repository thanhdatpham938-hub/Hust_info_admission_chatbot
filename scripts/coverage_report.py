"""Bao cao do phu du lieu theo tung nganh -> tra loi khach quan cau "da du chua".

Voi moi nganh cua nam moi nhat, kiem tra co du: diem chuan, chi tieu, phuong thuc,
mo ta ngan, curriculum_url, hoc phi (theo nhom chuong trinh).
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
PROGRAMS_DIR = ROOT / "data" / "programs"
YEAR = 2026


def load(name):
    path = PROC / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    programs = load(f"programs_{YEAR}.csv")
    scores = {r["program_code"] for r in load(f"admission_scores_{YEAR}.csv")}
    quotas = {r["program_code"] for r in load(f"quotas_{YEAR}.csv")}
    methods = {r["program_code"] for r in load(f"program_methods_{YEAR}.csv")}
    groups = {r["program_code"]: r.get("program_group", "") for r in load(f"quotas_{YEAR}.csv")}
    combos = {r["program_code"] for r in load(f"subject_combinations_{YEAR}.csv")}

    desc, curr = set(), set()
    for f in PROGRAMS_DIR.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("short_description"):
            desc.add(d["program_code"])
        if d.get("curriculum_url"):
            curr.add(d["program_code"])

    cols = ["điểm chuẩn", "chỉ tiêu", "phương thức", "tổ hợp", "nhóm CT (học phí)", "mô tả ngắn", "CTĐT"]
    missing_rows, counts = [], {c: 0 for c in cols}

    for p in programs:
        code = p["program_code"]
        have = {
            "điểm chuẩn": code in scores,
            "chỉ tiêu": code in quotas,
            "phương thức": code in methods,
            "tổ hợp": code in combos,
            "nhóm CT (học phí)": bool(groups.get(code)),
            "mô tả ngắn": code in desc,
            "CTĐT": code in curr,
        }
        for c in cols:
            counts[c] += have[c]
        if not all(have.values()):
            missing_rows.append((code, p["program_name"][:40], [c for c in cols if not have[c]]))

    n = len(programs)
    print(f"ĐỘ PHỦ DỮ LIỆU — {n} ngành (năm {YEAR})\n")
    for c in cols:
        pct = counts[c] * 100 / n
        bar = "█" * int(pct / 5)
        print(f"  {c:20s} {counts[c]:3d}/{n} {pct:5.1f}% {bar}")

    print(f"\nNgành còn thiếu: {len(missing_rows)}/{n}\n")
    for code, name, miss in missing_rows:
        print(f"  {code:10s} {name:42s} thiếu: {', '.join(miss)}")
