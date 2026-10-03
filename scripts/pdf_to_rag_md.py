"""Chuyển PDF văn bản quy định sang Markdown chunk theo Chương/Điều cho RAG.

Chunk theo ĐIỀU (không cắt nhỏ hơn) để mỗi chunk là một quy định trọn vẹn —
đúng nguyên tắc chunking trong PRD mục 11.2. Mỗi chunk kèm metadata phục vụ
citation (mục 12): tên tài liệu, số hiệu, chương, điều, số trang.

Chỉ xử lý PDF CÓ text layer. PDF scan (KKHT 2022, Quy chế thi TSA 2024) phải
transcribe bằng vision riêng — script sẽ báo và bỏ qua.

Dùng: python scripts/pdf_to_rag_md.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMISSION = ROOT / "data" / "raw" / "admission"
OUT_DIR = ROOT / "data" / "rag" / "raw_chunks"

# file -> metadata dùng cho citation
DOCS = {
    "QCDT_2025_5445_QD-DHBK.pdf": {
        "document_title": "Quy chế đào tạo trình độ đại học",
        "document_no": "5445/QĐ-ĐHBK",
        "document_type": "quy_che_dao_tao",
        "year": 2025,
        "source_url": "https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf",
    },
    "qui-dinh-ve-xttn-nam-2026-ky.pdf": {
        "document_title": "Quy định phương thức Xét tuyển tài năng áp dụng từ năm 2026",
        "document_no": "3030/QĐ-ĐHBK",
        "document_type": "quy_dinh_xttn",
        "year": 2026,
        "source_url": "https://ts.hust.edu.vn/tin-tuc/quy-dinh-ve-phuong-thuc-xet-tuyen-tai-nang-nam-2026",
    },
    "Quy_dinh_ngoai_ngu_K70.pdf": {
        "document_title": "Quy định về phân loại trình độ đầu vào, chương trình ngoại ngữ cơ bản và chuẩn ngoại ngữ đối với sinh viên đại học chính quy (từ khóa K70)",
        "document_no": "10728/QĐ-ĐHBK",
        "document_type": "quy_dinh_ngoai_ngu",
        "year": 2025,
        "source_url": "https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=44574",
        # Van con hieu luc voi sinh vien K70 tro ve truoc — tuc phan lon sinh vien
        # dang hoc. Ban K71 (10828) chi ap dung tu khoa 71. Hoi "chuan dau ra tieng
        # Anh" ma khong biet khoa nao thi phai hoi lai, khong duoc tra lua chon.
        "stop_at": "Phụ lục I",
        "layout": "bold_headings",
    },
    "Quy_dinh_ngoai_ngu_K71_2026.pdf": {
        "document_title": "Quy định về phân loại trình độ đầu vào, chương trình ngoại ngữ cơ bản và chuẩn ngoại ngữ đối với sinh viên đại học chính quy (K71)",
        "document_no": "10828/QĐ-ĐHBK",
        "document_type": "quy_dinh_ngoai_ngu",
        "year": 2026,
        "source_url": "https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=51634",
        # Tu "Phu luc I" tro di la 8 phu luc toan BANG (14 cot). pdftotext tra ve cac
        # o LECH COT -> nhet vao RAG se thanh van ban rac. Bang da boc sang CSV:
        # cert_equivalence_output_2026.csv va language_exit_requirement_2026.csv.
        # Phan van xuoi trong phu luc dua vao EXTRA_SECTIONS ben duoi.
        "stop_at": "Phụ lục I",
        "layout": "bold_headings",
    },
    # So tay sinh vien_2026.pdf KHONG xu ly o day nua: ban in dan 2 trang/1 trang PDF,
    # nhieu cot, infographic -> dung scripts/sotay_to_rag.py (cung file output).
}

DIEU_RE = re.compile(r"^\s*(Điều\s+(\d+)\s*[.:]\s*(.+?))\s*$")
KHOAN_RE = re.compile(r"^\s*(\d+)\.\s+(\S.*)$")
# Dieu dai hon nguong nay moi chia theo khoan; dieu ngan giu tron ven (PRD muc 11.2)
MAX_CHUNK_CHARS = 2500
CHUONG_RE = re.compile(r"^\s*(CHƯƠNG\s+([IVXLC]+)\b\s*[.:]?\s*(.*))\s*$", re.IGNORECASE)


def extract_pages(pdf: Path) -> list[str]:
    """Trả về text từng trang; dùng form feed (\f) mà pdftotext chèn giữa các trang."""
    out = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True, check=True,
    )
    return out.stdout.decode("utf-8", errors="replace").split("\f")


def extract_pages_bold(pdf: Path) -> list[str]:
    """Trich text nhung TACH tieu de in dam ra dong rieng.

    Mot so PDF (Quy dinh ngoai ngu K71) xuong dong theo chieu rong cot chu khong
    theo doan, nen pdftotext tra ve "Dieu 5. <tieu de> 1. <noi dung khoan 1>" tren
    CUNG MOT DONG. Ham chunk_by_dieu doi tieu de nam rieng mot dong nen se coi ca
    cum do la tieu de, roi bi bo loc "heading > 200 ky tu" loai sach — ket qua 7
    Dieu chi con 1 chunk.

    Ban in lai phan biet ro: tieu de Dieu duoc in dam. Dung co flag in dam cua
    PyMuPDF de cat, khong doan theo dau cham cau.
    """
    import pymupdf

    BOLD = 2 ** 4
    out = []
    with pymupdf.open(pdf) as doc:
        for page in doc:
            lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    head = "".join(s["text"] for s in spans if s["flags"] & BOLD).strip()
                    rest = "".join(s["text"] for s in spans if not s["flags"] & BOLD).strip()
                    whole = "".join(s["text"] for s in spans).strip()
                    # KHONG dung dau \b trong regex: da 3 lan bi ghi thanh ky tu
                    # backspace 0x08 vo hinh, lam regex im lang khong khop gi.
                    if head and re.match(r"(Điều\s+\d+|CHƯƠNG)", head):
                        lines.append(head)
                        if rest:
                            lines.append(rest)
                    elif whole:
                        lines.append(whole)
            out.append(chr(10).join(lines))
    return out


def cut_at(pages: list[str], marker: str) -> list[str]:
    """Bo phan tu `marker` tro di (vd cac Phu luc chi gom bang).

    Bang nhieu cot khi trich text se bi lech o; de nguyen se tao chunk rac ma
    retrieval van tra ve. Bang phai boc rieng sang CSV, khong nhet vao RAG.
    """
    out = []
    for page in pages:
        idx = page.find(marker)
        if idx == -1:
            out.append(page)
            continue
        head = page[:idx].strip()
        if head:
            out.append(head)
        break
    return out


def chunk_by_dieu(pages: list[str], meta: dict) -> list[dict]:
    chunks, current, chuong = [], None, ""

    for page_no, page in enumerate(pages, start=1):
        for line in page.splitlines():
            if m := CHUONG_RE.match(line):
                chuong = m.group(1).strip()
                continue
            if m := DIEU_RE.match(line):
                if current:
                    chunks.append(current)
                current = {
                    **meta,
                    "chuong": chuong,
                    "dieu_no": m.group(2),
                    "heading": m.group(1).strip(),
                    "page_no": page_no,
                    "lines": [],
                }
                continue
            if current and line.strip():
                current["lines"].append(line.strip())

    if current:
        chunks.append(current)

    # bỏ mục lục: "Điều X" trong mục lục không có nội dung thật (toàn dấu chấm dẫn trang)
    has_chapters = any(c["chuong"] for c in chunks)
    cleaned = []
    for c in chunks:
        body = "\n".join(c.pop("lines")).strip()
        body = re.sub(r"\.{4,}\s*\d+", "", body).strip()
        # Loai muc luc: tieu de co dau cham dan trang, hoac ca khoi muc luc dinh thanh 1 dong.
        if re.search(r"\.{4,}", c["heading"]) or len(c["heading"]) > 200:
            continue
        # Loai phan quyet dinh bia (Dieu 1/2 cua QD ban hanh, dung truoc CHUONG I):
        # moi Dieu cua quy che thuc su deu nam trong mot CHUONG.
        if has_chapters and not c["chuong"]:
            continue
        if len(body) < 60:
            continue
        cleaned.append({**c, "text": body})
    return cleaned


def chunk_by_heading(pages: list[str], meta: dict) -> list[dict]:
    """Chunker cho tai lieu KHONG co cau truc Dieu (vd So tay sinh vien).

    So tay la tai lieu thiet ke, moi muc mo dau bang mot dong IN HOA
    (vd "KY TUC XA BACH KHOA") -> dung dong in hoa lam ranh gioi chunk.
    Khong tim duoc tieu de nao thi lui ve chunk theo trang.
    """
    heading_re = re.compile(r"^[^a-z]{6,80}$")
    chunks, current = [], None

    for page_no, page in enumerate(pages, start=1):
        for line in page.splitlines():
            text = line.strip()
            if not text:
                continue
            if heading_re.match(text) and sum(ch.isalpha() for ch in text) >= 5:
                if current and len("\n".join(current["lines"]).strip()) >= 120:
                    chunks.append(current)
                current = {**meta, "chuong": "", "dieu_no": "",
                           "heading": text.title(), "page_no": page_no, "lines": []}
                continue
            if current is None:
                current = {**meta, "chuong": "", "dieu_no": "",
                           "heading": f"Trang {page_no}", "page_no": page_no, "lines": []}
            current["lines"].append(text)

    if current:
        chunks.append(current)

    out = []
    for c in chunks:
        body = "\n".join(c.pop("lines")).strip()
        if len(body) < 120:
            continue
        out.append({**c, "text": body})
    return out


def split_by_khoan(chunk: dict) -> list[dict]:
    """Chia mot Dieu qua dai thanh cac khoan, voi 2 chot an toan.

    Chot 1 - so khoan phai LIEN TIEP: chan cac dong bang danh so kieu "2.7", "3.1"
    (trong Dieu 4 cua XTTN 2026 co han mot bang diem thanh tich danh so nhu vay)
    va chan ca truong hop van ban goc danh trung so khoan (HUST co 2 khoan cung
    so "4" trong Dieu 4).

    Chot 2 - moi chunk con mang theo tieu de Dieu cha, de tach nho ma khong mat
    ngu canh (dung dieu PRD muc 11.2 lo ngai).
    """
    text = chunk["text"]
    if len(text) <= MAX_CHUNK_CHARS:
        return [chunk]

    lines = text.splitlines()
    bounds, expected = [], 1
    for i, line in enumerate(lines):
        m = KHOAN_RE.match(line)
        if m and int(m.group(1)) == expected:
            bounds.append((i, expected))
            expected += 1

    if len(bounds) < 2:  # khong tach duoc an toan -> giu nguyen
        return [chunk]

    children = []
    for idx, (start, khoan_no) in enumerate(bounds):
        end = bounds[idx + 1][0] if idx + 1 < len(bounds) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        if not body:
            continue
        title = re.sub(r"^\d+\.\s*", "", lines[start]).strip()
        heading = f"{chunk['heading']} - Khoan {khoan_no}: {title[:70]}"
        children.append({
            **{k: v for k, v in chunk.items() if k not in ("text", "heading")},
            "heading": heading,
            "khoan_no": str(khoan_no),
            # cau context o dau text de retrieval trung khoan ma van biet thuoc Dieu nao
            "text": f"[{chunk['heading']}]\n{body}",
        })

    # phan dau Dieu truoc khoan 1 (neu co) gan vao chunk dau tien
    head_text = "\n".join(lines[: bounds[0][0]]).strip()
    if head_text and children:
        children[0]["text"] = f"[{chunk['heading']}]\n{head_text}\n{children[0]['text'].split(chr(10), 1)[1]}"
    return children


def write_markdown(chunks: list[dict], stem: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path, jsonl_path = OUT_DIR / f"{stem}.md", OUT_DIR / f"{stem}.chunks.jsonl"

    meta = chunks[0]
    header = [
        f"# {meta['document_title']}",
        "",
        f"> Số hiệu: {meta['document_no'] or '—'} · Năm: {meta['year']}",
        f"> Nguồn: {meta['source_url']}",
        "",
    ]
    body, last_chuong = [], None
    for c in chunks:
        if c["chuong"] and c["chuong"] != last_chuong:
            body += [f"## {c['chuong']}", ""]
            last_chuong = c["chuong"]
        body += [f"### {c['heading']}", "", f"*(trang {c['page_no']})*", "", c["text"], ""]

    md_path.write_text("\n".join(header + body), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"  {md_path.name}: {len(chunks)} chunk (điều) -> kèm {jsonl_path.name}")


if __name__ == "__main__":
    for filename, meta in DOCS.items():
        pdf = ADMISSION / filename
        print(f"{filename}")
        if not pdf.exists():
            print("  [BỎ QUA] không tìm thấy file")
            continue
        pages = (extract_pages_bold(pdf) if meta.get("layout") == "bold_headings"
                 else extract_pages(pdf))
        if meta.get("stop_at"):
            pages = cut_at(pages, meta["stop_at"])
        if sum(len(p.strip()) for p in pages) < 500:
            print("  [BỎ QUA] PDF scan, không có text layer -> cần transcribe bằng vision")
            continue
        chunks = chunk_by_dieu(pages, meta)
        if not chunks:
            print(f"  không có cấu trúc Điều -> chunk theo tiêu đề mục ({len(pages)} trang)")
            chunks = chunk_by_heading(pages, meta)
        if not chunks:
            print("  [CẢNH BÁO] không chunk được -> cần xử lý riêng")
            continue
        before = len(chunks)
        chunks = [c for parent in chunks for c in split_by_khoan(parent)]
        if len(chunks) != before:
            print(f"  chia {len(chunks) - before} chunk theo khoản (Điều > {MAX_CHUNK_CHARS} ký tự)")
        write_markdown(chunks, pdf.stem.replace(" ", "_"))
