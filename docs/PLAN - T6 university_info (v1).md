# PLAN — T6 `university_info`: thông tin Trường/Khoa (v1)

**Ngày:** 2026-10-09 · **Trạng thái:** anh duyệt 2026-10-09 (điểm 4: không thêm ghi chú TROY), **đã thực hiện 2026-10-09** — xem mục "Đã thực hiện" · Bước 6 của `PLAN - Tools (v1).md` mục 9 · Dùng lại khung: `ToolResult`, `ToolContext`, `tools/common.py`, Entity Resolution

Mỗi quyết định có dòng **Vì sao**. Các con số trong file lấy từ Postgres ngày 2026-10-09.

**Tóm tắt:** T6 trả lời "Trường/Khoa X ở đâu, số điện thoại, email, website/fanpage, gồm những khoa/bộ môn/trung tâm nào, đào tạo những ngành nào" và "ngành Y thuộc Trường nào, liên hệ ai". Đây cũng là nguồn **link kênh thông tin chính thức** cho câu hỏi thông báo (AC9). Phần giới thiệu dài (lịch sử, thế mạnh, định hướng) vẫn do RAG (T7) trả lời.

---

## 1. T6 trả lời câu nào — và KHÔNG trả lời câu nào

| Trả lời | Ví dụ |
|---|---|
| Liên hệ: điện thoại, email, địa chỉ văn phòng | "Viện CNTT ở đâu?" (ví dụ PRD 10.1), "Số điện thoại Trường Kinh tế?" |
| Kênh thông tin chính thức (website) | "Trường CNTT&TT có thông báo gì mới?" → trả **link**, không bịa nội dung (PRD 13.2, AC9) |
| Đơn vị trực thuộc (khoa, bộ môn, trung tâm) | "Trường Điện - Điện tử gồm những khoa nào?" |
| Danh sách ngành của Trường/Khoa theo năm | "Trường Kinh tế đào tạo những ngành nào?" |
| Ngành thuộc Trường nào, liên hệ tư vấn ngành | "Ngành Toán Tin thuộc khoa nào, liên hệ ở đâu?" |
| Tên cũ → tên mới | "Viện Điện tử - Viễn thông giờ là trường nào?" |

| **Không** trả lời | Ai trả lời | Vì sao |
|---|---|---|
| Giới thiệu, lịch sử, thế mạnh, việc làm (Q106, Q109) | T7 RAG (chunk `gioi_thieu_truong_khoa`, lọc `faculty_code`) | Văn xuôi dài (PRD 3.1.D) |
| Nội dung thông báo, tin tức mới | Không ai — chỉ trả link (`official_channel_url`) | PRD 4.5: MVP không crawl thông báo theo thời gian thực |
| Điểm chuẩn, học phí, chỉ tiêu của ngành | T1–T4 | Mỗi con số chỉ có một đường lấy |

---

## 2. Dữ liệu có gì — và thiếu gì

| Bảng | Nội dung | Ghi chú |
|---|---|---|
| `faculties` (10 dòng) | Mã, tên, điện thoại, email, địa chỉ, `official_channel_url`, `contact_source_url` | Anh đã soát tay (`manual_verified`, 2026-10-05). Có Trường ghi nhiều số điện thoại (anh chốt giữ đủ); Trường Kinh tế có số riêng "093 898 3868 (riêng chương trình TROY)" |
| `faculty_units` (34 dòng) | Đơn vị trực thuộc: `khoa` / `bo_mon` / `trung_tam` | **SEM, SOFL chưa có** đơn vị trực thuộc trong dữ liệu |
| `programs` + `program_years` | Ngành nào thuộc Trường nào, năm nào | Vd SEM 2025: 8 ngành (có EM4, TROY-BA); 2026: 7 ngành (có EM-E17). TROY-IT thuộc **FAMI** (theo trang ngành) |
| `entity_aliases` loại `faculty` | Tên viết tắt, tên cũ "Viện …" | Vd SEEE: "Viện Điện", "Viện Điện tử - Viễn thông" |

---

## 3. Đầu vào

```python
class UniversityInfoInput(BaseModel):
    faculties: list[str] = []         # 0–3 Trường/Khoa (tên, mã, tên cũ)
    programs: list[str] = []          # 0–3 ngành -> tra Trường/Khoa quản lý
    fields: list[Literal["contact", "channel", "units", "programs"]] = []   # rỗng = tất cả
    year: int | None = None           # năm của danh sách ngành; rỗng = năm mới nhất (2026)
```

Không nêu Trường/Khoa lẫn ngành → trả **cả 10** Trường/Khoa (vd "Bách khoa có những trường, khoa nào?", hoặc lấy toàn bộ link kênh thông tin).

## 4. Đầu ra

```python
class Contact(BaseModel):
    phones: list[str]                 # tách theo ";", giữ đủ số và chú thích trong ngoặc
    email: str | None; address: str | None
    source: Source                    # trang ngành có mục "Đơn vị quản lý"

class Unit(BaseModel):    unit_name: str; unit_type: str; unit_type_label: str   # "Khoa" | "Bộ môn" | "Trung tâm"
class ProgramRef(BaseModel): program_code: str; program_name: str; program_group_code: str | None

class FacultyInfo(BaseModel):
    faculty_code: str; faculty_name: str
    former_names: list[str]           # tên cũ "Viện …" (alias old_name)
    official_channel_url: str | None  # kênh thông tin chính thức (AC9)
    contact: Contact | None
    units: list[Unit]
    programs_year: int | None; programs: list[ProgramRef]
    asked_programs: list[str]         # ngành người dùng hỏi mà thuộc Trường/Khoa này

class UniversityInfoData(BaseModel): faculties: list[FacultyInfo]; notes: list[str]
```

**Ví dụ thật** — `programs=["Toán Tin"]`:

```json
{"status": "ok", "data": {"faculties": [{
  "faculty_code": "FAMI", "faculty_name": "Khoa Toán - Tin", "former_names": [],
  "official_channel_url": "https://fami.hust.edu.vn/",
  "contact": {"phones": ["024 3869 2137", "024 3868 2470"], "email": "fami@hust.edu.vn",
              "address": "Phòng 101, Nhà C9, ĐHBK Hà Nội"},
  "units": [{"unit_name": "...", "unit_type": "bo_mon", "unit_type_label": "Bộ môn"}, "..."],
  "programs_year": 2026, "programs": ["MI-E22", "MI1", "MI2", "TROY-IT"],
  "asked_programs": ["MI1"]}]},
 "resolved": [{"mention": "Toán Tin", "codes": ["MI1"]}]}
```

> Câu trả lời mong muốn: *"Ngành Toán - Tin (MI1) thuộc **Khoa Toán - Tin**. Liên hệ: Phòng 101, Nhà C9, ĐHBK Hà Nội; điện thoại 024 3869 2137 hoặc 024 3868 2470; email fami@hust.edu.vn; website https://fami.hust.edu.vn/."*

---

## 5. Quá trình xử lý và quyết định

**Quá trình:**
1. Kiểm: quá 3 Trường/Khoa hoặc quá 3 ngành → `invalid`.
2. `faculties` → `resolve(..., "faculty")`. Không tìm thấy → `Missing(entity_not_found)`.
3. `programs` → `resolve(..., "program", year)`, rồi lấy `faculty_code` của ngành (U4).
4. Gộp các Trường/Khoa tìm được (không trùng); không có gì → `not_found`.
5. Lấy các phần trong `fields`; phần thiếu → `Missing(not_collected)`.
6. Nguồn: liên hệ → `contact_source_url` (trang ngành); đơn vị → `faculty_units.source_url`; ngành → nguồn danh mục ngành.

| # | Quyết định | Vì sao |
|---|---|---|
| U1 | Liên hệ **chỉ lấy từ bảng**, không qua RAG | PRD 3.1.D: hỏi địa chỉ, số điện thoại mà đi qua RAG là sai tầng, kết quả không ổn định |
| U2 | Số điện thoại trả **danh sách**, giữ đủ mọi số và chú thích trong ngoặc | Anh đã chốt (2026-10-05): nguồn ghi nhiều hotline thì giữ đủ. Tách danh sách để bot không nối nhầm hai số |
| U3 | `official_channel_url` luôn có trong `fields` mặc định; câu hỏi thông báo chỉ trả link này | AC9: 100% câu ANNOUNCEMENT_QUERY trả đúng link, không bịa nội dung |
| U4 | Hỏi theo ngành mà tên **mơ hồ**: nếu mọi ứng viên **cùng một Trường/Khoa** thì trả luôn, không hỏi lại; khác Trường thì hỏi lại | "Kỹ thuật Ô tô" (TE1 / TE-E2) đều thuộc Trường Cơ khí, hỏi lại là thừa vì câu trả lời như nhau. "Khoa học máy tính" (IT1 thuộc SOICT / TROY-IT thuộc FAMI) thì khác Trường, phải hỏi |
| U5 | Hỏi theo **nhóm ngành** (Elitech…) → `invalid` | Nhóm trải trên nhiều Trường/Khoa (Elitech có ở 7 Trường/Khoa), không có một câu trả lời "thuộc Trường nào" |
| U6 | `former_names` lấy từ alias loại `old_name` | Người dùng hay gọi tên cũ ("Viện Điện"). Bot nói được "Viện Điện nay là Trường Điện - Điện tử" thay vì chỉ trả tên mới làm người hỏi ngỡ ngàng |
| U7 | **Không** trả `contact_note` | Đây là ghi chú nội bộ về chỗ lệch giữa `data/link.md` và trang ngành (anh đã phân xử). Đưa cho LLM dễ làm nó nói lại chỗ lệch như thông tin thật |
| U8 | Danh sách ngành theo **năm** (mặc định 2026) | Danh mục ngành đổi theo năm (PRD 15.1): Trường Kinh tế năm 2026 có EM-E17, không còn EM4, TROY-BA |
| U9 | SEM, SOFL chưa có đơn vị trực thuộc → `units = []` + `Missing(not_collected)` | Nói rõ chưa có dữ liệu, không để bot nói "không có khoa nào" |
| U10 | Nhãn loại đơn vị: `khoa` → "Khoa", `bo_mon` → "Bộ môn", `trung_tam` → "Trung tâm" | Mã nội bộ không đưa ra cho người dùng |

---

## 6. Đáp án mong đợi và test — **anh duyệt từng dòng**

| # | Đầu vào | Đáp án mong đợi |
|---|---|---|
| T6-01 | `faculties=["Trường CNTT&TT"]` | SOICT. Điện thoại ["024 3869 2463"], email vp@soict.hust.edu.vn, địa chỉ "Văn phòng Trường CNTT&TT, Phòng 505, Nhà B1, ĐHBK Hà Nội", website https://soict.hust.edu.vn/; đơn vị: **2 khoa + 7 trung tâm**; ngành 2026: IT-E10, IT-E15, IT-E6, IT-E7, IT-EP, IT1, IT2 |
| T6-02 | `faculties=["Viện Điện"]` | SEEE (Trường Điện - Điện tử), `resolved` ghi khớp tên cũ; `former_names` có "Viện Điện", "Viện Điện tử - Viễn thông" |
| T6-03 | `faculties=["SoICT"]` | SOICT |
| T6-04 | `programs=["Toán Tin"], fields=["contact","channel"]` | FAMI (ví dụ mục 4); `asked_programs = ["MI1"]`; không có `units`, `programs` |
| T6-05 | `programs=["Kỹ thuật Ô tô"]` | Không hỏi lại (TE1, TE-E2 cùng SME) → **Trường Cơ khí**, `asked_programs = ["TE-E2","TE1"]` (U4) |
| T6-06 | `programs=["Khoa học máy tính"]` | `ambiguous`: IT1 (SOICT) / TROY-IT (FAMI) |
| T6-07 | `programs=["TROY-IT"]` | **FAMI** (Khoa Toán - Tin) theo trang ngành |
| T6-08 | `faculties=["Trường Kinh tế"], fields=["contact"]` | 3 số: "024 3869 2304", "024 3868 0791", "093 898 3868 (riêng chương trình TROY)" |
| T6-09 | `faculties=["SEM"], fields=["units"]` | `units = []` + `Missing(not_collected, "đơn vị trực thuộc SEM")`; `partial` |
| T6-10 | `faculties=["Trường Kinh tế"], fields=["programs"]` | 2026: 7 ngành EM-E13, EM-E14, EM-E17, EM1, EM2, EM3, EM5 |
| T6-11 | `faculties=["Trường Kinh tế"], fields=["programs"], year=2025` | 2025: 8 ngành, có EM4 và TROY-BA, chưa có EM-E17 |
| T6-12 | `fields=["channel"]` (không nêu gì) | Cả **10** Trường/Khoa, mỗi Trường có `official_channel_url` (AC9) |
| T6-13 | `programs=["Elitech"]` | `invalid` (U5) |
| T6-14 | `faculties=["Trường Y"]` | `not_found`, `ENTITY_NOT_FOUND` |
| T6-15 | 4 Trường/Khoa | `invalid`, câu PRD 10.2 |
| T6-16 | `faculties=["SOICT"], programs=["IT2"]` | Một Trường (không lặp): SOICT, `asked_programs = ["IT2"]` |
| T6-17 | **Quét toàn bộ** 10 Trường/Khoa | Liên hệ khớp `linking/faculties.csv`; đơn vị khớp `linking/faculty_units.csv`; ngành 2026 khớp `programs_2026.csv` |
| T6-18 | Nguồn của mọi ca | Mọi `source_url` thuộc `hust.edu.vn`; không có trường `contact_note` trong đầu ra (U7) |

---

## 7. File đụng tới

```
backend/app/schemas/university_info.py     mới
backend/app/tools/university_info.py       mới
backend/tests/test_university_info.py      mới: 18 ca mục 6
```

Không sửa dữ liệu nguồn, không sửa `build_db.py`.

## 8. Thứ tự và ước lượng

| Bước | Việc | Ước lượng |
|---|---|---|
| 1 | Schema + tool | ~1 giờ |
| 2 | 18 test | ~45 phút |
| 3 | Ghi "Đã thực hiện", cập nhật tài liệu | ~15 phút |

**Tổng: khoảng 2 giờ.**

---

## 9. Cần anh duyệt

1. **Bảng đáp án mục 6** (18 ca).
2. **U4:** hỏi "ngành X thuộc Trường nào" mà tên ngành mơ hồ nhưng mọi ứng viên cùng một Trường → trả luôn, không hỏi lại.
duyệt
3. **U7:** không đưa `contact_note` (ghi chú nội bộ về chỗ lệch nguồn liên hệ) cho bot.
duyệt
4. **TROY-IT thuộc Khoa Toán - Tin (FAMI)** theo trang ngành, trong khi số điện thoại riêng cho chương trình TROY lại nằm ở Trường Kinh tế (SEM). T6 trả đúng như dữ liệu: hỏi TROY-IT thì ra FAMI. Anh có muốn thêm ghi chú trỏ sang số TROY của SEM không? không

---

# Đã thực hiện (2026-10-09)

Anh duyệt: bảng 18 ca, U4 (mơ hồ cùng Trường thì trả luôn), U7 (không đưa `contact_note`); điểm 4 **không** thêm ghi chú trỏ sang số TROY của SEM.

## Kết quả

| Việc | Kết quả |
|---|---|
| Tool | `app/schemas/university_info.py`, `app/tools/university_info.py` |
| Test | `backend/tests/test_university_info.py` **18/18** ca đã duyệt xanh, gồm quét đủ 10 Trường/Khoa (liên hệ, đơn vị, ngành 2026 khớp CSV) |
| Tổng | `pytest backend` **270 passed**; `pyflakes` sạch; `validate_aliases` 0/0; AC2/AC8 vẫn 100% |

## Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| **Sửa Entity Resolution (fuzzy)** | Bỏ các chữ đầu chung "trường", "khoa", "viện", "ngành" ở **cả hai phía** trước khi chấm fuzzy; phần còn lại dưới 4 ký tự thì không đoán | Ca T6-14 bắt được: "Trường Y" được 86 điểm với mọi "Trường …" chỉ nhờ chữ "trường" → ra hỏi lại giữa 3 Trường. Kiểm thêm thấy **"Trường Luật" bị đoán thành Trường Vật liệu** ("luật" ~ "liệu"). Sau sửa: cả hai ra `not_found`; lỗi gõ thật vẫn bắt được ("truong vat lieuu" → SMSE, "Ngành Logictics" → EM-E14). Thêm 2 test giữ lại lỗi này |
| Ứng viên khi hỏi lại (U4, khác Trường) | Tên ứng viên kèm Trường/Khoa: "CNTT: Khoa học Máy tính (Trường CNTT&TT)" | Người hỏi "thuộc Trường nào" cần thấy ngay sự khác nhau giữa các ứng viên |
| Nguồn | Liên hệ → trang ngành có mục "Đơn vị quản lý"; đơn vị → trang cơ cấu tổ chức; kênh → chính website đó | Bảng `faculties` không có cột năm nên không dùng `row_source` chung |
| Không nêu gì | Trả cả 10 Trường/Khoa | Câu "Bách khoa có những trường, khoa nào" và lấy toàn bộ link kênh thông tin (AC9) |
