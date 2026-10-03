"""Trich Sổ tay sinh viên 2026 sang chunk RAG, theo dung bo cuc in.

Vi sao can script rieng (khong dung chung pdf_to_rag_md.py):
  1. PDF la TRANG DOI: moi trang PDF = 2 trang in (trai/phai), so trang in 2..109.
     Ban cu ghi page_no = so trang PDF (1..55) -> sinh vien mo so tay khong tim thay.
  2. Moi nua trang lai chia 2 COT, co trang 2 cot doc lap (46/145 tieu de muc nam o
     cot phai). Ban cu doc theo thu tu luong PDF, khong theo vi tri -> chunk "Cách thức
     và quy trình" ra buoc 1, 4, 2, 3 va lan ca cau cua muc khac vao giua.
  3. Co 3 cap tieu de: PHẦN (theo muc luc) > tieu de trang (co chu ~29) > tieu de muc
     (dong IN HOA co 8). Ban cu chi lay cap muc, mat het ngu canh cha.
  4. Ban cu viet hoa kieu title() -> "KếT Quả RèN LuyệN", "Clb". Nay giu nguyen chu in.
  5. Bang khung diem ren luyen bi ep phang thanh day so ("Mc Mc Mc"). Nay dung
     find_tables() va ghi thanh bang markdown, giu nguyen hang.

Dung: python scripts/sotay_to_rag.py
"""

import json
import re
import statistics
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "data" / "raw" / "admission" / "So tay sinh vien_2026.pdf"
OUT_DIR = ROOT / "data" / "rag" / "raw_chunks"
STEM = "So_tay_sinh_vien_2026"

META = {
    "document_title": "Sổ tay sinh viên 2026",
    "document_no": "",
    "document_type": "so_tay_sinh_vien",
    "year": 2026,
    "source_url": "https://ctsv.hust.edu.vn/so-tay-sv",
}

# Muc luc (trang in 6): khoang trang in -> PHAN. Trang 1-6 la bia, loi ngo, muc luc.
PARTS = [
    (1, 6, "Giới thiệu"),
    (7, 47, "Phần 01 – Quy chế, quy định, thủ tục cần nắm vững"),
    (48, 53, "Phần 02 – Đảng ủy, Chi bộ sinh viên, Đoàn Thanh niên, Hội Sinh viên"),
    (54, 57, "Phần 03 – Ban, Trung tâm"),
    (58, 68, "Phần 04 – Trường, Khoa đào tạo"),
    (69, 78, "Phần 05 – Bộ quy tắc ứng xử văn hóa sinh viên Bách khoa"),
    (79, 109, "Phần 06 – Chia sẻ kinh nghiệm"),
]
# 6 = muc luc; con lai la trang BIA cua tung Phan (chi ghi ten Phan + ten cac muc con,
# da co san trong tien to [Phan › ...] cua moi chunk) -> truoc day bi noi thanh tieu de
# rac "PHAN 2 › DANG UY › CHI BO SINH VIEN ..." gan vao muc cuoi cua Phan truoc.
# 1, 83, 90, 93, 100, 105 = trang bia muc chi co chu trang tri ("O tro", "GIAO THONG /
# DI LAI Nhung dieu can biet!!!", "MUC TIEU Tuong lai PHUONG HUONG"...): trang sau da co
# tieu de rieng, giu lai chi sinh chunk rong nghia.
SKIP_PRINTED_PAGES = {6, 7, 48, 54, 58, 69, 1, 83, 90, 93, 100, 105}
# Nhan canh ma QR ("Thong tin / chi tiet / xem tai day"): duong dan nam trong anh QR,
# chu nay dung rieng khong mang thong tin.
QR_LABEL = re.compile(r"\n?Thông tin\s*\n\s*chi tiết\s*\n\s*xem tại đây")

H1_MIN_SIZE = 16.0
H1_MAX_TOP = 160.0   # tieu de trang luon nam trong vung dau trang (y < 160pt)
# Tieu de muc co nhieu co chu: 6,8 (ten bang khung ren luyen), 8 (pha bien nhat),
# 12-13 (trang mo hinh dao tao). Tieu de to hon 16 la tieu de trang.
H2_SIZE = (6.5, 15.9)
LIST_MARK = re.compile(r"^([0-9]{1,2}[.)]|[-–•+✓*]|[a-zđ][)]|[IVX]+[.)])[ ]")
MAX_CHUNK_CHARS = 2400
TABLE_MIN_ROWS, TABLE_MIN_COLS = 4, 3   # bang nho hon la khung trang tri


def part_of(page: int) -> str:
    for lo, hi, name in PARTS:
        if lo <= page <= hi:
            return name
    return ""


def fix_letter_spacing(line: dict) -> str:
    """'S I N H V I Ê N C ẦN' -> 'SINH VIÊN CẦN' dua vao khoang cach giua cac ky tu."""
    chars = [c for s in line["spans"] for c in s["chars"] if c["c"].strip()]
    if len(chars) < 4:
        return "".join(c["c"] for s in line["spans"] for c in s["chars"])
    gaps = [b["bbox"][0] - a["bbox"][2] for a, b in zip(chars, chars[1:])]
    base = statistics.median(gaps)
    out = chars[0]["c"]
    for gap, ch in zip(gaps, chars[1:]):
        if gap > max(base * 1.8, base + 1.5):
            out += " "
        out += ch["c"]
    return out


# Font dung chu ghep (ligature): "ti" duoc ve bang mot glyph, trich ra thanh "Ɵ"
# ("Danh gia Ɵen do"). Quet ca tai lieu chi gap 1 cho, nhung giu bang de an toan.
LIGATURES = {"Ɵ": "ti", "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff"}


def fix_ligatures(text: str) -> str:
    for bad, good in LIGATURES.items():
        text = text.replace(bad, good)
    return text


def line_text(line: dict) -> str:
    # Mot so trang (vd 50-51) luu chu o dang TO HOP (NFD: "a" + dau rieng) -> nhin giong
    # het nhung khong khop khi tim kiem voi cau hoi go dang NFC. Chuan hoa ve NFC.
    return unicodedata.normalize("NFC", fix_ligatures(_line_text(line)))


def _line_text(line: dict) -> str:
    raw = "".join(c["c"] for s in line["spans"] for c in s["chars"])
    tokens = raw.split()
    if len(tokens) >= 4 and sum(1 for t in tokens if len(t) == 1) / len(tokens) > 0.6:
        return fix_letter_spacing(line)
    return re.sub(r"\s+", " ", raw).strip()


def is_icon_glyph(text: str) -> bool:
    """Dong rac sinh ra tu FONT BIEU TUONG (icon): "ln ms", "eqhr", "rtm", "'s".

    La ma ky tu cua cac hinh ve, khong phai chu. Dau hieu: rat ngan, toan chu Latin
    khong dau, khong co so, khong phai tu viet tat in hoa.
    """
    compact = text.replace(" ", "")
    if len(compact) == 1 and compact.isalpha():
        return True    # chu cai trang tri le loi ("L" o trang hoc bong gan ket que huong)
    if not 1 <= len(compact) <= 6 or any(ch.isdigit() for ch in compact):
        return False
    if compact.isupper():
        return False
    return all(ord(ch) < 128 or ch in "‘’" for ch in compact)


def is_upper_line(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and all(not c.islower() for c in letters)


def collect_half(page, x0: float, x1: float) -> tuple[str, list[dict]]:
    """Tra ve (so trang in, cac muc) cua mot nua trang."""
    H = page.rect.height
    raw = page.get_text("rawdict")
    tables = [t for t in page.find_tables().tables
              if t.row_count >= TABLE_MIN_ROWS and t.col_count >= TABLE_MIN_COLS
              and x0 <= (t.bbox[0] + t.bbox[2]) / 2 < x1]

    def inside_table(bbox) -> bool:
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        return any(t.bbox[0] <= cx <= t.bbox[2] and t.bbox[1] <= cy <= t.bbox[3] for t in tables)

    printed, items = "", []
    for block in raw["blocks"]:
        for line in block.get("lines", []):
            bbox = line["bbox"]
            if not (x0 <= (bbox[0] + bbox[2]) / 2 < x1):
                continue
            text = line_text(line)
            if not text:
                continue
            if text.isdigit() and bbox[1] > H - 40:
                printed = text          # so trang in o chan trang
                continue
            if inside_table(bbox):
                continue
            if is_icon_glyph(text):
                continue
            size = max(s["size"] for s in line["spans"])
            color = line["spans"][0]["color"]
            items.append({"bbox": bbox, "text": text, "size": size, "color": color})

    for t in tables:
        rows = [[re.sub(r"\s+", " ", c or "").strip() for c in r] for r in t.extract()]
        rows = [r for r in rows if any(r)]
        items.append({"bbox": t.bbox, "text": "", "size": 0, "table": rows})
    return printed, items


DECOR_ONLY = re.compile(r"^[\s\"“”‘’'«»!.…]*$")


def classify(item: dict) -> str:
    if item.get("table"):
        return "table"
    text, size = item["text"], item["size"]
    # Dau ngoac kep trang tri co chu rat lon (trang "Viec lam them") -> khong phai tieu de
    if DECOR_ONLY.match(text):
        return "decor"
    digits = sum(c.isdigit() for c in text)
    if size >= H1_MIN_SIZE and digits < len(text) / 2:
        # Chu to o DAU trang la tieu de trang; chu to o giua trang la nhan muc
        # ("CAN BO GIANG VIEN", "BAN CO VAN HOC TAP" o cac trang Truong/Khoa, y ~255).
        # Gop ca vao tieu de trang se lam dong lien he co van hoc tap mat nhan.
        return "h1" if item["bbox"][1] < H1_MAX_TOP else "h2"
    if (H2_SIZE[0] <= size <= H2_SIZE[1] and is_upper_line(text)
            and not text.rstrip().endswith(",") and len(text) >= 6):
        return "h2"
    return "body"


def demote_continuations(items: list[dict]) -> None:
    """Dong in hoa nam GIUA CAU khong phai tieu de.

    Vd "... cac CLB (BK-AMC," / "HUST-SMARTCAR, BK-UAV, AI-CLUB, GW" / "Club, GFC, SEP).":
    dong giua toan chu in hoa (ten viet tat) nen bi xep la tieu de muc. Neu dong ngay
    phia tren cung cot ket thuc bang dau phay, gach noi, mo ngoac hoac chu thuong
    (cau chua xong) thi dong in hoa nay la phan tiep theo cua cau.
    """
    bodies = [i for i in items if i["kind"] == "body" and i["text"]]
    for it in items:
        if it["kind"] != "h2":
            continue
        for b in bodies:
            h = max(1.0, b["bbox"][3] - b["bbox"][1])
            gap = it["bbox"][1] - b["bbox"][3]
            if abs(it["bbox"][0] - b["bbox"][0]) < 40 and -2 <= gap < h * 0.8:
                tail = b["text"].rstrip()[-1:]
                if tail in ",(-–" or tail.islower():
                    it["kind"] = "body"
                    break


def promote_heading_tails(items: list[dict]) -> None:
    """Dong cuoi cua tieu de muc qua ngan ("...THAC SI KHOA" / "HOC") khong dat nguong
    do dai nen bi xep vao than bai. Neu no in hoa, cung co/mau va nam sat ngay duoi
    mot tieu de muc thi day la phan duoi cua tieu de do."""
    heads = [i for i in items if i["kind"] == "h2"]
    for it in items:
        if it["kind"] != "body" or not it["text"] or any(ch.islower() for ch in it["text"]):
            continue
        if not any(ch.isalpha() for ch in it["text"]) or len(it["text"]) > 60:
            continue
        for h in heads:
            gap = it["bbox"][1] - h["bbox"][3]          # dong nay nam DUOI tieu de
            gap_up = h["bbox"][1] - it["bbox"][3]       # dong nay nam TREN tieu de
            same_style = (abs(it["size"] - h["size"]) <= 0.6 and it.get("color") == h.get("color"))
            if abs(it["bbox"][0] - h["bbox"][0]) < 25 and same_style and (
                    -4 <= gap < 6
                    # "TRIET HOC MAC-LENIN, KTCT MAC-LENIN," / "CHU NGHIA XA HOI KHOA HOC":
                    # dong dau cua tieu de ket thuc bang dau phay nen bi loai khoi h2
                    or (-4 <= gap_up < 6 and it["text"].rstrip().endswith(","))):
                it["kind"] = "h2"
                break


def merge_multiline(items: list[dict], kind: str) -> list[dict]:
    """Tieu de xuong dong ('TRUNG TAM SANG TAO VA' + 'KHOI NGHIEP SINH VIEN') -> 1 muc."""
    # Hai cot co the co tieu de o CUNG do cao ("DAM BAO DIEU KIEN" | "TU DANH GIA KET
    # QUA") -> phai so voi tieu de gan nhat CUNG COT, khong phai muc vua xet.
    # Dong thu hai cua tieu de thuong CHONG len dong dau ~3pt (khoang cach am).
    items = sorted(items, key=lambda i: (i["bbox"][1], i["bbox"][0]))
    out: list[dict] = []
    for it in items:
        target = None
        for prev in reversed(out):
            if abs(it["bbox"][0] - prev["bbox"][0]) < 25:
                target = prev
                break
        # Chi gop khi CUNG kieu chu: banner "LAP KE HOACH HOC TAP TOAN KHOA" va tieu de
        # con "THIET LAP ... PHU HOP VOI:" nam sat nhau nhung khac co/mau -> 2 tieu de.
        if target is not None and (abs(target["size"] - it["size"]) > 0.6
                                   or target.get("color") != it.get("color")):
            target = None
        if target is not None:
            h = target["bbox"][3] - target["bbox"][1]
            gap = it["bbox"][1] - target["bbox"][3]
            if -h * 0.6 <= gap < h * 1.2:
                target["text"] += " " + it["text"]
                target["bbox"] = (min(target["bbox"][0], it["bbox"][0]), target["bbox"][1],
                                  max(target["bbox"][2], it["bbox"][2]), it["bbox"][3])
                continue
        out.append(dict(it))
    return out


def order_half(items: list[dict], x0: float, x1: float) -> list[dict]:
    """Xep thu tu doc cua mot nua trang: gan moi dong vao tieu de muc so huu no.

    Cot duoc xac dinh bang vi tri bat dau cua dong so voi giua nua trang.
    - Neu cot phai KHONG co tieu de muc rieng: dong o cot phai thuoc tieu de gan nhat
      phia tren O BAT KY COT NAO (vd "Phan loai ket qua ren luyen": tieu de o cot
      trai, danh sach tran sang cot phai).
    - Neu cot phai CO tieu de rieng: hai cot doc lap, moi dong thuoc tieu de gan nhat
      phia tren trong CUNG cot.
    Trong moi muc: doc het cot trai roi moi sang cot phai, tren xuong duoi.
    """
    mid = column_split(items, x0, x1)

    def col(it) -> int:
        return 0 if it["bbox"][0] < mid else 1

    heads = [i for i in items if i["kind"] == "h2"]
    rest = [i for i in items if i["kind"] in ("body", "table")]
    independent = any(col(h) == 1 for h in heads)

    def owner(it):
        cands = [h for h in heads if h["bbox"][1] <= it["bbox"][1] + 2
                 and (not independent or col(h) == col(it))]
        if not cands and independent:
            cands = [h for h in heads if h["bbox"][1] <= it["bbox"][1] + 2]
        return max(cands, key=lambda h: h["bbox"][1]) if cands else None

    groups: dict[int, list[dict]] = {id(h): [] for h in heads}
    lead: list[dict] = []           # phan dau nua trang, truoc tieu de muc dau tien
    for it in rest:
        h = owner(it)
        (groups[id(h)] if h else lead).append(it)

    def colmajor(lst):
        rows = as_rows(lst)
        if rows:
            return rows
        return sorted(lst, key=lambda i: (col(i), i["bbox"][1], i["bbox"][0]))

    # Xep muc theo do cao truoc, cot sau (hai tieu de cung hang: trai truoc). Noi dung
    # van gan theo cot nen xep xen ke cac muc khong lam tron noi dung giua cac muc.
    heads_sorted = sorted(heads, key=lambda h: (round(h["bbox"][1] / 12), col(h)))
    out = join_paragraphs(colmajor(lead), col)
    for h in heads_sorted:
        out.append(h)
        out.extend(join_paragraphs(colmajor(groups[id(h)]), col))
    return out


def column_split(items: list[dict], x0: float, x1: float) -> float:
    """Tim ranh gioi 2 cot tu khe trong giua cac vi tri DAU DONG.

    Ban dau dung diem giua co dinh (48% be rong nua trang). Sai o cac trang cot trai
    hep: "Hoc bong gan ket que huong" co cot phai bat dau x~198 trong khi diem giua la
    201 -> hai tieu de dat canh nhau bi coi la cung mot cot. Nay lay khe lon nhat giua
    cac gia tri x dau dong (moi ben phai co du dong), khong co khe > 90pt thi coi la 1 cot.
    """
    # Chi tinh dong co CHU dang ke: cot so thu tu tron (1..6) nam le trai o trang
    # "Quy dinh sinh vien can luu y" khong phai mot cot noi dung.
    # Bo qua dong THUT VAO vi co so lon dung ben trai ("01" co 40 o trang Ung xu qua
    # thu dien tu: 4 dong dau thut sang x=93, cac dong sau ve x=43) — do la chu chay
    # vong quanh so, khong phai cot thu hai. Thu phep "dong trai vat qua ranh gioi"
    # truoc do: sai vi tinh tren ca nua trang, lam hong trang co dai toan chieu rong.
    drops = [i for i in items if i["size"] >= 20 and i["text"].strip().isdigit()]

    def beside_drop(it) -> bool:
        return any(d["bbox"][2] <= it["bbox"][0] <= d["bbox"][2] + 60
                   and d["bbox"][1] - 4 <= it["bbox"][1] <= d["bbox"][3] + 4 for d in drops)

    starts = sorted(round(i["bbox"][0]) for i in items
                    if i["kind"] in ("body", "h2") and len(i["text"]) >= 12
                    and not beside_drop(i))
    if len(starts) < 4:
        return x1
    best_gap, cut = 0.0, x1
    for a, b in zip(starts, starts[1:]):
        left = sum(1 for s in starts if s <= a)
        right = len(starts) - left
        if b - a > best_gap and left >= 2 and right >= 2:
            best_gap, cut = b - a, (a + b) / 2
    # Cot that trong so tay cach nhau ~150-230pt; thut le danh sach con chi 30-70pt.
    return cut if best_gap > 90 else x1


def as_rows(items: list[dict]) -> list[dict] | None:
    """Nhan dien bang KHONG ke o (vd "Phong | Chuc nang" o thu vien) va giu theo hang.

    Neu xep theo cot se in het so phong roi moi den ten phong -> mat cap
    "102 -> Phong muon sach tham khao". Dau hieu cua bang: nhieu hang, moi hang co
    >= 2 o ngan nam THANG HANG NGANG, va cac hang CACH XA nhau (> 2 lan chieu cao dong).
    Van xuoi 2 cot cung co dong thang hang, nhung cac dong xep sat nhau (~1 lan) —
    do la cai phan biet, khong phai do dai dong.
    """
    body = [i for i in items if i["kind"] == "body"]
    if len(body) < 6 or len(body) != len(items):
        return None
    rows: list[list[dict]] = []
    for it in sorted(body, key=lambda i: i["bbox"][1]):
        if rows and abs(it["bbox"][1] - rows[-1][0]["bbox"][1]) <= 3:
            rows[-1].append(it)
        else:
            rows.append([it])
    multi = [r for r in rows if len(r) >= 2 and all(len(c["text"]) < 60 for c in r)]
    if len(multi) < 3 or len(multi) < 0.6 * len(rows):
        return None
    tops = [r[0]["bbox"][1] for r in rows]
    line_h = statistics.median(i["bbox"][3] - i["bbox"][1] for i in body)
    if statistics.median(b - a for a, b in zip(tops, tops[1:])) < 2 * line_h:
        return None
    out = []
    for r in rows:
        r = sorted(r, key=lambda c: c["bbox"][0])
        out.append({**r[0], "kind": "body", "text": " | ".join(c["text"] for c in r),
                    "row": True})
    return out


def join_paragraphs(items: list[dict], col) -> list[dict]:
    """Noi cac dong bi ngat cung giua cau thanh mot doan.

    PDF xuong dong theo chieu rong cot, nen "Cong thong tin sinh / vien hoac cac kenh"
    la 2 dong. Noi khi: cung cot, khoang cach doc nho hon nua chieu cao dong, va dong
    sau khong bat dau bang dau danh sach. So thu tu dung rieng (vong tron danh so ben
    trai, vd "1") thi gan vao dau dong ngay sau thanh "1. ...".
    """
    widest = {0: 0.0, 1: 0.0}
    for it in items:
        if it["kind"] == "body":
            widest[col(it)] = max(widest[col(it)], it["bbox"][2])
    items = [{**it, "last_bbox": it["bbox"]} for it in items]
    out: list[dict] = []
    for it in items:
        if (it["kind"] != "body" or not out or out[-1]["kind"] != "body"
                or it.get("row") or out[-1].get("row")):
            out.append(dict(it))
            continue
        prev = out[-1]
        if re.fullmatch(r"[0-9]{1,2}", it["text"]):
            out.append(dict(it))    # so thu tu moi -> bat dau muc moi, khong noi vao doan truoc
            continue
        if re.fullmatch(r"[0-9]{1,2}", prev["text"]) and col(prev) == col(it):
            prev["text"] = f"{prev['text']}. {it['text']}"
            prev["bbox"] = it["bbox"]
            prev["last_bbox"] = it["bbox"]
            continue
        line_h = max(1.0, prev["last_bbox"][3] - prev["last_bbox"][1])
        gap = it["bbox"][1] - prev["last_bbox"][3]
        # Chi noi khi dong truoc KEO DAI toi gan le phai cua cot (bi ngat vi het cho).
        # Dong ngan ket thuc giua chung = het mot muc danh sach dang bieu tuong
        # ("Nhan biet ban than" / "Quy tac sap xep thoi gian khoa hoc"), khong duoc noi.
        wrapped = (prev["last_bbox"][2] >= widest[col(prev)] - 18
                   or it["text"][:1].islower())
        # Dong sau bat dau bang CHU THUONG thi chac chan la cau dang do -> cho phep
        # khoang cach dong rong hon (trang "Xu ly ky luat" gian dong lon).
        max_gap = line_h * (1.2 if it["text"][:1].islower() else 0.5)
        if (col(prev) == col(it) and -2 <= gap < max_gap and wrapped
                and not LIST_MARK.match(it["text"])):
            prev["text"] = f"{prev['text']} {it['text']}"
            prev["bbox"] = (prev["bbox"][0], prev["bbox"][1],
                            max(prev["bbox"][2], it["bbox"][2]), it["bbox"][3])
            prev["last_bbox"] = it["bbox"]
            continue
        out.append(dict(it))
    return out


def render(item: dict) -> str:
    if item["kind"] != "table":
        return item["text"]
    rows = item["table"]
    width = max(len(r) for r in rows)
    lines = ["| " + " | ".join(r + [""] * (width - len(r))) + " |" for r in rows]
    lines.insert(1, "|" + "---|" * width)
    return "\n".join(lines)


OVERRIDE_DIR = ROOT / "data" / "raw" / "sotay_overrides"


def load_override(printed: int) -> list[dict] | None:
    """Trang infographic/dong thoi gian/bang khong ke o: thuat toan bo cuc khong dung
    duoc, nen doc anh va chep tay thanh markdown tai sotay_overrides/p<trang>.md.

    Dinh dang: '# ' = tieu de trang, '## ' = tieu de muc, con lai la than bai
    (cac dong lien nhau gop thanh mot doan; bang markdown giu nguyen).
    """
    path = OVERRIDE_DIR / f"p{printed}.md"
    if not path.exists():
        return None
    items, buf = [], []

    def flush():
        if buf:
            items.append({"kind": "body", "text": "\n".join(buf), "page": printed})
            buf.clear()

    in_comment = False
    for line in unicodedata.normalize("NFC", path.read_text(encoding="utf-8")).splitlines():
        # chu thich nhieu dong (<!-- ... -->) la ghi chu cho nguoi, khong dua vao RAG
        if in_comment or line.lstrip().startswith("<!--"):
            in_comment = "-->" not in line
            continue
        if line.startswith("## "):
            flush()
            items.append({"kind": "h2", "text": line[3:].strip(), "page": printed})
        elif line.startswith("# "):
            flush()
            items.append({"kind": "h1", "text": line[2:].strip(), "page": printed})
        elif line.strip():
            buf.append(line.rstrip())
        else:
            flush()
    flush()
    return items


def extract() -> list[dict]:
    """Luong muc theo thu tu doc cua ca cuon so tay."""
    stream = []
    with pymupdf.open(PDF) as doc:
        for page in doc:
            W = page.rect.width
            for x0, x1 in ((0, W / 2), (W / 2, W)):
                printed, items = collect_half(page, x0, x1)
                if not printed or int(printed) in SKIP_PRINTED_PAGES:
                    continue
                override = load_override(int(printed))
                if override is not None:
                    stream.extend(override)
                    continue
                for it in items:
                    it["kind"] = classify(it)
                promote_heading_tails(items)
                demote_continuations(items)
                h1 = merge_multiline([i for i in items if i["kind"] == "h1"], "h1")
                h2 = merge_multiline([i for i in items if i["kind"] == "h2"], "h2")
                others = [i for i in items if i["kind"] in ("body", "table")]
                h1_text = " ".join(i["text"] for i in sorted(h1, key=lambda i: i["bbox"][1]))
                if h1_text:
                    stream.append({"kind": "h1", "text": h1_text, "page": int(printed)})
                for it in order_half(h2 + others, x0, x1):
                    stream.append({"kind": it["kind"], "text": render(it), "page": int(printed)})
    return stream


def build_chunks(stream: list[dict]) -> list[dict]:
    sections, cur, h1 = [], None, ""
    for it in stream:
        if it["kind"] == "h1":
            # Tieu de trang lap lai o ca 2 nua trang doi -> khong mo muc moi
            if it["text"] == h1:
                continue
            h1 = it["text"]
            cur = {"h1": h1, "h2": "", "page": it["page"], "last": it["page"], "parts": []}
            sections.append(cur)
            continue
        if it["kind"] == "h2":
            title = it["text"]
            # Banner khong co than bai rieng ("LAP KE HOACH HOC TAP TOAN KHOA") ngay truoc
            # tieu de nay -> la tieu de CHA, gop vao ngu canh thay vi bo mat.
            if cur and cur["h2"] and not cur["parts"] and cur["page"] == it["page"]:
                title = f"{cur['h2']} › {title}"
                sections.pop()
            cur = {"h1": h1, "h2": title, "page": it["page"], "last": it["page"], "parts": []}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"h1": h1, "h2": "", "page": it["page"], "last": it["page"], "parts": []}
            sections.append(cur)
        cur["parts"].append(it["text"])
        cur["last"] = it["page"]

    # Muc ngan (infographic: "DUONG DAI CO VIET: 35, 44, 51", cac o meo vat) KHONG duoc
    # bo di — ban truoc loc "than < 40 ky tu" va lam mat ca trang diem dung xe bus.
    # Gop cac muc ngan lien nhau cung tieu de trang thanh mot chunk dang "Tieu de: noi dung".
    SMALL = 220
    merged: list[dict] = []
    for s in sections:
        body = QR_LABEL.sub("", "\n".join(s["parts"])).strip()
        # Muc chi co tieu de, khong co chu (trang bia muc "O tro / KHONG CON LA NOI LO",
        # "05 ... BAN NEN" cua trang Hoc nhom) -> chunk rong nghia, chi gay nhieu truy hoi.
        if not re.search(r"[^\W\d_]", body):
            # tieu de khong than bai nam ngay sau muc cung trang (vd ten bai thong diep
            # "VUNG BUOC TRONG KY NGUYEN MOI..." in to o trang 5) -> giu lam dong cua muc truoc
            prev = merged[-1] if merged else None
            if s["h2"] and prev and prev["h1"] == s["h1"] and s["page"] - prev["last"] <= 1:
                prev["parts"].append(s["h2"])
            continue
        line = f"{s['h2']}: {body}" if s["h2"] and body else (s["h2"] or body)
        prev = merged[-1] if merged else None
        if (len(body) < SMALL and prev is not None and prev.get("group")
                and prev["h1"] == s["h1"] and s["page"] - prev["last"] <= 1
                and sum(len(x) for x in prev["parts"]) < MAX_CHUNK_CHARS):
            prev["parts"].append(line)
            prev["last"] = s["last"]
            prev["names"].append(s["h2"])
            continue
        if len(body) < SMALL:
            merged.append({"h1": s["h1"], "h2": s["h2"], "page": s["page"], "last": s["last"],
                           "parts": [line], "group": True, "names": [s["h2"]]})
        else:
            merged.append({**s, "parts": [body]})
    for m in merged:
        if m.get("group") and len([n for n in m["names"] if n]) > 1:
            names = [n for n in m["names"] if n]
            m["h2"] = ", ".join(names[:3]) + (f" và {len(names) - 3} mục khác" if len(names) > 3 else "")

    chunks = []
    for s in merged:
        body = "\n".join(s["parts"]).strip()
        if not body:
            continue
        part = part_of(s["page"])
        path = " › ".join(x for x in (part, s["h1"], s["h2"]) if x)
        heading = " › ".join(x for x in (s["h1"], s["h2"]) if x) or part
        pages = str(s["page"]) if s["last"] == s["page"] else f"{s['page']}-{s['last']}"
        for i, piece in enumerate(split_long(body), 1):
            chunks.append({
                **META,
                "chuong": part, "dieu_no": "", "khoan_no": "",
                "heading": heading + (f" (phần {i})" if len(split_long(body)) > 1 else ""),
                "page_no": pages,
                "text": f"[{path}]\n{piece}",
            })
    return chunks


def split_long(body: str) -> list[str]:
    if len(body) <= MAX_CHUNK_CHARS:
        return [body]
    out, buf, head = [], [], []
    lines = body.split("\n")
    for i, line in enumerate(lines):
        # dong tieu de bang markdown = dong "|...|" ngay truoc dong "|---|"
        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            head = [line, lines[i + 1]]
        elif not line.startswith("|"):
            head = []
        if buf and sum(len(x) for x in buf) + len(line) > MAX_CHUNK_CHARS:
            out.append("\n".join(buf))
            # bang markdown: lap lai dong tieu de bang o manh moi de khong mat nghia cot
            buf = list(head) if line.startswith("|") and not line.startswith("|---") else []
        buf.append(line)
    if buf:
        out.append("\n".join(buf))
    return out


def write(chunks: list[dict]) -> None:
    md = [f"# {META['document_title']}", "", f"> Nguồn: {META['source_url']}", ""]
    last_part = None
    for c in chunks:
        if c["chuong"] != last_part:
            md += [f"## {c['chuong']}", ""]
            last_part = c["chuong"]
        md += [f"### {c['heading']}", "", f"*(trang {c['page_no']})*", "",
               c["text"].split("\n", 1)[1], ""]
    (OUT_DIR / f"{STEM}.md").write_text("\n".join(md), encoding="utf-8")
    with (OUT_DIR / f"{STEM}.chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def coverage(chunks: list[dict]) -> dict[int, list[str]]:
    """Moi dong chu trong PDF phai co mat trong it nhat mot chunk.

    Phep kiem khach quan duy nhat cho loi "thieu muc": khong phu thuoc vao viec toi
    doan dung bo cuc, chi so noi dung. Tra ve {trang in: [dong bi mat]}.
    """
    def n(t: str) -> str:
        return re.sub(r"\s+", "", t).lower()

    blob = n(" ".join(c["text"] + " " + c["heading"] for c in chunks))
    lost: dict[int, list[str]] = {}
    with pymupdf.open(PDF) as doc:
        for page in doc:
            W, H = page.rect.width, page.rect.height
            raw = page.get_text("rawdict")
            for x0, x1 in ((0, W / 2), (W / 2, W)):
                lines, printed = [], ""
                for b in raw["blocks"]:
                    for l in b.get("lines", []):
                        bb = l["bbox"]
                        if not (x0 <= (bb[0] + bb[2]) / 2 < x1):
                            continue
                        t = line_text(l)
                        if t.isdigit() and bb[1] > H - 40:
                            printed = t
                        elif len(n(t)) >= 4:
                            lines.append(t)
                if not printed or int(printed) in SKIP_PRINTED_PAGES:
                    continue
                miss = [t for t in lines if n(t) not in blob]
                if miss:
                    lost[int(printed)] = miss
    return lost


if __name__ == "__main__":
    stream = extract()
    chunks = build_chunks(stream)
    write(chunks)
    lost = coverage(chunks)
    n_lost = sum(len(v) for v in lost.values())
    print(f"Độ phủ: mất {n_lost} dòng ở {len(lost)} trang in")
    for p, v in sorted(lost.items()):
        print(f"  tr.{p:>3}: {len(v):2d} dòng | vd: {v[0][:66]!r}")
    pages = sorted({int(p) for c in chunks for p in str(c["page_no"]).split("-")})
    print(f"{STEM}: {len(chunks)} chunk, {sum(len(c['text']) for c in chunks)} ký tự, "
          f"trang in {pages[0]}-{pages[-1]}")
