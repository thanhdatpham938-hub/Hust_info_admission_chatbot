"""Tim cac van ban ma CHINH du lieu cua minh dan toi nhung minh chua co.

Vi sao can phep kiem nay: van ban HUST hay "day" chi tiet sang van ban khac. QCDT
2025 Dieu 14 chi ghi "Dat chuan ngoai ngu dau ra" — con so nam o mot Quy dinh rieng
ma minh khong co. Bot se tra loi thieu ma KHONG bao loi gi, vi chunk van co, retrieval
van tra ve ket qua, chi la ket qua khong chua con so nguoi dung can.

Cac phep kiem do phu theo tu khoa KHONG bat duoc loai thieu nay: go "TOEIC" vao van
ra 19 chunk, nhin qua tuong la du, nhung 17/19 la bang diem thuong IELTS khi XET
TUYEN, khong phai chuan tot nghiep. Do phu dem so lan xuat hien, khong doc nghia.

Phep kiem nay di theo huong khac: liet ke moi van ban noi bo duoc trich dan, roi doi
chieu voi danh sach van ban da thu thap. Cai nao duoc dan toi ma khong co trong tay
thi la mot lo trong da biet truoc — quyet dinh lay hay bo la viec cua nguoi, nhung
phai NHIN THAY no.

Dung: python scripts/check_dangling_refs.py
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAG = ROOT / "data" / "rag" / "raw_chunks"
ADMISSION = ROOT / "data" / "raw" / "admission"

# So hieu cac van ban DA co trong tay -> doi chieu voi cac so hieu duoc trich dan
COLLECTED = {
    "5445/QĐ-ĐHBK": "QCDT 2025 (data/raw/admission/QCDT_2025_5445_QD-DHBK.pdf)",
    "10461/QĐ-ĐHBK": "Quy chế thi TSA 2024 (data/raw/admission/10461-QD-DHBK_...pdf)",
    "10828/QĐ-ĐHBK": "Quy định ngoại ngữ K71 (data/raw/admission/Quy_dinh_ngoai_ngu_K71_2026.pdf)",
    "10728/QĐ-ĐHBK": "Quy định ngoại ngữ K70 (data/raw/admission/Quy_dinh_ngoai_ngu_K70.pdf)",
}
# Van ban duoc dan toi nhung CO CHU DICH bo qua, kem ly do — de lan sau khong bao lai
IGNORED = {
    "4600/QĐ-ĐHBK": "QCDT 2023, đã bị 5445/QĐ-ĐHBK thay thế — chỉ có giá trị lịch sử",
    "3095/QĐ-ĐHBK-ĐT": "Quy chế đào tạo tiến sĩ 2021 — ngoài phạm vi MVP (đại học chính quy)",
    "2764/QĐ-ĐHBK-SĐH": "Quy định đào tạo tiến sĩ 2017 — ngoài phạm vi MVP",
    "2952/QĐ-ĐHBK-TCCB": "Quyết định tổ chức (nâng cấp Khoa SPKT) — không phục vụ câu hỏi nào",
}

DOC_NO = re.compile(r"(\d{3,5})\s*/\s*(QĐ-ĐHBK(?:-[A-ZĐ]{2,4})?)")
# Cac cach van ban day chi tiet sang cho khac -> diem mu can biet truoc
DEFER_PATTERNS = [
    (r"theo [Qq]uy định (?:hiện hành )?(?:riêng )?của (?:Nhà trường|ĐHBK|Đại học Bách khoa)",
     "đẩy sang quy định của Trường"),
    (r"do ĐHBK Hà Nội quy định", "để Trường quy định, không nêu số"),
    (r"theo quy định riêng", "theo quy định riêng"),
    (r"\(thông báo sau\)|sẽ (?:được )?thông báo sau", "sẽ thông báo sau"),
    (r"[Đđ]ạt chuẩn ngoại ngữ đầu ra(?!.{0,40}[Bb]ậc)", "yêu cầu chuẩn ngoại ngữ mà không nêu mức"),
]


def norm(t: str) -> str:
    return unicodedata.normalize("NFC", t)


def load_chunks() -> list[tuple[str, str]]:
    out = []
    for path in sorted(RAG.glob("*.chunks.jsonl")):
        name = path.name[:-len(".chunks.jsonl")]
        for line in path.open(encoding="utf-8"):
            out.append((name, norm(json.loads(line)["text"])))
    return out


def main() -> int:
    chunks = load_chunks()
    refs: dict[str, set[str]] = defaultdict(set)
    context: dict[str, str] = {}
    for src, text in chunks:
        for m in DOC_NO.finditer(text):
            key = f"{m.group(1)}/{m.group(2)}"
            refs[key].add(src)
            context.setdefault(key, re.sub(r"\s+", " ", text[max(0, m.start() - 170):m.start() + 60]))

    missing = {k: v for k, v in refs.items() if k not in COLLECTED and k not in IGNORED}
    print(f"{len(refs)} văn bản nội bộ được trích dẫn · {len(COLLECTED)} đã có · "
          f"{len(IGNORED)} chủ ý bỏ · {len(missing)} CHƯA CÓ\n")

    if missing:
        print("=== Văn bản được dẫn tới mà chưa thu thập ===")
        for key in sorted(missing):
            print(f"  {key}")
            print(f"      dẫn từ : {', '.join(sorted(missing[key]))}")
            print(f"      ngữ cảnh: ...{context[key][-150:]}")
        print()

    print("=== Chỗ văn bản đẩy chi tiết sang nơi khác (bot sẽ trả lời thiếu ở đây) ===")
    for pattern, label in DEFER_PATTERNS:
        hits = defaultdict(int)
        for src, text in chunks:
            n = len(re.findall(pattern, text))
            if n:
                hits[src] += n
        total = sum(hits.values())
        detail = ", ".join(f"{k}({v})" for k, v in sorted(hits.items(), key=lambda x: -x[1])[:3])
        print(f"  {label:44s} {total:3d}  {detail[:60]}")

    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
