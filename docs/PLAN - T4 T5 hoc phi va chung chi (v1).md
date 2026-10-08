# PLAN — T4 `tuition_fees` (học phí, lệ phí) + T5 `certificate_lookup` (chứng chỉ ngoại ngữ) (v1)

**Ngày:** 2026-10-08 · **Trạng thái:** anh duyệt 2026-10-09 (kèm bổ sung học phí tín chỉ 2025–2026, 2026–2027 — mục D), **đã thực hiện 2026-10-09** — xem mục E · Bước 5 của `PLAN - Tools (v1).md` mục 9 · Dùng lại khung: `ToolResult`, `ToolContext`, `tools/common.py`, Entity Resolution

Mỗi quyết định có dòng **Vì sao**. Các con số trong file lấy từ Postgres ngày 2026-10-08.

**Tóm tắt:** T4 trả "học phí ngành X bao nhiêu, bao nhiêu một tín chỉ, lệ phí thi/xét tuyển bao nhiêu". T5 trả "chứng chỉ X mức Y được quy đổi/cộng bao nhiêu khi xét tuyển" và "đạt bậc mấy, có đủ chuẩn đầu ra ngoại ngữ của ngành không". Cả hai chỉ tra bảng; quy định dạng văn bản (lộ trình tăng học phí, học kỳ hè ×1,5, cách nộp chứng chỉ) vẫn do RAG (T7) trả lời.

---

# A. T4 `tuition_fees`

## A1. Dữ liệu có gì — và thiếu gì

| Loại | Bảng | Năm | Đơn vị | Ghi chú |
|---|---|---|---|---|
| Học phí **theo ngành** | `tuition_program` (68 dòng) | **2026** | 63 ngành `triệu đồng/năm`; 5 ngành `triệu đồng/học kỳ` (ET-LUH, ME-LUH, ME-NUT, ME-GU, TROY-IT) | TROY-IT có `terms_per_year = 3`; 2 ngành ghi "khoảng" (`is_approximate`, vd IT-E10 "~ 68") |
| Học phí **theo nhóm, năm học 2024–2025** | `tuition_rules` loại `nam` (11 dòng) + bảng cầu thành viên | 2024 (năm học 2024–2025) | `triệu đồng/năm học` hoặc `/học kỳ` | Vd nhóm chuẩn 24–30 triệu/năm học |
| Học phí **theo tín chỉ** | `tuition_rules` loại `tin_chi` (30 + 29 + 31 dòng) + bảng cầu | **3 năm học riêng**: 2024–2025, 2025–2026 (QĐ 10232), 2026–2027 (QĐ 12006) — bổ sung 2026-10-09, mục D | `nghìn đồng/tín chỉ` (riêng TROY `nghìn đồng/học kỳ`) | Có dòng theo loại học phần (LLCT-GDTC-GDQP… / học phần khác), theo khoá (TROY), và 5 mức học phần ngoại ngữ áp dụng **mọi ngành** (trừ TROY, A5-T10) |
| **Lệ phí tuyển sinh** (phí thủ tục khi đăng ký thi / xét tuyển, **không phải học phí**) | `admission_fees` (6 dòng) | **chỉ 2024** | đồng, đồng/nguyện vọng | Lệ phí thi ĐGTD 500.000đ/đợt (anh đã chốt giữ, dù đề án 2024 ghi 450.000đ) |

**Không có:** học phí theo ngành năm 2024–2025, lệ phí tuyển sinh 2025–2026, học phí tín chỉ năm học 2027–2028 trở đi.

## A2. Đầu vào

```python
class TuitionInput(BaseModel):
    programs: list[str] = []          # 0–3 ngành (cụm người dùng gõ hoặc mã)
    program_group: str | None = None  # cả nhóm: "Elitech", "chương trình chuẩn", "PFIEV", "liên kết"
    years: list[int] = []             # năm tuyển sinh, 0–3; rỗng = năm mới nhất của loại số liệu đó
    kinds: list[Literal["program", "year_rule", "credit", "fee"]] = []   # rỗng = ["program"]
```

| `kinds` | Lấy gì | Cần ngành/nhóm? |
|---|---|---|
| `program` | Học phí theo ngành (2026) | Có (ngành hoặc nhóm) |
| `year_rule` | Học phí theo nhóm, năm học 2024–2025 | Có |
| `credit` | Học phí tín chỉ **của năm học hỏi** (năm 2026 = năm học 2026–2027) cho ngành/nhóm + 5 mức học phần ngoại ngữ | Không bắt buộc; bỏ trống = cả bảng của năm học đó |
| `fee` | **Lệ phí tuyển sinh**: phí đăng ký xét tuyển, thi ĐGTD, xác minh chứng chỉ — phí thủ tục, **không phải học phí** | Không |

## A3. Đầu ra

```python
class ProgramTuition(BaseModel):
    program_code; program_name; program_group_code; year: int
    amount_min: float; amount_max: float; unit: str          # "triệu đồng/năm" | "triệu đồng/học kỳ"
    per: Literal["năm", "học kỳ"]; terms_per_year: int | None # TROY-IT: 3
    is_approximate: bool; amount_text: str                   # nguyên văn trang ngành, vd "~ 68 triệu đồng/năm"
    amount_vnd_min: int; amount_vnd_max: int; unit_vnd: str  # A5-T11: đổi cấp tiền ra đồng, vd 28.000.000 "đồng/năm"
    source: Source

class TuitionRule(BaseModel):                                 # dùng cho year_rule và credit
    rule_id; rule_type: Literal["nam", "tin_chi"]; academic_year: str     # "2024-2025"
    group_text: str; course_type: str | None; cohort: str | None
    applies_to_all: bool                                      # học phần ngoại ngữ: mọi ngành
    amount_min: float; amount_max: float; unit: str
    amount_vnd_min: int; amount_vnd_max: int; unit_vnd: str  # vd 26000 "nghìn đồng/học kỳ" -> 26.000.000 "đồng/học kỳ"
    program_codes: list[str]                                  # các ngành (trong phạm vi hỏi) áp dụng mức này
    note: str | None; source: Source

class AdmissionFee(BaseModel): fee_type; year; amount: int; unit; note; source   # "lệ phí tuyển sinh" (A5-T12)

class UnitStat(BaseModel):     # chỉ khi hỏi theo nhóm; MỖI ĐƠN VỊ MỘT DÒNG (A5-T2)
    unit: str; count: int; min: float; max: float; program_codes: list[str]

class TuitionData(BaseModel):
    programs: list[ProgramTuition]; year_rules: list[TuitionRule]; credit_rules: list[TuitionRule]
    fees: list[AdmissionFee]; stats: list[UnitStat]; notes: list[str]
```

**Ví dụ thật** — `programs=["TROY-IT", "IT1"]`:

```json
{"status": "ok", "data": {"programs": [
   {"program_code": "IT1", "year": 2026, "amount_min": 28, "amount_max": 40, "unit": "triệu đồng/năm", "per": "năm",
    "amount_text": "28 - 40 triệu đồng/năm", "is_approximate": false},
   {"program_code": "TROY-IT", "year": 2026, "amount_min": 33, "amount_max": 33, "unit": "triệu đồng/học kỳ",
    "per": "học kỳ", "terms_per_year": 3, "amount_text": "33 triệu đồng/học kỳ"}]}}
```

> Câu trả lời mong muốn: *"Năm 2026, IT1 khoảng **28–40 triệu đồng/năm**; TROY-IT **33 triệu đồng/học kỳ**, chương trình có **3 học kỳ/năm**."* — không tự nhân ra "99 triệu/năm" (A5-T1).

## A4. Quá trình xử lý

1. Kiểm: quá 3 ngành / 3 năm → `invalid`. `kinds` có `program`/`year_rule` mà không có ngành hay nhóm → `invalid` ("cần nêu ngành hoặc nhóm ngành").
2. Ngành: `resolve_mentions` như T1. Mơ hồ → `ambiguous`, không truy vấn. Nhóm: `resolve(..., "program")`; ra `group` (Elitech, chương trình chuẩn, liên kết) thì lấy các ngành thuộc nhóm; ra danh sách cần hỏi lại (PFIEV → EE-EP, IT-EP, TE-EP) thì **lấy hết danh sách** (A5-T9).
3. Năm, **theo từng loại**: `program` có 2026; `year_rule` có 2024 (năm học 2024–2025); `fee` có 2024; `credit` có 2024, 2025, 2026 (năm học bắt đầu từ năm đó). Rỗng → năm mới nhất của loại đó. Năm không có → `Missing(not_collected, available_years)`.
4. Truy vấn từng loại; `credit` lấy luật của các ngành trong phạm vi **cộng** các dòng `applies_to_all`, **trừ** khi mọi luật của các ngành hỏi đều là "toàn bộ chương trình" (TROY: A5-T10).
5. Hỏi theo nhóm và `kinds` có `program` → tính `stats` **theo từng đơn vị**.
6. Ghi chú cố định: có `credit` → *"Học phí tín chỉ năm học <năm>–<năm+1>, tính cho 2 học kỳ chính; học kỳ hè tính 1,5 lần."*; có `year_rule` → *"Học phí theo nhóm của năm học 2024–2025."*; có `fee` → *"Lệ phí tuyển sinh theo Đề án tuyển sinh 2024 (phí thủ tục, không phải học phí)."*

## A5. Quyết định T4

| # | Quyết định | Vì sao |
|---|---|---|
| A5-T1 | **Không quy đổi** `/học kỳ` sang `/năm` (không nhân số học kỳ) | Chỉ TROY-IT có số học kỳ/năm trong dữ liệu (3). Bốn ngành khác tính theo học kỳ mà không ghi số kỳ/năm; tự giả định 2 kỳ có thể sai. PRD 3.1.A: gộp nhầm đơn vị sai tới 3 lần. Tool chỉ trả số kèm đơn vị và `terms_per_year` khi có |
| A5-T2 | Hỏi theo nhóm: `stats` **mỗi đơn vị một dòng**, không gộp | Nhóm Elitech có 22 ngành tính theo năm (35–68 triệu) và 4 ngành tính theo học kỳ (24–30 triệu). Gộp thành "24–68 triệu" là trộn hai đơn vị |
| A5-T3 | **Không tính chênh lệch** học phí giữa các ngành | Học phí là khoảng (28–40 vs 40–50) và có thể khác đơn vị; trừ hai khoảng ra một con số dễ gây hiểu sai. Trả số đặt cạnh nhau, đúng nguyên văn |
| A5-T4 | Học phí tín chỉ trả **theo đúng năm học**; không nói năm → năm học mới nhất (2026–2027); năm không có bảng → `not_collected` | **Thay quyết định cũ** "bảng 2024–2025 dùng chung mọi năm": ngày 2026-10-09 anh bổ sung QĐ học phí 2025–2026 và 2026–2027, mức tăng mỗi năm (IT1: 550 → 630 → 700 nghìn/tín chỉ) nên dùng chung là sai số |
| A5-T5 | Học phí theo ngành chỉ có 2026; hỏi 2025 → `not_collected`, gợi ý `year_rule` (2024–2025) và `program` (2026) | PRD 13.2: không lấy tạm số năm khác, nói rõ có sẵn gì |
| A5-T6 | Lệ phí: không nói năm → trả số **2024** kèm ghi chú nguồn; hỏi năm khác → `not_collected, available=[2024]` | Đúng quy ước "năm mới nhất có dữ liệu" (D6). Hỏi rõ năm 2026 thì không được trả số 2024 như số 2026 |
| A5-T7 | Ngành mơ hồ → hỏi lại như T1 | Mỗi con số học phí gắn một ngành; chọn sai ngành là sai số tiền |
| A5-T8 | Trả nguyên văn `amount_text` cạnh số | "~ 68 triệu" là ước lượng; giữ chữ "~" để bot không trình bày như số chính xác |
| A5-T9 | `program_group` mà tra ra danh sách cần hỏi lại (PFIEV, "Liên kết quốc tế") → lấy **hết** danh sách | Giống T2-3 anh đã duyệt: hỏi theo nhóm là muốn xem cả nhóm, và mỗi dòng ghi rõ mã ngành nên không gán nhầm số. Chỉ ô `programs` (từng ngành cụ thể) mới hỏi lại |
| A5-T10 | TROY (thu trọn gói "toàn bộ chương trình") **không** kèm 5 mức học phần ngoại ngữ; ghi rõ khoá và phí ghi danh 1,7 triệu đóng một lần | Anh duyệt 2026-10-09. Dữ liệu đánh dấu "áp dụng mọi ngành" chỉ vì văn bản liệt kê chung; với học phí trọn gói, cộng thêm phí ngoại ngữ là sai |
| A5-T11 | Trả kèm số **đổi ra đồng** (`amount_vnd_*`, `unit_vnd`) | Anh duyệt 2026-10-09. "26000 nghìn đồng/học kỳ" dễ bị đọc nhầm thành 26 nghìn. Chỉ đổi **cấp tiền** (nghìn/triệu → đồng), **không** đổi kỳ hạn (A5-T1) |
| A5-T12 | Loại `fee` gọi là **"lệ phí tuyển sinh"**, ghi chú "phí thủ tục, không phải học phí" | Anh duyệt 2026-10-09: tránh nhầm lệ phí (đóng khi đăng ký) với học phí (đóng khi đã là sinh viên) |

## A6. Đáp án mong đợi T4 — **anh duyệt từng dòng**

| # | Đầu vào | Đáp án mong đợi | Câu 120 |
|---|---|---|---|
| T4-01 | `programs=["IT1"]` | `ok`; 2026: **28–40 triệu đồng/năm** | — |
| T4-02 | `programs=["TROY-IT"]` | **33 triệu đồng/học kỳ**, `terms_per_year = 3`; không có số "/năm" tự tính | Q49 |
| T4-03 | `programs=["IT-E6","IT-EP","IT1"]` | IT-E6 40–50, IT-EP 40–50, IT1 28–40, cùng đơn vị triệu đồng/năm; không có chênh lệch | Q58 |
| T4-04 | `programs=["IT-E10"]` | 68 triệu đồng/năm, `is_approximate = true`, `amount_text = "~ 68 triệu đồng/năm"` | — |
| T4-05 | `program_group="Elitech"` | `stats` 2 dòng: `/năm` 22 ngành **35–68**; `/học kỳ` 4 ngành **24–30** (ET-LUH, ME-LUH, ME-NUT, ME-GU) | Q47 |
| T4-05b | `program_group="PFIEV"` | Lấy cả 3 ngành EE-EP, IT-EP, TE-EP (không hỏi lại); `/năm` 3 ngành | — |
| T4-06 | `program_group="chương trình chuẩn", kinds=["credit"]` | Năm học **2026–2027**: 3 mức chuẩn **700 / 680 / 620 nghìn đồng/tín chỉ**, mỗi mức kèm danh sách ngành; + 5 mức học phần ngoại ngữ (725–1085, `applies_to_all`) | Q46 |
| T4-07 | `programs=["IT1"], kinds=["credit"]` | Năm học 2026–2027: **700 nghìn đồng/tín chỉ** (= 700.000 đồng) + 5 mức ngoại ngữ | — |
| T4-07b | `programs=["IT1"], years=[2025], kinds=["credit"]` | Năm học 2025–2026: **630 nghìn đồng/tín chỉ** | — |
| T4-07c | `programs=["IT1"], years=[2024], kinds=["credit"]` | Năm học 2024–2025: **550 nghìn đồng/tín chỉ** | — |
| T4-07d | `programs=["IT1"], years=[2027], kinds=["credit"]` | `not_found`, `Missing(not_collected, available=[2024, 2025, 2026])` | — |
| T4-08 | `programs=["TROY-IT"], kinds=["credit"]` | TROY **không thu theo tín chỉ**. Năm học 2026–2027, 4 mức trọn gói theo khoá: **K71 34 triệu**, K70 30 triệu, K69 28,6 triệu, ≤K68 26 triệu **/học kỳ** (`amount_vnd` 34.000.000 …), 3 học kỳ/năm; phí ghi danh 1,7 triệu đóng một lần. **Không** kèm 5 mức ngoại ngữ (A5-T10) | Q49 |
| T4-09 | `programs=["IT1"], years=[2024], kinds=["year_rule"]` | Nhóm chuẩn năm học 2024–2025: **24–30 triệu đồng/năm học** | — |
| T4-10 | `programs=["IT1"], years=[2025]` | `not_found`; `Missing(not_collected, "học phí theo ngành năm 2025", available=[2026])` + ghi chú có học phí theo nhóm năm học 2024–2025 | PRD 13.2 |
| T4-11 | `programs=["EM4"]` | `not_found`, `program_not_open`, available [2024, 2025] | — |
| T4-12 | `programs=["EM4"], years=[2024], kinds=["year_rule"]` | Nhóm chuẩn 2024–2025: 24–30 triệu đồng/năm học | — |
| T4-13 | `kinds=["fee"]` | 6 khoản **lệ phí tuyển sinh** năm 2024, trong đó **Lệ phí đăng ký dự thi ĐGTD 500.000 đồng (mỗi đợt)**; ghi chú "theo Đề án 2024, phí thủ tục, không phải học phí" | Q8 |
| T4-14 | `kinds=["fee"], years=[2026]` | `not_found`, `available=[2024]`; **không** trả số 2024 | — |
| T4-15 | `programs=["Khoa học máy tính"]` | `ambiguous` IT1 / TROY-IT | — |
| T4-16 | `programs=["IT1","IT2","MI1","EM1"]` | `invalid`, câu PRD 10.2 | — |
| T4-17 | `kinds=["program"]` (không ngành/nhóm) | `invalid`, "cần nêu ngành hoặc nhóm ngành" | — |
| T4-18 | **Quét toàn bộ** | 68 ngành: số và đơn vị khớp `tuition_2026.csv`; mọi luật tín chỉ của mọi ngành, **cả 3 năm học**, khớp `linking/tuition_rule_members.csv` | — |
| T4-19 | Mọi ca trên | Mọi số tiền đều có `unit` và `amount_vnd`/`unit_vnd` đúng phép đổi (nghìn ×1.000, triệu ×1.000.000); mọi luật đều có `academic_year` | PRD 3.1.A |

---

# B. T5 `certificate_lookup`

## B1. Dữ liệu có gì — và thiếu gì

| Mục đích | Bảng | Năm | Nội dung |
|---|---|---|---|
| **Xét tuyển** | `cert_bonus` | 2026: 23 chứng chỉ (bảng chung `ca_hai`); 2025: chỉ IELTS; 2024: IELTS + VSTEP, tách 2 bảng `quy_doi`, `diem_thuong` | Mỗi mức: **điểm thưởng** (cộng vào điểm xét ĐGTD) và **điểm quy đổi môn tiếng Anh** (thang 10) |
| **Chuẩn đầu ra** — bậc | `cert_output` | quy định K71 (10828/QĐ-ĐHBK, 07/9/2026) | 18 chứng chỉ × 9 bậc (Bậc 1.1 … Bậc 5) |
| **Chuẩn đầu ra** — yêu cầu theo ngành | `language_requirements` + bảng cầu | **chỉ khoá K71 trở về sau** | 14 yêu cầu; vd chuẩn "từ Bậc 3", Elitech "từ Bậc 4", PFIEV nhiều điều kiện |
| Khung CEFR | `cert_cefr` | 2025 | Chứng chỉ → CEFR (B1/B2/C1…) + bậc KNLNN |

**Không có:** bảng chuẩn đầu ra khoá **K70 trở về trước** (văn bản 10728/QĐ-ĐHBK chỉ có ở RAG), xét tuyển 2025 cho chứng chỉ khác IELTS.

## B2. Đầu vào

```python
class CertificateInput(BaseModel):
    certificate: str                    # "IELTS", "TOEIC", "TOEFL iBT", "JLPT"...
    value: str | None = None            # "6.5", "300", "N3", "B2"; bỏ trống = cả bảng
    purpose: Literal["xet_tuyen", "chuan_dau_ra", "khung_cefr"] | None = None   # bỏ trống -> hỏi lại (B5-T1)
    year: int | None = None             # xét tuyển: năm tuyển sinh; rỗng = 2026
    programs: list[str] = []            # chuẩn đầu ra: 0–3 ngành
    cohort: str | None = None           # chuẩn đầu ra: "K71", "K70", "khoá 2026"...
```

## B3. Đầu ra

```python
class CertConversion(BaseModel):   # xét tuyển
    cert_code; cert_name; cert_value: str; year: int
    table: Literal["ca_hai", "quy_doi", "diem_thuong"]
    bonus_point: int | None          # điểm thưởng
    converted_score_10: float | None # điểm quy đổi môn tiếng Anh (thang 10)
    note; source

class ExitLevel(BaseModel):        # chuẩn đầu ra — bậc của chứng chỉ
    cert_code; cert_value; level: str; level_group: str; note; source

class ExitRequirement(BaseModel):  # chuẩn đầu ra — yêu cầu theo ngành
    req_id; cohort; group_text; main_language; degree_level; requirement: str
    min_level_group: str | None; note; program_codes: list[str]; source
    meets: bool | None               # B5-T5: chỉ tính khi yêu cầu đơn giản "từ Bậc N trở lên"

class CefrLevel(BaseModel): cert_code; cert_value; cefr_level; knlnn_level; source

class CertificateData(BaseModel):
    cert_codes: list[str]; matched: bool | None     # None khi không nêu value
    conversions: list[CertConversion]; exit_levels: list[ExitLevel]
    requirements: list[ExitRequirement]; cefr: list[CefrLevel]; notes: list[str]
```

**Ví dụ thật** — `certificate="IELTS", value="5.0", purpose="chuan_dau_ra", programs=["IT-E10"], cohort="K71"`:

```json
{"status": "ok", "data": {"cert_codes": ["IELTS_ACADEMIC"], "matched": true,
  "exit_levels": [{"cert_value": "5.0", "level": "Bậc 3.2", "level_group": "Bậc 3"}],
  "requirements": [{"req_id": "nn2026-elitech-htqt", "cohort": "K71+",
     "requirement": "Có chứng chỉ tiếng Anh quy đổi tương đương từ Bậc 4 trở lên",
     "min_level_group": "Bậc 4", "program_codes": ["IT-E10"], "meets": false}]}}
```

> Câu trả lời mong muốn: *"IELTS 5.0 tương đương **Bậc 3** (3.2). Chuẩn đầu ra ngoại ngữ của IT-E10 (khoá K71 trở về sau) là **từ Bậc 4** → **chưa đạt**; cần khoảng IELTS 5.5–6.5 (Bậc 4)."*

## B4. Quá trình xử lý

1. `purpose` trống → `ambiguous`, ứng viên "xét tuyển" / "chuẩn đầu ra".
2. Chứng chỉ: `resolve(..., "certificate")`. Mơ hồ (TOEFL → iBT/ITP; Cambridge) → `ambiguous`. TOEIC → nhóm 4 kỹ năng, lấy cả 4.
3. **Xét tuyển**: năm mặc định 2026; chứng chỉ không có ở năm đó → `Missing(not_collected, available_years)`.
4. **Chuẩn đầu ra**: `cohort` trống → `ambiguous` (K71 trở về sau / K70 trở về trước). K70 trở về trước → `Missing(not_collected)` + ghi chú "xem Quy định 10728/QĐ-ĐHBK (K70)". K71+ → tra `cert_output`, và nếu có ngành thì tra yêu cầu của ngành.
5. **Khớp `value`**:
   - là số → dòng có `value_min ≤ v ≤ value_max` (không có `value_max` = "từ … trở lên");
   - là chữ (N3, B2) → dòng có `cert_value` chứa chữ đó;
   - không dòng nào khớp → `matched = false`, trả **cả bảng** để bot nói được mức thấp nhất/cao nhất.
6. `meets` (B5-T5).

## B5. Quyết định T5

| # | Quyết định | Vì sao |
|---|---|---|
| B5-T1 | `purpose` **không có mặc định**; trống → hỏi lại | PRD 15.1: hai bảng chứng chỉ **không được dùng lẫn**. IELTS 6.5 xét tuyển cho điểm thưởng 4 / quy đổi 9,5; chuẩn đầu ra cho Bậc 4 — hai câu trả lời khác hẳn |
| B5-T2 | Chuẩn đầu ra: `cohort` trống → hỏi lại; K70 trở về trước → `not_collected`, trỏ sang văn bản K70 (RAG) | PRD 3.1.C: "hỏi chuẩn đầu ra mà chưa rõ khoá thì phải hỏi lại, không chọn bừa một bản". Bảng số chỉ có K71 |
| B5-T3 | TOEIC trả **từng kỹ năng**; ghi chú "điểm xét tuyển là trung bình cộng 4 kỹ năng" | Dữ liệu tách Nghe/Đọc/Nói/Viết với thang khác nhau (Nói/Viết tối đa 200). Một con số "TOEIC 600" không tra được; tool không tự chia |
| B5-T4 | Năm 2024 trả **hai bảng riêng** (`quy_doi`, `diem_thuong`) | Năm 2024 hai bảng có ranh giới mức khác nhau (ghi chú gốc: "Ranh giới mức KHÁC bảng quy đổi") |
| B5-T5 | `meets` **chỉ tính** khi: yêu cầu có dạng đơn giản "từ Bậc N trở lên" (`min_level_group` có giá trị), cùng ngôn ngữ với chứng chỉ, và không phải yêu cầu đầu khoá. Còn lại `meets = None` + nguyên văn yêu cầu | D5: phép so sánh do tool làm, không để LLM ước lượng. Nhưng PFIEV ("DELF B1 **và** TOEIC…"), nhóm ngôn ngữ (Ngoại ngữ 1 + Ngoại ngữ 2), tài năng (nhiều điều kiện) không so một bậc được; tự kết luận "đạt" là sai |
| B5-T6 | Ô gộp (IELTS 3.5 thuộc cả Bậc 2.2 và 2.3) → trả **cả hai dòng** | Đúng nguyên văn bảng (ghi chú "ô gộp"); `level_group` vẫn chung là Bậc 2 |
| B5-T7 | Yêu cầu của TROY-IT là **đầu khoá**, không phải chuẩn đầu ra → `meets = None` + ghi chú nguyên văn | Ghi chú trong dữ liệu: "Đây là yêu cầu ĐẦU KHÓA, không phải chuẩn đầu ra" |
| B5-T8 | Không khớp mức nào → `matched = false` + cả bảng | Bot nói được "IELTS 4.5 chưa đạt mức thấp nhất (5.0) để quy đổi", thay vì "không có dữ liệu" |

## B6. Đáp án mong đợi T5 — **anh duyệt từng dòng**

| # | Đầu vào | Đáp án mong đợi | Câu 120 |
|---|---|---|---|
| T5-01 | IELTS, `value="6.5"`, xét tuyển | 2026: **điểm thưởng 4, quy đổi 9,5** | Q5 |
| T5-02 | IELTS, xét tuyển (không value) | 2026, 5 mức: 5.0 → (1; 8,0) · 5.5 → (2; 8,5) · 6.0 → (3; 9,0) · 6.5 → (4; 9,5) · 7.0–9.0 → (5; 10) | Q4 |
| T5-03 | IELTS, `value="7.5"`, xét tuyển | Khớp mức **7.0–9.0**: (5; 10) | — |
| T5-04 | IELTS, `value="6.5"`, xét tuyển, `year=2024` | Hai bảng: `quy_doi` "≥ 6.5" → **10**; `diem_thuong` "6.5" → **4** | — |
| T5-05 | IELTS, `value="4.5"`, xét tuyển | `matched = false`, trả cả bảng 2026 (thấp nhất 5.0) | — |
| T5-06 | IELTS, `value="6.5"`, chuẩn đầu ra, `cohort="K71"` | **Bậc 4** | Q84 |
| T5-07 | IELTS 6.5, chuẩn đầu ra, IT1, K71 | Yêu cầu nn2026-chuan "từ **Bậc 3**" → `meets = true` | Q84 |
| T5-08 | IELTS 5.0, chuẩn đầu ra, IT-E10, K71 | Bậc 3.2 (nhóm Bậc 3); yêu cầu Elitech "từ **Bậc 4**" → `meets = false` (ví dụ B3) | — |
| T5-09 | IELTS 3.5, chuẩn đầu ra, K71 | 2 dòng: Bậc 2.2 và Bậc 2.3 (ô gộp), nhóm **Bậc 2** | — |
| T5-10 | IELTS 6.5, chuẩn đầu ra, **không cohort** | `ambiguous`: K71 trở về sau / K70 trở về trước | PRD 3.1.C |
| T5-11 | IELTS 6.5, chuẩn đầu ra, `cohort="K70"` | `not_found`, `Missing(not_collected)` + ghi chú "xem Quy định 10728/QĐ-ĐHBK" | — |
| T5-12 | IELTS 6.5, **không purpose** | `ambiguous`: xét tuyển / chuẩn đầu ra | PRD 15.1 |
| T5-13 | TOEFL, xét tuyển | `ambiguous`: TOEFL iBT / TOEFL ITP | — |
| T5-14 | TOEIC, `value="300"`, xét tuyển | Nghe 275–395 → (1; 8,0); Đọc 275–380 → (1; 8,0); Nói, Viết không khớp (thang khác); ghi chú "trung bình cộng 4 kỹ năng" | — |
| T5-15 | JLPT, `value="N3"`, xét tuyển | 3 dòng N3: (95–120) → (2; 8,5) · (121–149) → (3; 9,0) · (150–180) → (4; 9,5) | — |
| T5-16 | IELTS, chuẩn đầu ra, TROY-IT, K71 | Yêu cầu nn2026-troy-daukhoa (VSTEP B2 / tương đương), `meets = None`, ghi chú "yêu cầu ĐẦU KHÓA" | Q66 |
| T5-17 | IELTS 6.5, chuẩn đầu ra, EE-EP (PFIEV), K71 | 3 yêu cầu (cử nhân, kỹ sư, phụ lục văn bằng Pháp), tất cả `meets = None` | — |
| T5-18 | `certificate="abc"` | `not_found`, `ENTITY_NOT_FOUND` | — |
| T5-19 | **Quét toàn bộ** | Mỗi dòng `cert_bonus` năm 2026 và mỗi dòng `cert_output` tra lại được đúng bằng chính `cert_value` của nó | — |

---

# C. Chung cho cả hai

## C1. File đụng tới

```
backend/app/schemas/tuition.py, schemas/certificate.py     mới
backend/app/tools/tuition.py, tools/certificate.py         mới
backend/app/tools/context.py                               + năm có dữ liệu của tuition_program, admission_fees, cert_bonus
backend/tests/test_tuition.py, test_certificate.py         mới: 23 + 19 ca
```

Không sửa dữ liệu nguồn, không sửa `build_db.py`.

## C2. Thứ tự và ước lượng

| Bước | Việc | Ước lượng |
|---|---|---|
| 1 | T4: schema + tool + 23 test | ~2,5 giờ |
| 2 | T5: schema + tool + 19 test | ~3 giờ |
| 3 | Ghi "Đã thực hiện", cập nhật tài liệu | ~15 phút |

**Tổng: khoảng 6 giờ.**

## C3. Cần anh duyệt

1. **Bảng đáp án T4 (mục A6, 19 ca)** và **T5 (mục B6, 19 ca)**.
duyệt
2. **Không quy đổi học kỳ sang năm** (A5-T1). TROY-IT trả "33 triệu/học kỳ, 3 học kỳ/năm", bot không tự nhân ra 99 triệu/năm.
duyệt
3. **Lệ phí chỉ có 2024** (A5-T6): không nói năm thì trả số 2024 kèm ghi chú; hỏi rõ 2026 thì báo chưa có.
duyệt
4. **`meets` (đạt/chưa đạt chuẩn đầu ra)** chỉ tính cho yêu cầu đơn giản "từ Bậc N" (B5-T5); yêu cầu nhiều điều kiện thì chỉ đưa nguyên văn.
duyệt (trả lời qua câu hỏi 2026-10-09: "chỉ yêu cầu đơn giản")

5. **Chuẩn đầu ra bắt buộc biết khoá** (B5-T2): không nói khoá thì hỏi lại.
duyệt

---

# D. Bổ sung 2026-10-09: học phí tín chỉ 2025–2026 và 2026–2027

Anh đưa thêm hai quyết định học phí, kèm link công bố:

| Năm học | Văn bản | Link |
|---|---|---|
| 2025–2026 | QĐ 10232/QĐ-ĐHBK ngày 12/9/2025 | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2025-2026/QD%20HOC%20PHI%20-%202025-2026-final.pdf |
| 2026–2027 | QĐ 12006/QĐ-ĐHBK ngày 05/10/2026 | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2026-2027/12006_Q%C4%90-%C4%90HBK.pdf |

**Đã làm:** thêm **60 dòng** vào `tuition_credit.csv` (29 dòng 2025–2026, 31 dòng 2026–2027) và **192 dòng** vào `linking/tuition_rule_members.csv`. Thêm 2 nguồn vào `build_source_list.py` → `docs/nguon_du_lieu.md`. `validate_metadata` 0 lỗi, `build_db` 0 khoá mồ côi, `validate_links` 0 lỗi (7 cảnh báo cũ, không thêm cảnh báo mới).

| Chỗ | Làm | Vì sao |
|---|---|---|
| Cách đọc | Lấy chữ từ PDF (có lớp chữ) và **đối chiếu với ảnh trang** để xác định ô gộp | Bảng ELITECH có cột "LLCT, GDTC, GDQP-AN, Tiếng Anh cơ bản" gộp một ô cho nhiều dòng; chỉ đọc chữ thì không biết số nào thuộc cột nào |
| `verification_status` | `pdf_text`; bảng gán ngành `rule_derived` | Bóc từ văn bản có sẵn chữ. Nhãn `manual_verified` chỉ người soát mới gắn được (PRD 26) |
| "Các chương trình tiên tiến còn lại" | Gán cho các ngành ELITECH không có tên riêng trong văn bản: 13 ngành (2025–2026), 14 ngành (2026–2027, thêm CH-E20); đã gồm IT-EP | Văn bản ghi "Công nghệ thông tin Việt-Pháp **và** các chương trình tiên tiến còn lại" |
| "Các chương trình chuẩn khác" | Không có ngành nào rơi vào (mọi ngành chuẩn đều có tên trong văn bản) | Đã kiểm bằng danh sách ngành theo năm |
| Ghi chú | Nối vào cột `programs_listed` (CSV không có cột `note`), như dòng TROY năm 2024–2025 | Giữ phí ghi danh IPE (14 triệu/năm khoá 69–71; 13 triệu khoá ≤68) và điểm mơ hồ dưới đây |

**Điểm cần anh biết (không tự sửa):**

1. **TROY-IT khoá K71 lệch nguồn:** QĐ 12006 ghi **34 triệu/học kỳ**, trang ngành 2026 (`tuition_2026.csv`) ghi **33 triệu/học kỳ**. T4 trả cả hai, mỗi số kèm nguồn: `kinds=["program"]` ra 33 (trang ngành), `kinds=["credit"]` ra 34 (quyết định học phí).
2. **2026–2027, dòng "Việt-Pháp và tiên tiến còn lại" (800):** chú thích chỉ nói học phần LLCT, GDTC, GDQP-AN tính 750, **không nói Tiếng Anh cơ bản, cơ sở** tính 750 hay 800. Dữ liệu ghi dòng "cơ bản" 750 kèm ghi chú nói rõ điểm mơ hồ này.

---

# E. Đã thực hiện (2026-10-09)

## Kết quả

| Việc | Kết quả |
|---|---|
| T4 `tuition_fees` | `app/schemas/tuition.py`, `app/tools/tuition.py`; `backend/tests/test_tuition.py` **23/23** ca đã duyệt xanh (T4-07 tách 3 ca theo năm học), gồm quét đủ 68 ngành và **mọi cặp (ngành, năm học)** có luật tín chỉ |
| T5 `certificate_lookup` | `app/schemas/certificate.py`, `app/tools/certificate.py`; `backend/tests/test_certificate.py` **19/19** ca xanh, gồm quét mọi dòng `cert_bonus` 2026 và mọi dòng `cert_output` |
| `ToolContext` | Nạp thêm `tuition_program`, `tuition_rules`, `admission_fees`; độ phủ năm của học phí theo nhóm (`tuition_nam`) và tín chỉ (`tuition_tin_chi`) |
| Tổng | `pytest backend` **246 passed**; `pyflakes` sạch; `validate_aliases` 0/0, `validate_links` 0 lỗi, `validate_metadata` 0/0; AC2/AC8 vẫn 100% |

## Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| Tra ngành cho học phí tín chỉ / theo nhóm | Tra trên **mọi năm có ngành** (2024–2026), không lọc theo năm tuyển sinh; chỉ `kinds=["program"]` (trang ngành 2026) mới lọc theo năm | Test quét toàn bộ bắt được: học phí tín chỉ áp dụng cho **sinh viên đang học** mọi khoá. EM4 ngừng tuyển từ 2026 nhưng QĐ 12006 (2026–2027) vẫn ghi "Kế toán". Lọc theo năm tuyển thì báo nhầm "ngành không tuyển" và mất số liệu đúng |
| `programs` chứa tên nhóm (vd "Elitech") | Coi như hỏi theo nhóm (lấy cả nhóm) thay vì báo `invalid` như T1 | T4 có chế độ hỏi theo nhóm (A5-T2, A5-T9); LLM có thể đặt tên nhóm vào ô `programs` |
| T5 khớp `value` | Số thuần (6.5, 300, "7,5") → so khoảng `value_min`–`value_max`; còn lại (N3, B2, "275-395", "≥ 8.0") → so chữ đã chuẩn hoá | Bảng có cả mức số lẫn mức chữ; quét toàn bộ xác nhận mọi dòng đều tra lại được bằng chính giá trị của nó |
| T5 `meets` | Chỉ khi yêu cầu khớp đúng mẫu "Có chứng chỉ … từ Bậc N trở lên", không có ";", cùng ngôn ngữ, không phải yêu cầu đầu khoá | B5-T5 anh duyệt; mẫu chặt để không kết luận nhầm với PFIEV / ngành ngôn ngữ / tài năng |
| T5 khoá | "K71", "khoá 71", "71", hoặc năm nhập học "2026" (K = năm − 1955) | Người dùng hay nói năm nhập học thay vì số khoá |
| IELTS dưới mức thấp nhất | `status = ok`, `matched = false`, trả cả bảng | Có dữ liệu để trả lời ("chưa đạt mức thấp nhất 5.0"), không phải "không có dữ liệu" (B5-T8) |
