# PLAN — T3 `program_info`: thông tin ngành (v1)

**Ngày:** 2026-10-08 · **Trạng thái:** anh duyệt 2026-10-08, **đã thực hiện 2026-10-08** — xem mục "Đã thực hiện" cuối file · Bước 4 của `PLAN - Tools (v1).md` mục 9 · Dùng lại khung đã có: `ToolResult`, `ToolContext`, Entity Resolution (`PLAN - Entity Resolution + Admission Tool (v1)`)

Mỗi quyết định có dòng **Vì sao**.

**Tóm tắt:** T3 trả lời "ngành X là ngành gì, thuộc Trường nào, học bằng tiếng gì, mấy năm, bằng gì, tuyển bao nhiêu, xét những phương thức và tổ hợp nào, điểm tính theo công thức nào". Số liệu lấy từ bảng; phần giới thiệu dài (học gì, ra làm gì) vẫn do RAG (T7) trả lời.

---

## 1. T3 trả lời câu nào — và KHÔNG trả lời câu nào

| Trả lời | Ví dụ trong bộ 120 câu |
|---|---|
| Thông tin chung: tên, Trường/Khoa, nhóm (chuẩn/Elitech/PFIEV/liên kết), ngôn ngữ, bằng, thời gian, link CTĐT, mô tả ngắn | Q63, Q65, Q66 (phần "học bằng tiếng gì, mấy năm"), Q75 |
| Chỉ tiêu của từng ngành | Q36 (tổng chỉ tiêu IT2) |
| Phương thức xét tuyển của ngành, thang điểm | Q39 ("FL2 thang 30 hay 40") |
| Tổ hợp, môn chính, công thức tính điểm | Q10, Q11 |

| **Không** trả lời | Ai trả lời | Vì sao |
|---|---|---|
| Điểm chuẩn | T1 `admission_scores` | Một con số chỉ có một đường lấy. Hai tool cùng trả điểm thì sẽ có lúc lệch nhau |
| Học phí | T4 `tuition_fees` | Học phí có quy tắc bắt buộc riêng: luôn kèm đơn vị và năm áp dụng (PRD 3.1.A) |
| Liên hệ Trường/Khoa | T6 `university_info` | PRD 3.1.D |
| "Học gì, ra trường làm gì" | T7 RAG (chunk trang ngành, lọc theo `program_code`) | Văn xuôi dài, PRD 3.1.C |
| Câu hỏi cả nhóm ("Elitech học bằng tiếng gì?" — Q62) | RAG + T2 | T3 nhận tối đa 3 ngành (mục 5, P8) |

---

## 2. Đầu vào

```python
class ProgramInfoInput(BaseModel):
    programs: list[str]        # cụm người dùng gõ hoặc mã; 1–3 ngành
    years: list[int] = []      # 1–3 năm; rỗng = năm mới nhất (2026)
    fields: list[Literal["overview", "quota", "methods", "combinations"]] = []   # rỗng = tất cả
```

| Trường | Ý nghĩa | Ví dụ |
|---|---|---|
| `programs` | Như T1: nhận mã hoặc tên, tool tự gọi Entity Resolution | `["Toán Tin"]`, `["IT1", "IT2"]` |
| `years` | Năm của chỉ tiêu / phương thức / tổ hợp | `[2025, 2026]` để so chỉ tiêu hai năm |
| `fields` | Chỉ lấy phần cần | Q39 chỉ cần `["methods"]`; Q36 chỉ cần `["quota"]` |

---

## 3. Đầu ra

```python
class Overview(BaseModel):            # theo trang giới thiệu ngành 2026
    language: str | None; degree: str | None; duration: str | None
    curriculum_url: str | None; short_description: str | None
    as_of_year: int                   # = 2026
    source: Source                    # trang ngành ts.hust.edu.vn

class QuotaItem(BaseModel):    year: int; quota: int; quota_type: str; source: Source
class MethodItem(BaseModel):   year: int; method_code: str; method_name: str; scale: int | None
class CombinationItem(BaseModel):
    year: int; method_code: str; combination_code: str; subjects: str
    main_subject: str | None          # "Toán" hoặc None
    formula_type: str                 # mon_chinh_toan | khong_mon_chinh | K01 | DGTD | chua_ro
    main_subject_known: bool          # False khi formula_type = chua_ro
class FormulaItem(BaseModel):   formula_type: str; method_code: str; scale: int; formula: str | None; note: str; source: Source

class ProgramInfo(BaseModel):
    program_code: str; program_name: str
    faculty_code: str; faculty_name: str
    program_group_code: str; program_group_name: str
    open_years: list[int]             # các năm ngành có tuyển
    overview: Overview | None
    quotas: list[QuotaItem]; methods: list[MethodItem]
    combinations: list[CombinationItem]
    formulas: list[FormulaItem]       # mỗi công thức một lần, không lặp theo tổ hợp

class ProgramInfoData(BaseModel): programs: list[ProgramInfo]
```

Đầu ra bọc trong `ToolResult` như T1/T2: `status`, `missing`, `clarifications`, `resolved`, `sources`.

### Ví dụ đầu ra thật — `programs=["IT1"]` (rút gọn chỗ `...`)

```json
{
  "status": "ok",
  "data": {"programs": [{
    "program_code": "IT1", "program_name": "CNTT: Khoa học Máy tính",
    "faculty_code": "SOICT", "faculty_name": "Trường CNTT&TT",
    "program_group_code": "chuan", "program_group_name": "Chương trình chuẩn",
    "open_years": [2024, 2025, 2026],
    "overview": {"language": "Tiếng Việt", "degree": "Cử nhân - Thạc sĩ tích hợp", "duration": "4 - 5,5 năm",
                 "curriculum_url": "https://soict.hust.edu.vn/chuong-trinh-khoa-hoc-may-tinh-ma-tuyen-sinh-it1.html",
                 "short_description": "Ngành Khoa học Máy tính đào tạo nguồn nhân lực trình độ cao ...",
                 "as_of_year": 2026,
                 "source": {"url": "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cntt-khoa-hoc-may-tinh"}},
    "quotas": [{"year": 2026, "quota": 300, "quota_type": "tong_nganh"}],
    "methods": [{"year": 2026, "method_code": "DGTD", "scale": 100},
                {"year": 2026, "method_code": "THPT", "scale": 30},
                {"year": 2026, "method_code": "XTTN", "scale": 100}],
    "combinations": [
      {"method_code": "DGTD", "combination_code": "K00", "subjects": "Tư duy Toán học, Tư duy Đọc hiểu, Tư duy Khoa học/Giải quyết vấn đề", "formula_type": "DGTD"},
      {"method_code": "THPT", "combination_code": "A00", "subjects": "Toán, Vật lý, Hóa học",   "main_subject": "Toán", "formula_type": "mon_chinh_toan"},
      {"method_code": "THPT", "combination_code": "A01", "subjects": "Toán, Vật lý, Tiếng Anh", "main_subject": "Toán", "formula_type": "mon_chinh_toan"},
      {"method_code": "THPT", "combination_code": "K01", "subjects": "Toán , Ngữ văn, Lý/Hóa/Sinh/Tin", "formula_type": "K01"}],
    "formulas": [
      {"formula_type": "mon_chinh_toan", "formula": "ĐX = [(Môn 1 + Môn 2 + Môn 3 + Môn chính) x 3/4] + Điểm ưu tiên", "note": "Tổ hợp có môn chính là Toán (Toán được tính 2 lần)"},
      {"formula_type": "K01", "formula": "ĐX = [(Toán x 3 + Ngữ Văn x 1 + Lý/Hóa/Sinh/Tin x 2) x 1/2] + Điểm ưu tiên"},
      {"formula_type": "DGTD", "formula": "ĐX = (Điểm thi ĐGTD + Điểm thưởng) + Điểm ưu tiên"},
      {"formula_type": "XTTN", "formula": "ĐX = Điểm XTTN + Điểm ưu tiên"}]
  }]},
  "sources": [
    "trang ngành IT1 (thông tin chung, danh sách tổ hợp)",
    "Thông tin tuyển sinh 2026 (chỉ tiêu, phương thức)",
    "Bài công bố điểm chuẩn 2026 (công thức, môn chính)"]
}
```

Câu trả lời mong muốn mà Synthesizer (Tuần 4) dựng từ đầu ra trên, để anh hình dung:

> Ngành **Khoa học Máy tính (IT1)** thuộc Trường CNTT&TT, chương trình chuẩn, học bằng tiếng Việt, 4–5,5 năm (Cử nhân – Thạc sĩ tích hợp). Năm 2026 tuyển **300** chỉ tiêu theo 3 phương thức: điểm thi THPT (thang 30), ĐGTD (thang 100), xét tuyển tài năng (thang 100). Xét THPT các tổ hợp A00, A01 (môn chính Toán, **Toán tính 2 lần**: ĐX = [(Môn 1 + Môn 2 + Môn 3 + Toán) × 3/4] + ưu tiên) và K01 (công thức riêng: Toán × 3 …).
> [Nguồn] Trang ngành IT1 · Thông tin tuyển sinh 2026 · Bài công bố điểm chuẩn 2026

---

## 4. Quá trình xử lý

1. **Kiểm đầu vào**: bỏ trùng. Quá 3 ngành hoặc quá 3 năm → `invalid` với câu PRD 10.2.
2. **Năm**: rỗng → `[2026]`. Năm ngoài 2024–2026 → `Missing(year_out_of_range)`.
3. **Ngành**: `resolve(..., "program", years)` như T1:
   - mơ hồ → `ambiguous` + ứng viên, **không truy vấn**;
   - nhóm ngành → `invalid` + gợi ý dùng `list_programs`;
   - ngành không tuyển năm hỏi → `Missing(program_not_open, available_years)`.
4. **Truy vấn** (mỗi phần một câu SQL, chỉ chạy phần nằm trong `fields`):
   - `programs` ⨝ `faculties` ⨝ `program_groups`: thông tin chung + mô tả ngắn
   - `quotas`: chỉ tiêu theo năm
   - `program_methods` ⨝ `admission_methods`: phương thức + thang điểm
   - `program_combinations` ⨝ `combinations`: tổ hợp, môn chính, `formula_type`
   - `scoring_formulas`: công thức của các `formula_type` vừa gặp, cộng công thức theo phương thức (ĐGTD, XTTN)
5. **Missing theo từng phần** (mục 5, P5–P7).
6. **Nguồn**: mỗi phần gắn nguồn riêng (mục 5, P3).
7. **Trạng thái**: có dữ liệu và không thiếu gì → `ok`; có dữ liệu nhưng thiếu một phần → `partial`; không có gì → `not_found`.

---

## 5. Quyết định

| # | Quyết định | Vì sao |
|---|---|---|
| P1 | T3 **không** trả điểm chuẩn, học phí, liên hệ | Mục 1: mỗi con số chỉ có một đường lấy; học phí có quy tắc bắt buộc riêng (đơn vị, năm) do T4 lo |
| P2 | Thông tin chung (ngôn ngữ, bằng, thời gian, link CTĐT, mô tả ngắn) ghi rõ `as_of_year = 2026` | Dữ liệu này chỉ thu từ trang ngành năm 2026. Hỏi năm 2025 vẫn trả, nhưng phải nói rõ là theo trang ngành hiện tại |
| P3 | **Mỗi phần gắn nguồn riêng.** Danh sách tổ hợp → trang ngành; **môn chính và công thức → bài công bố điểm chuẩn 2026**; chỉ tiêu, phương thức → thông tin tuyển sinh của năm đó | Anh đã chốt: cột môn chính lấy từ tuyensinh247, **không** đưa vào danh sách nguồn, chatbot **không** trích dẫn. Bài điểm chuẩn 2026 là nguồn chính thức của công thức "môn chính Toán tính 2 lần" |
| P4 | Tổ hợp D01 của TROY-IT (`chua_ro`) → `main_subject_known = false`, `formula = None` | Nguồn không cho biết D01 có môn chính hay không. Ghi chú trong `scoring_formulas` bắt bot nói rõ "chưa xác định", không đoán |
| P5 | Tổ hợp **chỉ có năm 2026**. Hỏi tổ hợp năm 2024/2025 → `Missing(not_collected, available_years=[2026])` + ghi chú "tổ hợp đại diện năm đó có trong dòng điểm chuẩn (T1)" | PRD 13.2: nói rõ thiếu gì, có sẵn gì (ví dụ "TE1 năm 2024 xét tổ hợp nào") |
| P6 | Chỉ tiêu và phương thức **chỉ có 2025–2026**. Hỏi năm 2024 → `Missing(not_collected, available_years=[2025, 2026])` | PRD 13.2 ví dụ "Chỉ tiêu IT1 năm 2024" → báo chưa có, đề xuất 2025/2026. Dùng `not_collected` chứ không phải `year_out_of_range` vì 2024 vẫn nằm trong phạm vi dữ liệu, chỉ là chưa thu được bảng này |
| P7 | Trường thông tin chung bị trống (FL3 chưa có ngôn ngữ; EM4, TROY-BA không có trang 2026) → giữ `None` và ghi vào `missing` | Không để Synthesizer tự điền. Bot chỉ được nói "chưa có thông tin" |
| P8 | Tối đa 3 ngành; nhóm ngành → `invalid` gợi ý `list_programs` | Như T1 (PRD 10.2). Đầu ra T3 dài, 26 ngành Elitech thì quá tải ngữ cảnh LLM |
| P9 | Tham số `fields` | Q39 chỉ hỏi thang điểm. Trả cả mô tả và 4 công thức là tốn token và làm LLM dễ lạc đề |
| P10 | `formulas` liệt kê **một lần mỗi công thức**, tổ hợp chỉ ghi `formula_type` | Bốn tổ hợp cùng `mon_chinh_toan` mà lặp lại công thức 4 lần thì đầu ra dài gấp nhiều lần, không thêm thông tin |
| P11 | Công thức XTTN/ĐGTD gắn theo **phương thức** của ngành; công thức THPT gắn theo **tổ hợp** | `program_combinations` không có dòng XTTN. Công thức XTTN áp dụng chung cho mọi ngành xét XTTN |
| P12 | Mã phương thức trả theo bảng `program_methods` (`XTTN`, không tách 1.1/1.2/1.3) | Đề án công bố phương thức ở mức XTTN; chi tiết diện thuộc về RAG (quy định XTTN 2026) |

### Thay đổi kèm theo trong `build_db.py`

Thêm cột `programs.program_page_url` (lấy từ `source_url` của `program_overview_2026.csv`).

**Vì sao:** thông tin chung lấy từ trang ngành, nhưng hiện bảng `programs` chỉ giữ nguồn của danh mục mã ngành (`ma_nganh_truong.md`). Không có cột này thì T3 không trích dẫn đúng trang cho "học bằng tiếng gì, mấy năm". Không phải sửa CSV nguồn; chỉ là nạp thêm một cột đã có sẵn.

---

## 6. Đáp án mong đợi và test — **anh duyệt từng dòng**

Giá trị lấy từ dữ liệu hiện có (đã kiểm trong Postgres 2026-10-08). Test sẽ so đúng các giá trị này, phần quét toàn bộ thì so thẳng với CSV.

| # | Đầu vào | Đáp án mong đợi | Câu 120 |
|---|---|---|---|
| T3-01 | `programs=["IT1"]` | `ok`. Như ví dụ mục 3: SOICT, chuẩn, tiếng Việt, 4–5,5 năm, chỉ tiêu 2026 = **300**, phương thức DGTD/THPT/XTTN, tổ hợp A00, A01 (môn chính Toán), K01, K00; 4 công thức | — |
| T3-02 | `programs=["Toán Tin"], fields=["combinations"]` | MI1. THPT: A00, A01 môn chính **Toán** → `mon_chinh_toan` ("Toán được tính 2 lần"); K01 → công thức K01 riêng. Nguồn công thức = **bài điểm chuẩn 2026**; không có URL ngoài ts.hust.edu.vn | Q10, Q11 |
| T3-03 | `programs=["FL2"], fields=["methods","combinations"]` | Phương thức THPT **thang 30**, DGTD thang 100, XTTN thang 100. THPT: D01 → `khong_mon_chinh`, K01. DGTD: K00 | Q39 |
| T3-04 | `programs=["TROY-IT"], fields=["combinations"]` | D01: `formula_type = chua_ro`, `main_subject_known = false`, `formula = None`. A00, A01 môn chính Toán; K01 | — |
| T3-05 | `programs=["IT2"], fields=["quota"]` | Chỉ tiêu 2026 = **200** (`tong_nganh`) | Q36 |
| T3-06 | `programs=["IT1"], years=[2024,2025,2026], fields=["quota"]` | 2025 = 300, 2026 = 300; `Missing(not_collected, 2024, available=[2025,2026])`; `partial` | — |
| T3-07 | `programs=["CH-E20"], years=[2025]` | `not_found`, `Missing(program_not_open, available=[2026])` (ngành mở 2026) | Q73 |
| T3-08 | `programs=["EM4"]` (không nói năm) | `not_found`, `Missing(program_not_open, available=[2024,2025])` | — |
| T3-09 | `programs=["EM4"], years=[2025]` | `partial`. Chỉ tiêu 2025 = **80**; phương thức DGTD/THPT/XTTN; `overview = None` (không có trang 2026); tổ hợp → `Missing(not_collected, available=[2026])` | — |
| T3-10 | `programs=["IT1"], years=[2025], fields=["combinations"]` | `not_found`, `Missing(not_collected, available=[2026])` + ghi chú "tổ hợp đại diện năm 2025 có trong dòng điểm chuẩn" | PRD 13.2 |
| T3-11 | `programs=["FL3"], fields=["overview"]` | `overview.language = None` + `Missing(not_collected, "ngôn ngữ đào tạo FL3")`; các trường khác có | — |
| T3-12 | `programs=["Khoa học máy tính"]` | `ambiguous`, ứng viên IT1 / TROY-IT, không có `data` | — |
| T3-13 | `programs=["Elitech"]` | `invalid`, gợi ý `list_programs` | Q62 |
| T3-14 | `programs=["IT1","IT2","MI1","EM1"]` | `invalid`, câu PRD 10.2 | — |
| T3-15 | `programs=["IT1"], fields=["quota"]` | Chỉ có `quotas`; `overview`, `methods`, `combinations`, `formulas` rỗng | — |
| T3-16 | `programs=["Việt Nhật","Global ICT"], fields=["overview"]` | IT-E6 và IT-E7, mỗi ngành ngôn ngữ/bằng/thời gian đúng như `program_overview_2026.csv` | Q63, Q65 |
| T3-17 | **Quét toàn bộ** 68 ngành năm 2026 | Mọi trường thông tin chung khớp `program_overview_2026.csv`; chỉ tiêu khớp `quotas_2026.csv`; phương thức khớp `program_methods_2026.csv`; tổ hợp khớp `subject_combinations_2026.csv` + `linking/program_combinations_extra.csv` | — |
| T3-18 | Nguồn của mọi ca trên | Không có `source_url` nào ngoài miền `hust.edu.vn` (không lọt tuyensinh247) | — |

---

## 7. File đụng tới

```
scripts/build_db.py                      + cột programs.program_page_url
backend/app/schemas/program_info.py      mới: model mục 2–3
backend/app/tools/program_info.py        mới: tool
backend/app/tools/admission.py           tách _resolve_all, _invalid, _years ra file dùng chung (tools/common.py)
backend/tests/test_program_info.py       mới: 18 ca mục 6
```

**Vì sao tách phần dùng chung:** T3 cần đúng các hàm phân giải cụm từ, báo lỗi và xử lý năm của T1. Copy sang thì sau này sửa một chỗ quên chỗ kia; T4–T6 cũng sẽ dùng các hàm này.

## 8. Thứ tự và ước lượng

| Bước | Việc | Ước lượng | Xong khi |
|---|---|---|---|
| 1 | `build_db.py` thêm `program_page_url`; tách `tools/common.py` | ~30 phút | 186 test cũ vẫn xanh |
| 2 | Schema + tool | ~1,5 giờ | Chạy được T3-01 |
| 3 | 18 test mục 6 | ~1 giờ | Toàn bộ xanh |
| 4 | Ghi "Đã thực hiện" + cập nhật `cautrucduan.md`, `memory.md` | ~15 phút | |

**Tổng: khoảng 3 giờ 15 phút.**

---

## 9. Cần anh duyệt

1. **Bảng đáp án mong đợi mục 6** (18 ca). Dòng nào anh thấy sai thì sửa thẳng vào bảng hoặc báo tôi.
duyệt 
2. **Phạm vi mục 1**: T3 không trả điểm chuẩn / học phí / liên hệ, mỗi loại để tool riêng lo.
3. **Tham số `fields`** (P9): có giữ không, hay luôn trả đủ mọi phần?
giữ tham số fields
4. **Thêm cột `program_page_url`** vào bảng `programs` (mục 5, "Thay đổi kèm theo").
thêm vào oke

---

# Đã thực hiện (2026-10-08)

Anh duyệt: bảng 18 ca mục 6, giữ tham số `fields`, thêm cột `program_page_url`. Điểm 2 (phạm vi) anh không ghi gì; hiểu là đồng ý theo câu "đã đưa thông tin duyệt".

## Kết quả

| Bước | Kết quả |
|---|---|
| 1 | `build_db.py` thêm `programs.program_page_url`: 68/70 ngành có (EM4, TROY-BA không có trang 2026). Phần dùng chung tách sang `app/tools/common.py`: `resolve_mentions`, `invalid_result`, `ambiguous_result`, `pick_years`, `row_source`, `to_float`. `admission.py` dùng lại các hàm này; 186 test cũ vẫn xanh |
| 2 | `app/schemas/program_info.py`, `app/tools/program_info.py`. Đầu ra với IT1 khớp ví dụ mục 3 |
| 3 | `backend/tests/test_program_info.py`: **18/18 ca đã duyệt xanh**, gồm quét đủ 68 ngành năm 2026 (thông tin chung, chỉ tiêu, phương thức, tổ hợp khớp CSV) |
| Tổng | `pytest backend`: **204 passed**; `pyflakes` sạch |

## Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| `MethodItem` | Thêm `source` (plan mục 3 chưa có) | Phương thức cũng cần trích nguồn (thông tin tuyển sinh năm đó), giống chỉ tiêu |
| `FormulaItem` | Thêm `year` | Công thức gắn với năm (hiện chỉ có 2026); không có thì không biết công thức áp dụng năm nào |
| `ProgramInfoData.notes` | Ghi chú cố định "tổ hợp đại diện có trong dòng điểm chuẩn" | P5, giống `notes` của T2 |
| `ToolContext.program_methods` | Bảng (ngành, năm) → phương thức, nạp một lần | Gắn công thức ĐGTD/XTTN theo phương thức của ngành (P11) cả khi người dùng không lấy phần `methods` |
| Kiểm năm | Dựa trên độ phủ `program_years` (2024–2026) | T3 trải nhiều bảng; bảng nào thiếu năm thì báo `not_collected` cho riêng phần đó (P5, P6) |
| T3-18 | Tự kiểm nguồn của **cả 68+ ngành**, mọi phần, năm 2025 và 2026; không dựa vào các test khác | Bản đầu gom nguồn từ các ca chạy trước, nên chạy riêng thì đỏ oan; bản mới phủ rộng hơn bảng duyệt |
| `scan.py` | Bỏ một import thừa (pyflakes báo) | Dọn khi chạy kiểm lỗi toàn backend |
