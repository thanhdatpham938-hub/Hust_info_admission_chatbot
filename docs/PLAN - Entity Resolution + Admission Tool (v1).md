# PLAN — Entity Resolution + Admission Tool (v1, chi tiết)

**Ngày:** 2026-10-07 · **Trạng thái:** anh duyệt toàn bộ mục 7 (2026-10-07), **đã thực hiện 2026-10-07** — xem mục "Đã thực hiện" cuối file · Chi tiết hoá bước 1–3 của `PLAN - Tools (v1).md` mục 9 · Dùng các quyết định anh đã chốt ở mục 10 của plan đó.

Mỗi quyết định có dòng **Vì sao**.

**Phạm vi:** "hai tool đầu tiên" là **Entity Resolution** và **Admission Tool**. Admission Tool chia thành hai hàm: T1 `admission_scores` (điểm chuẩn của 1–3 ngành, PRD 10.2) và T2 `list_programs` (xếp hạng, cả bảng, theo Trường/Khoa hay nhóm ngành). Kèm theo là phần khung chung mà cả hai cần.

```
Câu hỏi ──► scan() ──► các cụm từ ──► resolve() ──► mã ngành / phương thức đã kiểm
                                                      │
                     T1 admission_scores / T2 list_programs ◄┘  (tool gọi resolve() bên trong)
                                                      │
                                                 ToolResult  (status, data, missing, clarifications, sources)
```

---

## 1. Khung chung (bước 1, ~1h)

### 1.1 `backend/app/schemas/common.py`

```python
class Status(StrEnum):    ok | partial | not_found | ambiguous | invalid
class ErrorCode(StrEnum): ENTITY_NOT_FOUND | ENTITY_AMBIGUOUS | DATA_NOT_FOUND | INVALID_REQUEST   # PRD 24

class Source(BaseModel):        title: str; url: str; year: int | None; verification_status: str
class Missing(BaseModel):       what: str                       # "điểm chuẩn IT1 năm 2020"
                                reason: Literal["year_out_of_range", "program_not_open",
                                                "method_no_score", "not_collected"]
                                available_years: list[int] = []
class Candidate(BaseModel):     code: str; name: str; entity_type: str
class Clarification(BaseModel): mention: str; candidates: list[Candidate]
class Resolved(BaseModel):      mention: str; entity_type: str; codes: list[str]
                                matched_by: Literal["exact", "substring", "fuzzy"]

class ToolResult(BaseModel, Generic[T]):
    status: Status
    error_code: ErrorCode | None = None
    data: T | None = None
    missing: list[Missing] = []
    clarifications: list[Clarification] = []
    resolved: list[Resolved] = []     # để Synthesizer nói "mình hiểu 'Toán Tin' là MI1"
    sources: list[Source] = []        # đã khử trùng theo url
    message: str | None = None        # câu fallback cố định khi status = invalid
```

| # | Quyết định | Vì sao |
|---|---|---|
| K1 | **Có một cụm từ cần hỏi lại thì tool không truy vấn gì**, trả `ambiguous`, dù các cụm khác đã rõ | PRD 14: thực thể đang chờ hỏi lại thì chưa được coi là "đã xác nhận". Trả một nửa số liệu rồi hỏi lại thì câu trả lời rối, người dùng không biết số nào ứng với ngành nào |
| K2 | **Cụm từ không tìm thấy thì không chặn**: vẫn truy vấn các cụm khác, trả `partial` và ghi cụm đó vào `missing` | Khác với trường hợp mơ hồ: không tìm thấy là kết quả cuối cùng, không có gì để người dùng chọn. Chặn lại chỉ làm mất phần trả lời được |
| K3 | `Missing.reason` tách 4 lý do | Mỗi lý do cần một câu trả lời khác nhau (PRD 13.2). `program_not_open`: "ngành dừng tuyển từ 2026". `year_out_of_range`: "chỉ có 2024–2026". `method_no_score`: "tuyển thẳng không có điểm chuẩn". `not_collected`: "chưa thu thập" |

### 1.2 `backend/app/tools/context.py`: dữ liệu nạp một lần

```python
class ToolContext:
    aliases: AliasIndex                 # mục 2.2
    coverage: Coverage                  # năm có dữ liệu theo bảng / theo phương thức
    methods: dict[str, Method]          # code -> tên, thang điểm, parent_method
    program_names: dict[str, str]
    @classmethod
    async def load(cls) -> "ToolContext"            # đọc Postgres qua pool (lifespan FastAPI / conftest)
    @classmethod
    def from_tables(cls, T: dict[str, list[dict]])  # dựng từ build_db.build_rows(), KHÔNG cần DB
```

`Coverage` lấy từ `SELECT DISTINCT year ...` trên các bảng `admission_scores`, `quotas`, `program_methods`, `program_combinations`, `program_years`, cộng thêm "phương thức nào có điểm ở năm nào" (`XTTN_1.2/1.3` chỉ có từ 2025).

| # | Quyết định | Vì sao |
|---|---|---|
| K4 | Có hai cách dựng: `load()` đọc Postgres, `from_tables()` đọc thẳng kết quả `build_db.build_rows()` | `from_tables` cho test Entity Resolution và `validate_aliases.py` chạy được mà **không cần Postgres**, mà vẫn dùng **đúng** logic dựng bảng của `build_db` (tên chuẩn theo đề án 2026, bỏ "(mới)"…). Không phải viết lại phần đọc CSV lần thứ hai |
| K5 | Tool nhận `ctx` qua tham số (mặc định lấy bản đã nạp) | Test truyền vào `ctx` dựng sẵn, không phải giả lập biến toàn cục |

---

## 2. Entity Resolution (bước 2, ~4h)

### 2.1 File

```
backend/app/entity_resolution/
    normalize.py   normalize() chuyển nguyên từ validate_aliases.py; compact() bỏ dấu cách cho mã ("it e10" -> "ite10")
    index.py       AliasIndex: bảng tra theo khoá đã chuẩn hoá
    resolver.py    resolve(mention, entity_type, years, ctx) -> Resolution
    scan.py        scan(question, ctx) -> list[Mention]
```

### 2.2 `AliasIndex`: lấy khoá từ đâu

| Nguồn | `entity_type` | Khoá tra | Tham gia bước |
|---|---|---|---|
| `entity_aliases` (253 dòng + alias phương thức) | theo cột | `normalize(alias)` | B2. Thêm B3 nếu không phải `abbrev` |
| `programs.program_code` | program | `normalize(code)` và `compact(code)` | Chỉ B2 (như `abbrev`) |
| `programs.program_name` | program | `normalize(name)` | B2, B3 |
| `faculties` mã + tên | faculty | như trên | mã: B2; tên: B2, B3 |
| `certificates` mã + tên | certificate | như trên | như trên |
| `admission_methods` mã + tên | method | như trên | như trên |
| `program_groups` mã + tên | program_group | như trên | như trên, `resolution = group` |
| `program_years` | — | `valid_years[program_code]` | B1 |

Tra `entity_type = program` thì xét luôn các khoá `program_group`, để "Elitech" ra nhóm ngành.

**Vì sao thêm `compact(code)`:** người dùng hay gõ "ITE10", "it e10". Hiện tại các cách gõ này chỉ khớp được nhờ fuzzy (không chắc chắn), trong khi đây là mã chính xác, nên đưa thẳng vào bước khớp chính xác.

### 2.3 Thuật toán `resolve()`

```
resolve(mention, entity_type, years=None):
    ys  = years or [năm mới nhất]                         # anh chốt: không nói năm -> năm mới nhất
    key = normalize(mention);  rỗng -> not_found
    alive(code) = entity_type != program  or  valid_years[code] ∩ ys ≠ ∅          # B1

    B2  hits = exact[key] lọc alive            -> có thì decide(hits, "exact"), DỪNG
    B3a hits = các khoá (không phải abbrev, không phải mã) CHỨA key, lọc alive, key ≥ 3 ký tự
                                                -> có thì decide(hits, "substring")
    B3b chỉ khi key ≥ 4 ký tự: rapidfuzz.process.extract(key, các khoá không phải abbrev/mã,
          scorer=fuzz.ratio, score_cutoff=NGƯỠNG), lọc alive -> decide(hits, "fuzzy")
    không có gì -> not_found; nếu khớp được nhưng bị B1 loại thì trả kèm
                   other_years = {mã: các năm có} để tool báo "ngành dừng tuyển"

decide(hits, how):
    có dòng resolution = group  -> status group, members = các ngành của nhóm còn alive
    đúng 1 mã                   -> unique
    nhiều mã, how = exact       -> clarify, liệt kê ĐỦ (anh chốt)
    nhiều mã, substring/fuzzy   -> clarify, top-3 theo điểm rapidfuzz (anh chốt: chỉ ứng viên
                                   không được khai báo mới cắt còn 3)
```

| # | Quyết định | Vì sao |
|---|---|---|
| E1 | **B1 lọc theo `program_years` của mã ngành**, không theo cột `year` của alias | Đã kiểm 2026-10-07: cột `year` của alias là năm **ghi nhận** alias. Ví dụ "Logistics và Quản lý chuỗi cung ứng" mang year=2025 (lấy từ `quotas_2025`), nhưng EM-E14 vẫn tuyển năm 2026. Lọc theo cột này thì người hỏi năm 2026 bằng tên cũ sẽ không ra gì |
| E2 | Lọc năm **trước** khi xét "B2 có trúng không" | Đúng thứ tự PRD. "Accounting" năm 2026: B2 chỉ trúng EM4, B1 loại EM4 (chỉ có 2024–2025), nên lùi xuống B3 và ra EM-E17. Nếu kiểm "B2 có trúng" trước rồi mới lọc năm thì sẽ dừng ở B2 với kết quả rỗng |
| E3 | Alias khai báo `clarify` mà sau lọc năm chỉ còn 1 mã thì trả `unique` | Ví dụ "Troy" năm 2026: TROY-BA đã dừng tuyển, chỉ còn TROY-IT. Hỏi lại khi chỉ còn một lựa chọn là thừa |
| E4 | Có nhiều mã trùng cùng một khoá chính xác thì luôn `clarify`, kể cả khi dòng alias ghi `unique` | Phòng thủ: `validate_aliases.py` đã bắt lỗi khai báo này, nhưng nếu lọt qua thì bot hỏi lại thay vì chọn bừa một mã |
| E5 | Chuỗi con (B3a) cần ≥ 3 ký tự, fuzzy (B3b) cần ≥ 4 ký tự. Fuzzy dùng `fuzz.ratio` (so cả chuỗi) | Khoá quá ngắn như "co" là chuỗi con của hàng chục tên ngành. `ratio` bắt lỗi gõ sai trên cả cụm; `token_set_ratio` cho 100 điểm khi một cụm là tập con của cụm kia, tức là lặp lại việc B3a đã làm. **Ngưỡng khởi điểm 85**, chỉnh sau khi đo (mục 5) |
| E6 | Kết quả mang `matched_by` | Kết quả từ fuzzy có thể sai. Synthesizer dùng trường này để nói "mình hiểu ý bạn là ngành X", để người dùng tự sửa nếu sai |

### 2.4 `scan(question)`: tìm cụm từ trong cả câu

```
scan(question, ctx) -> list[Mention{text, start, end, entity_type, key}]   + years: list[int]
  1. Mã ngành: regex từ danh sách mã thật (dài trước, ranh giới từ, không phân biệt hoa/thường)
  2. Alias abbrev (BA, SIE, TSA, XTTN...): khớp trên CÂU GỐC, PHÂN BIỆT hoa/thường, ranh giới từ
  3. Các khoá còn lại (tên, alias ≥ 4 ký tự): khớp trên câu đã chuẩn hoá, ranh giới từ,
     dài trước, không chồng lấn; giữ bản đồ vị trí để trả lại đúng cụm gốc
  4. Năm: \b20\d\d\b
```

| # | Quyết định | Vì sao |
|---|---|---|
| E7 | `scan` chỉ **tìm** cụm từ, không gọi `resolve` | Tách hai việc thì test riêng từng việc được. Đến Tuần 4, Router quyết định cụm nào là ngành và cụm nào là phương thức để đưa vào tool |
| E8 | Viết tắt khớp phân biệt hoa/thường trên câu gốc | Câu đã chuẩn hoá thì "BA" (Business Analytics) giống hệt "ba" trong "ba năm" |
| E9 | Cụm dài khớp trước, không chồng lấn | "Kỹ thuật Ô tô" phải ra một cụm, không bị tách thành thêm cụm "Ô tô" |

Đã biết trước một chỗ có thể nhận nhầm: "THPT" trong "trường THPT chuyên" là mã phương thức, nên `scan` sẽ báo là cụm phương thức. Ở Tuần 3 việc này không sao vì `scan` chỉ báo cụm tìm được; Tuần 4 Router sẽ lọc theo ngữ cảnh.

### 2.5 Alias phương thức: **nháp, chờ anh duyệt trước khi ghi vào `entity_aliases.csv`**

Mã và tên chính thức của 6 phương thức (`THPT`, `DGTD`, `XTTN`, `XTTN_1.1/1.2/1.3`, "Xét tuyển tài năng"…) **đã tự khớp chính xác** qua bảng `admission_methods` (mục 2.2), nên danh sách dưới đây chỉ gồm cách gọi khác. Tôi đã bỏ các dòng trùng: "ĐGTD" sau chuẩn hoá thành "dgtd", trùng với mã `DGTD`; "XTTN 1.2" thành "xttn 1 2", trùng với mã `XTTN_1.2`.

| # | alias | entity_code | alias_type | Ghi chú |
|--:|---|---|---|---|
| 1 | thi THPT | THPT | colloquial | |
| 2 | điểm thi THPT | THPT | colloquial | |
| 3 | thi tốt nghiệp THPT | THPT | colloquial | |
| 4 | điểm thi tốt nghiệp | THPT | colloquial | |
| 5 | TSA | DGTD | abbrev | Tên kỳ thi; chỉ khớp chính xác |
| 6 | đánh giá tư duy | DGTD | colloquial | |
| 7 | Thinking Skills Assessment | DGTD | en | |
| 8 | tài năng | XTTN | colloquial | Tool T1 tự mở `XTTN` thành `XTTN_1.1/1.2/1.3` qua `parent_method` |
| 9 | tuyển thẳng | XTTN_1.1 | colloquial | Không có điểm chuẩn → T1 trả `method_no_score` |
| 10 | diện 1.1 | XTTN_1.1 | colloquial | |
| 11 | diện 1.2 | XTTN_1.2 | colloquial | |
| 12 | diện 1.3 | XTTN_1.3 | colloquial | |
| 13 | hồ sơ năng lực | XTTN_1.3 | colloquial | |

Tất cả: `entity_type = method`, `resolution = unique`, `year` để trống, `dataset_version = 2026.1`. Kèm theo đó: `validate_aliases.py` thêm `method` vào danh sách loại hợp lệ và kiểm mã có trong `linking/admission_methods.csv`; `validate_links.py` nhận loại `method`.

**Không thêm:** "chứng chỉ quốc tế" (dễ khớp nhầm khi câu hỏi nói về chứng chỉ IELTS) và "học bạ" (HUST không có phương thức xét học bạ, nên để `not_found` là trả lời đúng).

### 2.6 `validate_aliases.py` dùng chung resolver của backend

- Bỏ hàm `normalize` và `simulate_lookup` riêng; import `app.entity_resolution` (thêm `backend/` vào `sys.path`), dựng `ToolContext.from_tables(build_db.build_rows())`.
- Mỗi alias được tra với `years` = các năm mà mã nó khai báo có trong `program_years`. Không truyền năm thì resolver lấy năm mới nhất, và "Accounting" (EM4, chỉ có đến 2025) sẽ bị báo sai.
- Kết quả phải giữ nguyên **0 lỗi** như hiện nay. Nếu ra lỗi mới thì đó là chỗ bản mô phỏng cũ và resolver thật đang khác nhau, cần đọc từng lỗi chứ không sửa cho qua.

**Vì sao:** PRD ghi validator "mô phỏng lại đúng 4 quy tắc". Chỉ một bản code thì cái được kiểm chính là cái bot chạy.

### 2.7 Test Entity Resolution (không cần DB)

| Nhóm | Ca |
|---|---|
| Toàn bộ alias | Mỗi alias trong CSV tra ra đúng tập mã khai báo (thay cho `simulate_lookup`) |
| 4 quy tắc PRD | "Accounting" 2026 → EM-E17, 2025 → EM4 · "Chemistry" không ra "Cosmetic Chemistry" · "BA" không khớp chuỗi con · "Khoa học máy tính" → clarify {IT1, TROY-IT} · "Toán Tin" → MI1 · 7 cặp chuẩn/tiên tiến đều clarify |
| Liệt kê đủ | "BK CNTT" → clarify đủ 7 ngành (anh chốt) |
| Năm | "Troy" 2026 → unique TROY-IT (E3) · tên cũ "Logistics và Quản lý chuỗi cung ứng" 2026 → EM-E14 (E1) |
| Chuẩn hoá | Hoa/thường, không dấu ("khoa hoc may tinh"), "đ", thừa khoảng trắng, "ITE10" / "it-e10" → IT-E10 |
| Fuzzy | "Khoa hoc may tihn" → kết quả có `matched_by = fuzzy`; cụm 3 ký tự không chạy fuzzy |
| Nhóm | "Elitech" → group, đủ thành viên của năm đang hỏi |
| `scan` | "Điểm IT1 và Toán Tin năm 2025 theo TSA" → [IT1, Toán Tin, TSA] + năm 2025 · "ba năm" không ra BA · "Kỹ thuật Ô tô" là một cụm |

---

## 3. T1 `admission_scores` (bước 3, ~2h)

### 3.1 Đầu vào / đầu ra

```python
class AdmissionScoresInput(BaseModel):
    programs: list[str]        # cụm người dùng gõ hoặc mã; 1–3 sau khi bỏ trùng
    years: list[int] = []      # rỗng -> năm mới nhất có điểm chuẩn (2026)
    methods: list[str] = []    # rỗng -> mọi phương thức

class ScoreRow(BaseModel):
    program_code; program_name; year; method_code; method_name
    combination_group; combination_group_label; subject_combinations: list[str]
    score: float; scale: int; score_note: str | None
    is_rule_derived: bool      # verification_status == rule_derived
    source: Source

class Delta(BaseModel):        # D5: tool tính, LLM không tính
    kind: Literal["year", "program"]
    method_code; combination_group
    a: str; b: str             # "2024"/"2025" hoặc mã ngành
    value_a: float; value_b: float; diff: float     # diff = b - a, Decimal rồi làm tròn 0,01

class AdmissionScoresData(BaseModel): rows: list[ScoreRow]; deltas: list[Delta]
```

### 3.2 Các bước xử lý

1. **Kiểm số lượng**: bỏ trùng; chiều nào > 3 thì trả `invalid` với `message` = câu fallback PRD 10.2: *"Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác."*
2. **Năm**: rỗng thì lấy năm mới nhất. Năm ngoài `coverage["admission_scores"]` → `Missing(year_out_of_range, available_years=[2024, 2025, 2026])`, các năm còn lại vẫn truy vấn.
3. **Phương thức**: `resolve(..., "method")`. `XTTN` mở thành các mã con qua `parent_method`. Mơ hồ hoặc không tìm thấy thì xử lý theo K1/K2.
4. **Ngành**: `resolve(..., "program", years)`.
   - `clarify` → trả `ambiguous` (K1).
   - `group` → nhóm có nhiều hơn 3 ngành nên trả `invalid`, `message` gợi ý dùng `list_programs`.
   - Mã đã dừng tuyển ở năm hỏi → `Missing(program_not_open, available_years)`.
5. **Truy vấn** (một câu SQL):

```sql
SELECT s.program_code, p.program_name, s.year, s.method_code, m.method_name,
       s.combination_group, s.subject_combinations, s.score, s.scale, s.score_note,
       s.source, s.source_url, s.verification_status
FROM admission_scores s
JOIN programs p USING (program_code)
JOIN admission_methods m USING (method_code)
WHERE s.program_code = ANY(%(codes)s)
  AND s.year = ANY(%(years)s)
  AND (%(methods)s::text[] IS NULL OR s.method_code = ANY(%(methods)s))
ORDER BY s.program_code, s.year, s.method_code, s.combination_group
```

6. **Missing theo từng tổ hợp đã hỏi** (ngành × năm, thêm phương thức nếu người dùng nêu): không có dòng thì gán lý do theo thứ tự `program_not_open` → `method_no_score` (phương thức không có điểm năm đó, ví dụ `XTTN_1.1`, hoặc XTTN năm 2024) → `not_collected`.
7. **Chênh lệch**: chỉ so **cùng phương thức và cùng nhóm tổ hợp**.
   - Theo năm: các năm liền kề của cùng một ngành.
   - Theo ngành: từng cặp trong ≤ 3 ngành, cùng năm.
   - Tính bằng `Decimal` rồi mới đổi ra `float`.
8. **Trạng thái**: có dòng và không thiếu gì → `ok`; có dòng và có thiếu → `partial`; không có dòng nào → `not_found` (`DATA_NOT_FOUND` hoặc `ENTITY_NOT_FOUND`).

| # | Quyết định | Vì sao |
|---|---|---|
| A1 | Không so điểm khác phương thức hoặc khác nhóm tổ hợp | THPT thang 30, ĐGTD thang 100. Nhóm `ky_thuat` và `kinh_te_gd_nn` của cùng một ngành lệch nhau 0,5 điểm theo quy tắc, không phải do điểm thay đổi |
| A2 | Nhãn nhóm tổ hợp: `tat_ca` → "mọi tổ hợp", `ky_thuat` → "tổ hợp khối ngành kỹ thuật", `kinh_te_gd_nn` → "tổ hợp khối ngành kinh tế, giáo dục, ngoại ngữ" (**chờ anh duyệt**, mục 7) | Mã nội bộ không đưa ra cho người dùng được. Hai nhãn sau lấy đúng cách gọi trong `score_note` (từ bài công bố điểm chuẩn). Nhãn đặt ở một chỗ thì T2 dùng lại được |
| A3 | `is_rule_derived` trên từng dòng | 27 dòng điểm chuẩn tính theo quy tắc +0,5 không có trên bảng công bố; câu trả lời phải nói rõ điều này (PRD 26) |
| A4 | `score` trả về `float`, `scale` luôn đi kèm | Đầu ra cho LLM là JSON: `Decimal` sẽ thành chuỗi `"29.39"`. Thiếu thang điểm thì "86,97" không biết là trên 100 hay trên 30 |

### 3.3 Test T1 (marker `db`)

| Ca | Kỳ vọng |
|---|---|
| **Quét toàn bộ dữ liệu** | Với **mỗi** dòng trong 3 file `admission_scores_*.csv` (687 dòng), gọi T1 với (mã, năm, phương thức) phải trả đúng dòng đó, đúng điểm, đúng thang. Đây là AC1 "tool accuracy 100%" đo trên toàn bộ dữ liệu, không chỉ vài câu mẫu |
| Q26: IT1, THPT, 2024 + 2025 | 2 dòng, đúng điểm trong CSV; 1 `Delta(kind=year)` = điểm 2025 − điểm 2024 |
| Q30: IT1 + IT2, THPT, 2024–2026 | 6 dòng; chênh lệch theo năm và theo ngành |
| "Khoa học máy tính" | `ambiguous`, ứng viên {IT1, TROY-IT}, `data` rỗng |
| 4 ngành | `invalid`, đúng câu PRD 10.2 |
| EM4 năm 2026 | `Missing(program_not_open, available_years=[2024, 2025])` |
| IT1 năm 2020 | `Missing(year_out_of_range, [2024, 2025, 2026])` |
| IT1, XTTN, 2024 | `method_no_score` |
| IT1, không nói năm | Năm 2026; `resolved` ghi IT1 |
| FL3 2025 THPT | 2 dòng (khác nhóm tổ hợp), dòng `ky_thuat` có `is_rule_derived = true`, không có `Delta` giữa hai dòng |
| "TSA" (khi alias đã được duyệt) | Ra `DGTD` |
| Nguồn | Mọi `source_url` của các dòng trả về đều có trong `sources` |

---

## 4. T2 `list_programs` (bước 4, ~2,5h)

### 4.1 Đầu vào / đầu ra

```python
class ListProgramsInput(BaseModel):
    metric: Literal["score", "quota"]
    years: list[int] = []                 # ≤ 3; rỗng -> năm mới nhất của bảng tương ứng
    method: str | None = None             # metric=score; None -> xếp riêng từng phương thức
    faculty: str | None = None            # cụm tên Trường/Khoa
    program_group: str | None = None      # cụm tên nhóm (Elitech, PFIEV...)
    programs: list[str] = []              # cụm tên ngành, KHÔNG giới hạn 3 (mục 4.2, T2-3)
    combination: str | None = None        # mã tổ hợp, vd D01
    without_method: str | None = None     # ngành KHÔNG xét phương thức này (Q43)
    score_min: float | None = None; score_max: float | None = None
    order: Literal["desc", "asc"] = "desc"
    limit: int | None = 10                # None = cả bảng; > 100 -> invalid

class ListRow(BaseModel):
    rank: int; program_code; program_name; faculty_code; faculty_name; program_group_code
    year; method_code | None; combination_group | None; combination_group_label | None
    value: float; scale: int | None; is_rule_derived: bool; source: Source
class GroupStat(BaseModel):   # mỗi (năm, phương thức, nhóm tổ hợp) — hoặc mỗi năm với chỉ tiêu
    year; method_code | None; count: int; min: float; max: float; total: float | None   # total chỉ cho quota
class ListProgramsData(BaseModel):
    rows: list[ListRow]; stats: list[GroupStat]; deltas: list[Delta]
    total_rows: int; truncated: bool
```

### 4.2 Xử lý

**`metric = score`**: một câu SQL; xếp hạng bằng `RANK()` theo từng (năm, phương thức), rồi cắt `limit` cho **mỗi nhóm**.

```sql
WITH f AS (
  SELECT s.*, p.program_name, p.faculty_code, fa.faculty_name, p.program_group_code
  FROM admission_scores s
  JOIN programs p USING (program_code) JOIN faculties fa USING (faculty_code)
  WHERE s.year = ANY(%(years)s) AND s.method_code = ANY(%(methods)s)
    AND (%(faculty)s::text   IS NULL OR p.faculty_code = %(faculty)s)
    AND (%(grp)s::text       IS NULL OR p.program_group_code = %(grp)s)
    AND (%(codes)s::text[]   IS NULL OR s.program_code = ANY(%(codes)s))
    AND (%(combo)s::text     IS NULL OR %(combo)s = ANY(string_to_array(s.subject_combinations, ';')))
    AND (%(without)s::text   IS NULL OR NOT EXISTS (SELECT 1 FROM program_methods pm
            WHERE pm.program_code = s.program_code AND pm.year = s.year AND pm.method_code = %(without)s))
    AND (%(smin)s::numeric   IS NULL OR s.score >= %(smin)s)
    AND (%(smax)s::numeric   IS NULL OR s.score <= %(smax)s))
SELECT *, RANK() OVER (PARTITION BY year, method_code ORDER BY score DESC) AS rnk FROM f
ORDER BY year, method_code, rnk, program_code
```

Chiều sắp xếp: hai chuỗi SQL viết sẵn (`DESC` và `ASC`), chọn theo `order`. **Vì sao:** PostgreSQL không truyền được `ASC`/`DESC` bằng tham số, mà ghép chuỗi người dùng vào SQL thì vi phạm quy ước `LiteralString`.

**`metric = quota`**: truy vấn `quotas` ⨝ `programs` với cùng bộ lọc (trừ lọc điểm). `stats.total` là tổng chỉ tiêu mỗi năm, `deltas` là chênh lệch tổng giữa các năm (Q37).

| # | Quyết định | Vì sao |
|---|---|---|
| T2-1 | **Xếp hạng theo dòng** (ngành × nhóm tổ hợp), không gộp theo ngành | EM3 năm 2025 có hai mức THPT (24,8 và 24,3) theo khối. Gộp lại thì mất mức thấp hơn, nên câu "ngành nào thấp nhất" (Q32) sẽ trả lời sai |
| T2-2 | `method = None` thì xếp **riêng từng phương thức** | Không xếp chung thang 30 với thang 100. Q32 "thấp nhất năm ngoái" không nêu phương thức, nên trả mức thấp nhất của mỗi phương thức |
| T2-3 | `programs` của T2 **không** giới hạn 3. Alias khai báo `clarify` thì **lấy tất cả ứng viên** thay vì hỏi lại (**chờ anh duyệt**, mục 7) | T2 là liệt kê: mỗi dòng ghi rõ mã ngành nên không có nguy cơ gán số của ngành này cho ngành kia, là điều mà bước hỏi lại ở T1 phải chặn. Câu như Q9 "các ngành CNTT" chính là muốn xem cả nhóm |
| T2-4 | Lọc tổ hợp theo `subject_combinations` **của từng dòng điểm**, không theo `program_combinations` | Dùng được cho cả 2024–2025 (bảng `program_combinations` chỉ có 2026), và đúng với ngành có hai mức điểm theo khối. Năm 2024 thì thêm ghi chú "chỉ có tổ hợp đại diện" (đúng ví dụ ở PRD 13.2) |
| T2-5 | Chỉ tiêu theo phương thức (Q36) → `Missing(not_collected)`, vẫn trả tổng chỉ tiêu của ngành | Dữ liệu chỉ có `quota_type = tong_nganh`. Nói rõ thiếu gì, có sẵn gì |
| T2-6 | `limit` mặc định 10, `None` = cả bảng, tối đa 100 | Q28 "cho xin cả bảng" cần đủ 65 ngành. Đặt trần để LLM không lỡ tay kéo về hàng nghìn dòng khi bộ lọc trống |
| T2-7 | Tool chỉ trả số liệu, không tư vấn "có đỗ không" | PRD 4.2 để tư vấn quyết định ngoài phạm vi. Q9 vẫn có số để trả lời ("các ngành CNTT năm 2025 lấy từ … đến … điểm TSA"); câu nhắc "không dự đoán khả năng đỗ" là việc của Synthesizer |

### 4.3 Test T2 (marker `db`)

| Ca (câu trong bộ 120) | Kỳ vọng (tính từ CSV ngay trong test) |
|---|---|
| Q27: DGTD, năm mới nhất, desc, limit 5 | Đúng top-5 tính từ `admission_scores_2026.csv`, có xử lý điểm bằng nhau (cùng hạng) |
| Q28: DGTD 2025, cả bảng | 65 dòng, `truncated = false` |
| Q32: 2025, asc, limit 1, không nêu phương thức | Mỗi phương thức một dòng thấp nhất |
| Q31: Trường Điện – Điện tử, THPT, 2024–2026 | Mọi dòng thuộc Trường đó; `deltas` theo năm của từng ngành |
| Q33: Trường Vật liệu, THPT | `stats` min/max đúng |
| "Elitech", 2026 | Mọi dòng `program_group_code = elitech` |
| D01, 2026 | Mọi dòng có D01 trong `subject_combinations` |
| Q37: quota 2025 + 2026 | `stats.total` đúng tổng trong CSV; `Delta` 2025 → 2026 |
| quota 2024 | `not_found`, `available_years = [2025, 2026]` |
| quota + method THPT (Q36) | Trả tổng chỉ tiêu + `Missing(not_collected)` |
| Q43: without_method THPT, 2026 | Khớp phép tính trên `program_methods_2026.csv` |
| limit 500 | `invalid` |

---

## 5. Đo Entity Resolution trên bộ 120 câu (cuối bước 2)

Chạy `scan` + `resolve` trên 114 câu, xuất bảng `câu → cụm tìm được → mã` vào `docs/ghi_chu/2026-10-xx - Ket qua entity resolution.md`. **Mục đích:** đọc bằng mắt để chỉnh ngưỡng fuzzy và phát hiện alias còn thiếu. Đây **chưa phải** số đo AC2/AC8, vì anh chưa chọn ai soạn bộ ca có nhãn (sẽ hỏi lại ở bước 8 của `PLAN - Tools`).

---

## 6. Thứ tự, tiêu chí xong, file đụng tới

| Bước | Việc | Ước lượng | Xong khi |
|---|---|---|---|
| 1 | `schemas/common.py`, `tools/context.py` (+ `Coverage`) | ~1h | Test khuôn kết quả; `Coverage` báo chỉ tiêu có 2025–2026, XTTN có từ 2025 |
| 2a | `normalize.py`, `index.py`, `resolver.py` + test | ~2h | Mọi ca mục 2.7 (trừ `scan`) xanh, không cần DB |
| 2b | `scan.py` + test | ~1h | Ca `scan` ở 2.7 xanh |
| 2c | Ghi alias phương thức (sau khi anh duyệt 2.5), sửa `validate_aliases.py` (2.6) + `validate_links.py` | ~1h | `validate_aliases` 0 lỗi, `validate_links` 0 lỗi |
| 2d | Đo trên bộ 120 câu (mục 5) | ~0,5h | Có file ghi chú |
| 3 | `tools/admission.py`: T1 + test | ~2h | Quét 687 dòng đúng 100%; mọi ca 3.3 xanh |
| 4 | T2 + test | ~2,5h | Mọi ca 4.3 xanh |
| 5 | Ghi "Đã thực hiện" vào plan này; cập nhật `cautrucduan.md`, `memory.md`, `backend/requirements.txt` (`rapidfuzz==3.14.6`) | ~0,5h | |

**Tổng: khoảng 10,5 giờ.**

---

## 7. Cần anh duyệt

1. **Danh sách 13 alias phương thức** ở mục 2.5: giữ, bỏ hay sửa dòng nào? Tôi chỉ ghi vào CSV sau khi anh duyệt.
2. **T2 gặp alias mơ hồ thì lấy tất cả ứng viên** thay vì hỏi lại (T2-3)? Khuyến nghị: có. T1 vẫn luôn hỏi lại.
3. **Cách viết nhãn nhóm tổ hợp** (A2): "mọi tổ hợp" / "tổ hợp khối ngành kỹ thuật" / "tổ hợp khối ngành kinh tế, giáo dục, ngoại ngữ" (hai nhãn sau theo đúng cách gọi trong `score_note`). Anh muốn gọi khác không?

---

# Đã thực hiện (2026-10-07)

Anh duyệt cả 3 điểm ở mục 7 đúng như đề xuất: 13 alias phương thức, T2 lấy hết ứng viên khi mơ hồ, nhãn nhóm tổ hợp theo `score_note`.

## Kết quả

| Bước | Kết quả |
|---|---|
| 1 | `app/schemas/common.py` (`ToolResult`…), `app/tools/context.py` (`ToolContext`: alias + `Scanner` + độ phủ năm + phương thức + mã tổ hợp; dựng từ Postgres hoặc từ `build_db.build_rows()`) |
| 2a | `app/entity_resolution/{normalize,index,resolver}.py`. Mọi ca ở mục 2.7 xanh, không cần DB |
| 2b | `app/entity_resolution/scan.py`. Dựng một lần mất 6 ms, mỗi câu hỏi 0–2 ms |
| 2c | 13 alias phương thức đã ghi vào `entity_aliases.csv` (266 dòng). `validate_aliases.py` dùng resolver của backend, nay kiểm **mọi loại** thực thể (bản cũ chỉ kiểm `program`): **0 lỗi, 0 cảnh báo**. `validate_links.py` nhận loại `method`: 0 lỗi |
| 2d | `scripts/eval_entity_scan.py` → `docs/ghi_chu/2026-10-07 - Ket qua entity resolution.md`. 114 câu, 62 câu có cụm; các cụm ra 85 `unique` / 19 `group` / 8 `clarify`, không cụm nào `not_found` |
| 3 | `app/schemas/admission.py`, `app/tools/admission.py` (T1). **Quét đủ 687 dòng điểm chuẩn: đúng 100%** (AC1 tool accuracy trên toàn bộ dữ liệu) |
| 4 | T2 trong cùng file. Mọi ca ở mục 4.3 xanh |
| Tổng | `pytest backend`: **80 passed**, khoảng 4 giây. Mỗi lần gọi tool mất 0,6–12 ms (PRD 22.2 đòi < 500 ms) |

## Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| Cách chấm fuzzy | `window_ratio`: `fuzz.ratio` so với đoạn từ liên tiếp khớp nhất trong tên (dài n−1 đến n+1 từ); cụm 1 từ thì so cả chuỗi. Plan ghi `fuzz.ratio` so cả chuỗi | Đã đo trên 10 lỗi gõ. `ratio` so cả chuỗi trượt khi cụm gõ sai chỉ là một phần của tên dài ("khoa hoc may tihn" vs "cntt khoa hoc may tinh": 82 điểm). `partial_ratio`/`WRatio` cho "hoa hoc" 100 điểm (khớp nhầm). So theo cửa sổ từ giữ được cả hai yêu cầu |
| Fuzzy nhiều ứng viên | Top-1 hơn top-2 từ 10 điểm trở lên thì trả `unique`, còn lại hỏi lại top-3 | AC8: chỉ hỏi lại khi các ứng viên sát điểm nhau |
| Chuỗi con (B3a) | Khớp **nguyên từ** | "tinh" không được khớp vào giữa từ khác. Gõ thiếu chữ ("kinh doan") thì để fuzzy bắt |
| Mã nhóm ngành | Mã nội bộ `chuan`/`elitech`/`pfiev`/`lien_ket` **không** làm khoá tra | Validator mới bắt được: khoá `pfiev` lấn alias "PFIEV" anh đã chốt (3 ngành, có IT-EP). Mã nhóm do mình tự đặt ở bước Data Linking, người dùng không gõ |
| `group` ngoài nhóm ngành | Trả tất cả mã đã khai báo (TOEIC → 4 kỹ năng) | Validator mới bắt được: bản đầu hiểu mọi `group` là nhóm ngành |
| `Missing.reason` | Thêm `entity_not_found` (lý do thứ 5) | K2: cụm không tìm thấy không chặn truy vấn nhưng vẫn phải báo lại |
| Mã gõ không gạch nối | Thêm khoá `compact` ("ite10") trong resolver và trong `scan` | Đúng mục 2.2; `scan` cũng cần thì mới tìm được trong câu |
| T2 `program_group` | Nếu cụm không ra nhóm mà ra ngành, dùng các ngành đó làm bộ lọc | Người dùng/Router có thể đưa tên ngành vào ô nhóm; bỏ qua thì mất bộ lọc |
| T2 `stats` | Tính theo (năm, phương thức) trên **mọi** dòng khớp lọc, trước khi cắt `limit` | Q33 "dao động trong khoảng nào" cần min/max của cả nhóm, không chỉ của top-10 |
| T2 `Delta(kind="total")` | Chênh lệch tổng chỉ tiêu giữa các năm | Q37 |
| T2 `notes` | Ghi chú cố định khi lọc tổ hợp năm 2024 | PRD 13.2: chỉ có tổ hợp đại diện |
| `build_db.py` | `connect_timeout=10` | Lúc làm Docker Desktop đang tắt, `--postgres` treo quá 2 phút; giờ báo lỗi sau 10 giây |
| `.gitkeep` | `git rm` ở `schemas/`, `tools/`, `entity_resolution/`, thay bằng `__init__.py` | Thư mục đã có code thật |

## Còn lại

- **4 alias có thể còn thiếu** ("công nghệ thông tin", "Điện - Điện tử", "ngành Vật liệu", "Leibniz"): bảng gợi ý ở cuối file ghi chú entity resolution. Đây là sửa dữ liệu nguồn nên **chờ anh quyết**.
- **Bộ ca có nhãn để đo AC2/AC8**: anh chưa chọn ai soạn (mục 10.5 của `PLAN - Tools`).
- Ghi cho Router (Tuần 4): ưu tiên mã trong ngoặc ngay sau tên ngành (Q96); "THPT" trong "trường THPT chuyên" không phải phương thức; "2026-2027" là một năm học.
- Tiếp theo theo `PLAN - Tools (v1)` mục 9: bước 4 T3 `program_info`.
