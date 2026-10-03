"""Do xem 120 cau hoi trong backend/tests/eval/120_question_check_data.md co du lieu tra loi hay khong.

KHONG phai chay chatbot — chua co bot. Day la phep do do phu: voi tung cau, tim
trong (a) cac bang CSV va (b) 573 chunk RAG xem co nguon nao chua cac tu khoa cot
loi cua cau do khong. Ket qua chia 3 muc:

    DU     — tim thay nguon ro rang (nhieu tu khoa cung xuat hien trong mot chunk)
    YEU    — chi tim thay mot phan, co the tra loi mo ho hoac phai suy dien
    THIEU  — khong tim thay nguon nao

Muc dich la loc ra danh sach cau THIEU de biet con phai thu thap gi, truoc khi
viet bo test that su cho AC1-AC9.

Dung: python scripts/probe_questions.py [--detail]
"""

import csv
import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QFILE = ROOT / "backend" / "tests" / "eval" / "120_question_check_data.md"

STOP = set("""la gi co khong nao the nhu the nao bao nhieu cua va hay cac nhung
duoc cho tai voi tu den ve theo mot hai ba khi neu thi ma o tren duoi ra vao
em toi anh chi minh truong nam hoc sinh vien hust bach khoa ha noi dhbk
cau hoi vd vi du thuong rat hon kem sau truoc con moi cung deu tat ca
nhung con phai can nen sao lam gi dau bang""".split())


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower().replace("đ", "d"))  # "đ" khong phai to hop
    #  dau nen NFD khong tach ra; khong doi thanh "d" truoc thi buoc loc [^a-z0-9]
    #  se XOA han no: "dang ky" -> "ang ky", "diem" -> "iem". Hau qua: nguoi dung go
    #  khong dau ("dien tu vien thong") se khong khop voi ten nganh da chuan hoa.
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t)


def keywords(q: str) -> list[str]:
    """Tra ve CUM TU (2-3 am tiet) chu khong phai tung am tiet.

    Tieng Viet la ngon ngu da am tiet: "ky tuc xa", "ty le choi", "chi phi sinh hoat"
    chi co nghia khi di lien nhau. Ban dau toi loc tu khoa theo do dai ky tu, ket qua
    la "ky tuc xa" bi loai sach (moi am tiet <= 3 chu) va cau chi con mot tu "phong"
    -> khop 100% mot cach vo nghia. Do do bat buoc phai khop theo cum.
    """
    codes = [norm(c) for c in re.findall(r"\b[A-Z]{2,5}-?[A-Z]?\d{1,2}\b", q)]
    syl = [w for w in norm(q).split() if w not in STOP]
    phrases = []
    for size in (3, 2):
        for i in range(len(syl) - size + 1):
            gram = syl[i:i + size]
            if sum(1 for g in gram if g in STOP) == 0:
                phrases.append(" ".join(gram))
    return list(dict.fromkeys(codes + phrases))


def load_corpus() -> list[tuple[str, str]]:
    """[(nhan nguon, van ban da chuan hoa)] gom ca RAG va CSV."""
    out = []
    for f in glob.glob(str(ROOT / "data" / "rag" / "raw_chunks" / "*.chunks.jsonl")):
        name = Path(f).name[:-13]
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            out.append((f"rag:{name}", norm(f"{r.get('heading','')} {r['text']}")))
    for f in sorted(glob.glob(str(ROOT / "data" / "processed" / "*.csv"))):
        name = Path(f).stem
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        head = norm(" ".join(rows[0].keys())) if rows else ""
        blob = norm(" ".join(" ".join(r.values()) for r in rows[:400] if r))
        out.append((f"csv:{name}", head + " " + blob))
    return out


def parse_questions() -> list[tuple[int, str, str]]:
    section, out = "", []
    for line in QFILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("###"):
            section = re.sub(r"^#+\s*MỤC \d+:\s*", "", line).strip()
        m = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if m:
            out.append((int(m.group(1)), section, m.group(2).strip()))
    return out


def main() -> None:
    detail = "--detail" in sys.argv
    corpus = load_corpus()
    questions = parse_questions()
    print(f"{len(questions)} câu hỏi · {len(corpus)} nguồn (RAG chunk + bảng CSV)\n")

    # Tinh IDF: tu xuat hien o gan het cac nguon ("nganh", "chuong trinh", "dao tao")
    # khong chung minh duoc gi. Dem so tu khop tho se cho ket qua ĐỦ gia — da thu,
    # ra 119/120 ĐỦ, trong do co ca cau ve ty le choi va gia gui xe von khong co du lieu.
    import math
    df: dict[str, int] = {}
    all_kws = {k for _, _, q in questions for k in keywords(q)}
    for k in all_kws:
        df[k] = sum(1 for _, text in corpus if k in text)
    n = len(corpus)
    idf = {k: math.log((n + 1) / (df[k] + 1)) for k in all_kws}

    verdicts = []
    for num, section, q in questions:
        kws = [k for k in keywords(q) if df.get(k, 0) > 0]
        missing_all = [k for k in keywords(q) if df.get(k, 0) == 0]
        total_w = sum(idf[k] for k in keywords(q)) or 1e-9
        best, best_score, best_hits = "", 0.0, []
        for label, text in corpus:
            hits = [k for k in kws if k in text]
            score = sum(idf[k] for k in hits)
            if score > best_score:
                best, best_score, best_hits = label, score, hits
        ratio = best_score / total_w
        level = "ĐỦ" if ratio >= 0.55 else ("YẾU" if ratio >= 0.3 else "THIẾU")
        verdicts.append((num, section, q, level, best, ratio, missing_all))

    from collections import Counter
    by_section = {}
    for v in verdicts:
        by_section.setdefault(v[1], []).append(v[3])
    print(f"{'MỤC':58s} {'ĐỦ':>4s} {'YẾU':>4s} {'THIẾU':>6s}")
    for sec, lvs in by_section.items():
        c = Counter(lvs)
        print(f"  {sec[:56]:56s} {c['ĐỦ']:4d} {c['YẾU']:4d} {c['THIẾU']:6d}")
    total = Counter(v[3] for v in verdicts)
    print(f"\nTổng: ĐỦ {total['ĐỦ']} · YẾU {total['YẾU']} · THIẾU {total['THIẾU']}")

    print("\n=== Câu THIẾU nguồn (cần thu thập thêm hoặc chấp nhận ngoài phạm vi) ===")
    for num, sec, q, lv, src, ratio, gone in verdicts:
        if lv == "THIẾU":
            extra = f"  [từ khoá không có trong dữ liệu: {', '.join(gone[:4])}]" if gone else ""
            print(f"  {num:3d}. ({ratio:.0%}) {q[:92]}{extra}")
    if detail:
        print("\n=== Câu YẾU (chỉ tìm thấy một phần) ===")
        for num, sec, q, lv, src, ratio, gone in verdicts:
            if lv == "YẾU":
                print(f"  {num:3d}. [{ratio:.0%} {src}] {q[:86]}")


if __name__ == "__main__":
    main()
