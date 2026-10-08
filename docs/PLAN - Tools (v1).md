# PLAN — Các tool Tuần 3 (v1)

**Ngày:** 2026-10-06 · **Trạng thái:** anh đã chốt mục 10 (2026-10-07); chi tiết Entity Resolution + T1/T2 ở `PLAN - Entity Resolution + Admission Tool (v1).md` — **bước 1–3 đã xong 2026-10-07**; **bước 4 (T3 `program_info`) xong 2026-10-08** theo `PLAN - T3 program_info (v1).md`; **bước 5 (T4, T5) xong 2026-10-09** theo `PLAN - T4 T5 hoc phi va chung chi (v1).md` · Gắn với PRD v1.2 mục 3.1 (độ phủ dữ liệu), 10.2 (Admission Tool), 10.3 (Entity Resolution), 12 (Citation), 13 (Fallback), 20 (Tuần 3), 21 (AC1, AC2, AC4, AC8, AC9), 24 (mã lỗi) · Đi trước: `PLAN - Backend PostgreSQL (v1).md` (lớp DB, mục 4 đã thống nhất cách tool dùng DB)

Mỗi quyết định có dòng **Vì sao**.

**Deliverable Tuần 3 theo PRD:** các tool hoạt động độc lập và có test. Kế hoạch này **không** gồm Router, LangGraph, nối tool vào LLM — những phần đó thuộc Tuần 4. Tool ở đây phải chạy và kiểm được mà không cần LLM.

---

## 1. Bộ 120 câu đòi hỏi tool gì

Phân loại 114 câu đang có (thiếu Q99–Q104) theo **chỗ lấy câu trả lời**:

| Loại câu hỏi | Ví dụ | Số câu (ước) | Tool |
|---|---|--:|---|
| Điểm chuẩn của 1–3 ngành cụ thể | Q26 IT1 2024–2025, Q29, Q30 so sánh IT1/IT2, Q34, Q45 | 6 | T1 `admission_scores` |
| Xếp hạng / cả bảng / theo nhóm ngành | Q27 cao nhất TSA, Q28 cả bảng ĐGTD 2025, Q31 khối Điện, Q32 thấp nhất, Q33 nhóm Vật liệu, Q9 "60 điểm TSA vào được ngành CNTT nào" | 6 | T2 `list_programs` |
| Chỉ tiêu, phương thức, tổ hợp, công thức, thông tin ngành | Q36, Q37, Q43, Q10/Q11/Q39 (môn chính, thang điểm), Q62, Q64 | 9 | T3 `program_info` (+ T2 cho tổng chỉ tiêu) |
| Học phí, lệ phí | Q8 lệ phí TSA, Q46 tín chỉ, Q47 Elitech, Q49 liên kết, Q58 so sánh | 5 | T4 `tuition_fees` |
| Chứng chỉ ngoại ngữ (xét tuyển / chuẩn đầu ra) | Q4 quy đổi IELTS, Q84 chuẩn đầu ra | 2 | T5 `certificate_lookup` |
| Trường/Khoa: liên hệ, đơn vị, ngành trực thuộc | (bộ 120 câu chưa có câu thuần loại này; PRD AC9 cần) | — | T6 `university_info` |
| Văn bản: quy chế, đề án, sổ tay, giới thiệu ngành/Khoa | Q1–Q25 phần lớn, Q50–Q57, Q61–Q120 | ~75 | T7 `rag_search` |
| Không có dữ liệu | Q38, Q40 (số hồ sơ, tỷ lệ chọi), một phần Q36 (chỉ tiêu theo phương thức) | 3 | Tool trả `not_found` có giải thích |

Nhiều câu cần **hai tool**: Q10 cần công thức (T3) và đoạn giải thích (T7); Q84 cần bảng quy đổi (T5) và quy định (T7). Tool chỉ cần trả đúng phần của mình. Việc ghép hai phần là việc của Synthesizer ở Tuần 4.

---

## 2. Quyết định chung cho mọi tool

| # | Quyết định | Vì sao |
|---|---|---|
| D1 | **Mỗi tool là một hàm async Python thuần**, đầu vào và đầu ra là model Pydantic, **không gọi LLM**. Tuần 4 mới bọc thành tool của LangChain/LangGraph | Deliverable Tuần 3 là "tool chạy độc lập, có test". Test không gọi LLM thì chạy nhanh, không tốn tiền, kết quả lần nào cũng như nhau. Riêng AC1 đòi tool đúng **100%**, chỉ kiểm được khi tool không phụ thuộc LLM |
| D2 | **Tool nhận đúng chữ người dùng gõ** (`programs: ["Khoa học máy tính"]`, cả mã lẫn tên đều được) và **tự gọi Entity Resolution bên trong**. Không để LLM tự đổi tên ngành ra mã | Nếu để LLM tự đổi tên ra mã, nó sẽ đoán "Khoa học máy tính" là IT1. Đây đúng là lỗi PRD 10.3 cấm: TROY-IT cũng tên "Khoa học máy tính", phải hỏi lại. Gọi resolver trong tool thì LLM không có đường nào bỏ qua 4 quy tắc khớp, cũng không tự bịa ra mã ngành không tồn tại |
| D3 | **Mọi tool trả cùng một khuôn `ToolResult`**: `status` (`ok` / `partial` / `not_found` / `ambiguous` / `invalid`), `data`, `missing` (thiếu gì, có sẵn gì), `candidates` (khi cần hỏi lại), `sources` | PRD 13.2 đòi "nói rõ thiếu cái gì và có sẵn cái gì", PRD 24 đòi phân biệt các loại lỗi. Đưa vào khuôn chung thì Synthesizer và Clarification Node (Tuần 4) chỉ cần đọc một kiểu dữ liệu. `status` ánh xạ thẳng sang mã lỗi PRD: `ambiguous` → `ENTITY_AMBIGUOUS`, `not_found` → `DATA_NOT_FOUND` / `ENTITY_NOT_FOUND`, `invalid` → `INVALID_REQUEST` |
| D4 | **Mỗi dòng số liệu mang theo `year`, `source_url`, `verification_status`** | Phục vụ citation (PRD 12, AC4). `verification_status = rule_derived` (27 dòng điểm chuẩn tính từ quy tắc +0,5) cần được nói rõ trong câu trả lời, không trình bày như số công bố |
| D5 | **Tool tự tính phép so sánh** (chênh lệch giữa các năm/ngành, xếp hạng, tổng chỉ tiêu) và trả kèm kết quả | PRD 10.2: "mọi phép so sánh/tính chênh lệch được thực hiện trên số liệu đã truy xuất, không để LLM tự ước lượng". LLM hay cộng trừ sai số thập phân |
| D6 | **Không nói năm thì lấy năm mới nhất có dữ liệu của bảng đó.** Kết quả ghi rõ năm đã dùng và các năm có sẵn (`available_years`) | "Điểm chuẩn IT1" mà không nêu năm thì gần như luôn hỏi năm gần nhất. Ghi rõ năm thì Synthesizer có thể nói "đây là số năm 2026; còn có 2024, 2025". Cách hiểu "năm nay" / "năm ngoái" là việc của Router (Tuần 4); tool chỉ nhận năm cụ thể |
| D7 | **Độ phủ theo năm đọc từ DB** (`SELECT DISTINCT year FROM quotas`…), không ghi cứng trong code | Năm sau thêm dữ liệu 2027 thì tool tự biết, không phải sửa code. Ví dụ hỏi chỉ tiêu năm 2024: tool trả `not_found` kèm `available_years = [2025, 2026]`, đúng ví dụ ở PRD 13.2 |
| D8 | **Giới hạn 3 phần tử mỗi chiều** (ngành / năm / phương thức) chỉ áp dụng cho T1. Truyền quá 3 thì trả `invalid` kèm câu fallback của PRD 10.2. Câu hỏi kiểu xếp hạng hay "cả bảng" đi qua T2 | PRD 10.2 đặt giới hạn này để giữ độ chính xác cho câu hỏi theo ngành cụ thể. Q28 "cả bảng ĐGTD 2025" là câu hỏi hợp lệ nhưng không thể hỏi bằng ≤ 3 ngành, nên cần đường riêng thay vì nới giới hạn |

**Vị trí file:**

```
backend/app/schemas/tools.py          ToolResult, Source, Missing + input/output của từng tool
backend/app/entity_resolution/
    normalize.py                      chuẩn hoá chuỗi (chuyển từ scripts/validate_aliases.py)
    resolver.py                       4 quy tắc khớp, AliasIndex nạp từ DB một lần
    scan.py                           tìm mã/alias trong cả câu hỏi (mục 3.3)
backend/app/tools/
    admission.py                      T1 admission_scores, T2 list_programs
    program_info.py                   T3
    tuition.py                        T4
    certificates.py                   T5
    university_info.py                T6
    rag_tool.py                       T7 (gọi backend/app/rag/retriever.py)
backend/app/tools/coverage.py         năm có dữ liệu theo bảng (D7)
```

---

## 3. Entity Resolution (làm đầu tiên)

### 3.1 Giao diện

```python
resolve(mention: str, entity_type: "program"|"faculty"|"certificate"|"method", year: int | None) -> Resolution
# Resolution: status = unique | clarify | group | not_found
#             codes, candidates[{code, name}], matched_by = exact | substring | fuzzy, alias
```

### 3.2 Thuật toán (đúng thứ tự PRD 10.3)

| Bước | Làm gì | Ghi chú |
|---|---|---|
| Chuẩn hoá | Bỏ dấu, thường hoá, `đ` → `d`, gộp khoảng trắng | Dùng đúng hàm `normalize()` đang có trong `validate_aliases.py` (đã xử lý bẫy chữ "đ") |
| B1 lọc năm | Bỏ các mã không có trong `program_years` của năm đang hỏi; không nói năm thì lấy năm mới nhất (D6) | "Accounting" năm 2026 → EM-E17, năm 2025 → EM4 |
| B2 khớp chính xác | Tra trong: alias + tên ngành chuẩn + chính mã ngành (kể cả `code_variant` như TEEP) | Khớp được thì **dừng**, không xét bước sau |
| B3a chuỗi con | Chỉ chạy khi B2 trượt; alias `abbrev` không tham gia | Quy tắc 3, 4 của PRD |
| B3b fuzzy | Chỉ chạy khi B3a cũng trượt; dùng `rapidfuzz` trên tên đã chuẩn hoá, chuỗi ≥ 4 ký tự. Đúng **một** ứng viên vượt ngưỡng thì trả `unique` (ghi `matched_by = fuzzy`); hai ứng viên đầu điểm sát nhau thì trả `clarify` với tối đa 3 ứng viên | PRD 3.B có "fuzzy matching ở mức phù hợp" (ví dụ gõ sai "Khoa hoc may tihn"). AC8: điểm top-1 và top-2 gần nhau thì phải hỏi lại. Ngưỡng đặt bằng bộ test ở mục 8, không đoán |
| Đọc `resolution` | `unique` → trả mã · `clarify` → **không tự chọn**, trả các ứng viên · `group` → liệt kê các ngành trong nhóm từ bảng `programs.program_group_code` | |

| # | Quyết định | Vì sao |
|---|---|---|
| E1 | **Nạp alias vào bộ nhớ một lần** khi khởi động (một câu SELECT, 253 dòng); tra cứu bằng Python | Đã thống nhất ở `PLAN - Backend PostgreSQL` mục 4. Test được mà không cần DB: dựng `AliasIndex` từ list dòng trong test |
| E2 | **`scripts/validate_aliases.py` chuyển sang import resolver của backend**, bỏ bản `simulate_lookup` riêng | PRD ghi validator "mô phỏng lại đúng 4 quy tắc". Giữ hai bản code thì sớm muộn sẽ lệch nhau, và validator báo xanh trên một thuật toán khác với thuật toán bot đang chạy |
| E3 | Thêm `entity_type = method` vào bảng alias (khoảng 15 dòng: TSA, ĐGTD, đánh giá tư duy, thi THPT, điểm thi tốt nghiệp, tài năng, XTTN 1.2/1.3, tuyển thẳng…) — **cần anh đồng ý, mục 10** | Hiện chưa có cách đổi "TSA" thành `DGTD`. Dùng chung một bảng alias thì dùng chung một resolver, và validator kiểm luôn phần này |

### 3.3 Tìm thực thể trong cả câu hỏi (`scan.py`)

Resolver nhận một **cụm từ** đã tách sẵn, nhưng người dùng gõ cả câu. Thêm hàm `scan(question)` tất định:

- Mã ngành dạng `IT1`, `IT-E10`, `TROY-IT` (lấy từ danh sách mã thật, có ranh giới từ).
- Alias khớp nguyên cụm, ưu tiên cụm dài nhất trước. Alias `abbrev` thì **phân biệt hoa/thường trên câu gốc**: "BA" (viết tắt) không được khớp với "ba năm".

**Vì sao:** Tuần 4, Router sẽ dùng `scan` làm bước đầu, chỉ nhờ LLM tách cụm từ khi `scan` không tìm ra gì. Như vậy phần lớn câu hỏi có mã hoặc tên ngành không tốn thêm lượt gọi LLM (TTFT, PRD 22.1). Còn ở Tuần 3, `scan` cho phép chạy đo Entity Resolution trên bộ 120 câu mà không cần LLM.

### 3.4 Test

- Mỗi alias trong CSV tra ra đúng tập mã đã khai báo. Đây là phép kiểm `simulate_lookup` chuyển thành pytest.
- Các ca bắt buộc của PRD: Accounting 2026/2025 · "Chemistry" không bị "Cosmetic Chemistry" nuốt · `BA` không khớp chuỗi con · "Khoa học máy tính" → hỏi lại giữa IT1 và TROY-IT · "Toán Tin" → MI1 · 7 cặp chuẩn/tiên tiến trùng tên đều phải hỏi lại.
- Chuẩn hoá: viết hoa/thường, gõ không dấu, chữ "đ", thừa khoảng trắng.
- Bộ ca có nhãn cho AC2 (≥ 95%) và AC8 (≥ 95%): mục 8.

---

## 4. Các tool SQL

| Tool | Đầu vào | Trả về | Bảng |
|---|---|---|---|
| **T1 `admission_scores`** (PRD 10.2) | `programs` ≤ 3, `years` ≤ 3, `methods` ≤ 3 (không nói phương thức = mọi phương thức) | Mỗi dòng: mã + tên ngành, năm, phương thức, nhóm tổ hợp, `score`, `scale`, `subject_combinations`, `score_note`, nguồn. **`comparisons`**: chênh lệch cùng ngành/phương thức giữa các năm, hoặc giữa các ngành trong cùng năm (D5) | `admission_scores`, `programs`, `admission_methods` |
| **T2 `list_programs`** | `year`, `metric` (`score` / `quota`), `method`, phạm vi (`all` / Trường-Khoa / nhóm ngành / tổ hợp / chưa có phương thức X), `order`, `limit` (bỏ trống = cả bảng), khoảng điểm (tuỳ chọn) | Danh sách đã sắp xếp + `total` khi `metric = quota` | như T1 + `quotas`, `program_methods`, `program_combinations` |
| **T3 `program_info`** (tool "thông tin ngành", phần có cấu trúc) | `programs` ≤ 3, `year` | Tên, Trường/Khoa, nhóm, **mô tả ngắn** (S7), bằng, thời gian, ngôn ngữ, `curriculum_url`, chỉ tiêu, các phương thức, các tổ hợp (kèm `main_subject` và **nguyên văn công thức** từ `scoring_formulas`), `is_open` của năm đó | `programs`, `program_years`, `quotas`, `program_methods`, `program_combinations`, `scoring_formulas`, `combinations` |
| **T4 `tuition_fees`** | `programs` ≤ 3 hoặc nhóm ngành, `kind` (`program` / `credit` / `admission_fee`) | Học phí theo ngành (**bắt buộc có `unit` và `terms_per_year`**), học phí tín chỉ qua `tuition_rule_members` (**kèm ghi chú "mức năm học 2024–2025"**), lệ phí xét tuyển / thi | `tuition_program`, `tuition_rules`, `tuition_rule_members`, `admission_fees` |
| **T5 `certificate_lookup`** | `certificate`, `value` (tuỳ chọn, ví dụ 6.5), **`purpose` bắt buộc** (`xet_tuyen` / `chuan_dau_ra`), `program`, `cohort` | `xet_tuyen` → `cert_bonus` (điểm thưởng / quy đổi) · `chuan_dau_ra` → `cert_output` + `language_requirements` của nhóm ngành | `cert_bonus`, `cert_cefr`, `cert_output`, `language_requirements`, `language_req_members` |

| # | Quyết định | Vì sao |
|---|---|---|
| S1 | Tách T1 và T2 thay vì một tool có nhiều chế độ | T1 khớp đúng đặc tả PRD 10.2, là chỗ đo AC1. T2 phục vụ câu hỏi xếp hạng/cả bảng (6 câu trong bộ 120), không bị giới hạn 3 phần tử |
| S2 | T4 bắt buộc trả `unit` + `terms_per_year`; học phí tín chỉ luôn kèm `academic_year` | Quy tắc bắt buộc ở PRD 3.1.A: nhầm đơn vị thì sai tới 3 lần (TROY có 3 học kỳ/năm). Anh đã chốt bảng tín chỉ 2024–2025 dùng chung cho mọi năm, và khi trả lời phải ghi rõ năm |
| S3 | T5 không có giá trị mặc định cho `purpose`. Nếu không xác định được mục đích thì trả `ambiguous` | PRD 15.1: hai bảng chứng chỉ **không được dùng lẫn nhau**. Cùng là IELTS 6.5 nhưng xét tuyển và chuẩn đầu ra cho kết quả khác nhau. Chuẩn đầu ra mà chưa rõ khoá (K70/K71) cũng phải hỏi lại (PRD 3.1.C) |
| S4 | T3 trả `main_subject` nhưng nguồn trích dẫn là **bài điểm chuẩn 2026** (nguồn của `scoring_formulas`), không phải tuyensinh247 | Anh đã chốt: nguồn bên thứ ba không vào danh sách nguồn, chatbot không trích dẫn |
| S5 | Ngành đã dừng tuyển (EM4, TROY-BA) vẫn tra được ở năm cũ. Hỏi năm 2026 thì trả `not_found` kèm "ngành dừng tuyển từ 2026, có dữ liệu 2025" | Anh đã chốt giữ hai ngành này trong `programs`, để trả lời đúng câu "năm nay có tuyển không" |
| S7 | **Bổ sung cột `short_description`** (mô tả ngắn 1–2 câu của 68 ngành) vào `program_overview_2026.csv`, rồi nạp vào bảng `programs` — **cần anh đồng ý, mục 10** | PRD 3.1.D và 15.1 xếp "mô tả ngắn ngành" vào bảng `programs`, nhưng hiện cột này chỉ có trong `data/programs/*.json`. Thư mục đó không lên git (R3 của plan Data Linking), nên DB chưa có. Thiếu cột này thì câu "ngành X là gì" luôn phải đi qua RAG, kể cả khi chỉ cần một câu tóm tắt. Phần giới thiệu dài (học gì, cơ hội việc làm) vẫn để ở RAG như cũ |
| S6 | Câu không có dữ liệu (Q38, Q40, chỉ tiêu theo từng phương thức ở Q36) trả `not_found`. `missing` ghi rõ thiếu gì; T3 vẫn trả tổng chỉ tiêu nếu có | PRD 13.2: nói rõ thiếu gì và có sẵn gì, không trả lời cụt |

**Quy ước SQL:** chỉ dùng tham số (`%(ten)s`, `= ANY(%(codes)s)`); luôn có `ORDER BY` để thứ tự kết quả cố định; tool không ghép chuỗi người dùng vào SQL (`fetch_all` đã ép kiểu `LiteralString`).

---

## 5. T6 `university_info`

Đầu vào: tên/mã Trường-Khoa **hoặc** tên/mã ngành (cho câu "ngành X thuộc Trường nào"). Trả về: mã, tên, điện thoại, email, địa chỉ, `official_channel_url`, các đơn vị trực thuộc, danh sách ngành của năm đang hỏi, kèm nguồn.

**Vì sao làm tool riêng:** PRD 3.1.D yêu cầu hỏi địa chỉ hoặc số điện thoại phải lấy từ bảng, không qua RAG ("kết quả sẽ không ổn định"). AC9 (Announcement) cũng lấy `official_channel_url` từ tool này. Thông tin SEM, SOFL chưa có đơn vị trực thuộc thì trả `partial`.

---

## 6. T7 `rag_search` + `backend/app/rag/retriever.py`

| # | Quyết định | Vì sao |
|---|---|---|
| R1 | **Lọc theo thực thể đã nhận diện**: có `program_code` / `faculty_code` thì thêm `should` theo trường đó (ưu tiên chứ không loại trừ) | PRD 11.3: lọc theo `program_code` chính xác hơn tìm theo nghĩa. Dùng `should` để vẫn lấy được chunk quy chế chung khi câu hỏi nhắc tên ngành. **Câu so sánh 2–3 ngành** (Q80 IT1/IT2, Q96 TE1/ME2, Q98) thì tìm **riêng cho từng ngành** (top-3 mỗi ngành) rồi gộp lại. Nếu tìm chung một lượt, ngành có nhiều chunk khớp hơn sẽ chiếm hết top-5, ngành kia không còn chunk nào để so |
| R2 | **Câu hỏi không nêu năm → chỉ lấy `is_latest = true` hoặc `versioned = false`.** Nêu năm thì lọc đúng năm đó | Q12 và Q18 trượt vì top-1 là đề án 2025/2024 thay cho 2026. Cờ `is_latest` đã có sẵn trong payload Qdrant nhưng `search_chunks.py` chưa dùng mặc định |
| R3 | **Tìm hai nhánh rồi gộp bằng RRF**: (a) dense không lọc chữ, (b) dense có lọc `MatchText` theo cụm từ chuyên ngành tách từ câu hỏi (danh sách cụm cố định: "môn chính", "điểm sàn", "hệ số", "cảnh báo học tập"…; mã tổ hợp `[A-D]\d{2}`/`K\d{2}`; "Điều N") | Cách đã thử ở `PLAN - Embedding` cho Q10: lọc "môn chính" thì tài liệu sai bị loại, top-2 đúng. Gộp với nhánh không lọc để không mất kết quả khi cụm từ đó không có trong tài liệu. Dùng Prefetch + Fusion RRF có sẵn trong Qdrant, không cần thêm BM25 |
| R4 | **Ngưỡng fallback dựa trên cosine của top-1 ở nhánh (a)**, không dùng điểm RRF | Điểm RRF chỉ là thứ hạng, không so được giữa các câu hỏi. PRD 13.1: ngưỡng phải đặt từ tập validation. Bước này **ghi lại phân bố điểm** của câu có đáp án và câu ngoài phạm vi; đặt ngưỡng chính thức ở Tuần 4 khi đã có câu ngoài phạm vi từ Router |
| R5 | Trả top-5 chunk, mỗi chunk kèm đủ trường citation: `document_title`, `heading`, `chuong` / `dieu_no` / `khoan_no`, `page_no`, `source_url`, `verification_status`, `chunk_id` | PRD 12: citation lấy từ metadata, LLM không được tự tạo. Thiếu trường nào thì Synthesizer không thể dựng citation hợp lệ (AC4) |
| R6 | Client Qdrant và OpenAI dạng async, cấu hình đọc từ `Settings` | Thống nhất với pool async (D8 của plan Postgres) |

**Đo:** chạy lại 77 câu có tham chiếu RAG. Hit@5 **không được thấp hơn mức hiện tại 81%** (bỏ câu đã biết thiếu dữ liệu). Mục tiêu là sửa được Q10, Q12, Q18. Kết quả ghi vào `docs/ghi_chu/`.

---

## 7. Test

| Marker | Cần gì | Chạy khi |
|---|---|---|
| (không marker) | Không cần gì: chuẩn hoá, resolver, `scan`, bộ dựng filter Qdrant, tách cụm từ | Luôn chạy |
| `db` | Postgres đã nạp | T1–T6 |
| `rag` | Qdrant + `OPENAI_API_KEY` (chạy cả bộ tốn khoảng 0,001 USD) | T7, chạy tay: `pytest -m rag` |

**Giá trị kỳ vọng lấy từ CSV**, không lấy từ cột "Đáp án mong đợi" của bộ 120 câu. Vì sao: anh đã chốt cột đó chỉ để tham khảo, không dùng để chấm; ví dụ Q8 ghi lệ phí TSA 450.000đ, trong khi dữ liệu đã chốt là 500.000đ.

---

## 8. Bộ ca có nhãn (cần cho AC1, AC2, AC8)

PRD 25 cần 50 câu Admission, còn bộ 120 câu chỉ có khoảng 20 câu số liệu, và chưa có bộ alias nào được gán nhãn. Đề xuất hai file:

- `backend/tests/eval/admission_cases.csv` (khoảng 50 ca): câu hỏi → tool + tham số mong đợi → khoá dòng kết quả mong đợi. Gồm 1 ngành, nhiều ngành, nhiều năm, ngành đã dừng tuyển, năm không có dữ liệu, quá 3 phần tử.
- `backend/tests/eval/entity_cases.csv` (khoảng 60 ca): cụm từ + năm → `unique` / `clarify` / `group` / `not_found` + các mã. Gồm gõ không dấu, gõ sai chính tả, viết tắt, tiếng Anh, tên cũ "Viện…", 7 cặp chuẩn/tiên tiến trùng tên.

Tôi soạn nháp từ CSV và bộ 120 câu, **anh duyệt** trước khi dùng để chấm. Vì sao: nhãn do chính người viết code tự đặt thì dễ đặt khớp với cách code đang chạy, mà nhãn sai thì con số ≥ 95% không còn ý nghĩa.

---

## 9. Thứ tự thực hiện

| Bước | Việc | Ước lượng | Xong khi | Vì sao ở vị trí này |
|---|---|---|---|---|
| 1 | Khung chung: `schemas/tools.py` (`ToolResult`…), `coverage.py` | ~1h | Test khuôn kết quả + độ phủ năm (2024 không có chỉ tiêu) xanh | Mọi tool dùng chung khuôn; chốt khuôn trước thì không phải sửa 7 lần |
| 2 | Entity Resolution: `normalize`, `resolver`, `scan`; đổi `validate_aliases.py` sang dùng resolver này (E2); alias phương thức (E3, nếu anh đồng ý) | ~3h | Mọi alias trong CSV tra ra đúng; các ca PRD 10.3 xanh; `validate_aliases.py` vẫn 0 lỗi | Mọi tool gọi resolver bên trong (D2) |
| 3 | T1 `admission_scores` + T2 `list_programs` | ~2,5h | Ca điểm chuẩn trong `admission_cases` đúng 100% | Nhóm câu hỏi số nhiều nhất, và là chỗ đo AC1 |
| 4 | T3 `program_info` | ~2h | Q10/Q11/Q39 trả đúng công thức; Q36 trả `partial` | Phụ thuộc phần resolver + khuôn của T1 |
| 5 | T4 `tuition_fees` + T5 `certificate_lookup` | ~2,5h | Mọi kết quả học phí có đơn vị; IELTS 6.5 cho hai kết quả khác nhau theo `purpose` | Đều là bảng tra cứu, rủi ro thấp |
| 6 | T6 `university_info` | ~1h | 10/10 Trường/Khoa trả đủ liên hệ; tra được từ mã ngành | Đơn giản nhất, dữ liệu đã đủ |
| 7 | `retriever.py` + T7 | ~3h | Hit@5 ≥ 81%, Q10/Q12/Q18 lọt top-5; có bảng phân bố điểm | Độc lập với các tool SQL; cần chạy đo nên để sau khi khung ổn |
| 8 | Bộ ca có nhãn (mục 8) + chạy đo AC1, AC2, AC8 + ghi "Đã thực hiện" | ~2h (+ thời gian anh duyệt) | Có số đo thật ghi vào `docs/ghi_chu/` | Cần đủ tool mới đo được hết |

**Tổng: khoảng 17 giờ.** Thư viện mới: `rapidfuzz` (bước 2), `qdrant-client` + `openai` cho backend (bước 7), ghim cùng phiên bản với `requirements-ingest.txt`.

---

## 10. Cần anh quyết

1. **Số ứng viên khi hỏi lại.** PRD 10.3 ghi "tối đa 3 candidate", nhưng có alias khai báo `clarify` trỏ tới 4–7 ngành (ví dụ "BK CNTT" → 7 ngành CNTT, "Vi mạch" → 4 ngành). Cắt còn 3 thì người dùng không thấy được ngành mình muốn. **Khuyến nghị:** alias đã khai báo trong bảng thì liệt kê đủ; chỉ ứng viên từ fuzzy mới cắt còn 3.
2. **Thêm alias phương thức** (E3, khoảng 15 dòng `entity_type = method` vào `entity_aliases.csv`)? Việc này sửa dữ liệu nguồn nên cần anh đồng ý. Tôi sẽ đưa danh sách để anh duyệt trước khi ghi.
3. **Không nói năm thì lấy năm nào** (D6)? **Khuyến nghị:** năm mới nhất có dữ liệu, kèm danh sách năm có sẵn. Phương án khác: riêng điểm chuẩn thì trả cả 3 năm (thông tin hơn, nhưng câu trả lời dài hơn).
4. **Fuzzy dùng `rapidfuzz` (khuyến nghị) hay `difflib` có sẵn trong Python?** `rapidfuzz` nhanh hơn và có sẵn hàm so khớp theo từ (token), hợp với tên ngành dài. `difflib` thì không phải cài thêm thư viện.
5. **Bộ ca có nhãn** (mục 8): tôi soạn nháp, anh duyệt. Anh đồng ý cách chia việc này không?
6. **Thêm `short_description` của 68 ngành vào `program_overview_2026.csv`** (S7, lấy từ `data/programs/*.json`)? Việc này sửa dữ liệu nguồn nên cần anh đồng ý.

**Anh đã chốt (2026-10-07):**

| # | Chốt | Đã làm |
|---|---|---|
| 1 | Liệt kê **đủ** các ngành của alias đã khai báo `clarify`; chỉ ứng viên từ fuzzy mới cắt còn 3 | Ghi vào thiết kế resolver |
| 2 | **Đồng ý** thêm alias phương thức | Danh sách nháp ở plan chi tiết mục 2.5, **chờ anh duyệt từng dòng** rồi mới ghi vào CSV |
| 3 | Không nói năm → **năm mới nhất** có dữ liệu, kèm các năm có sẵn | Ghi vào thiết kế T1/T2 |
| 4 | Dùng **`rapidfuzz`** | Đã cài `rapidfuzz 3.14.6` trên máy; thêm vào `backend/requirements.txt` ở bước Entity Resolution |
| 5 | **Không** chọn phương án "tôi soạn nháp bộ ca có nhãn" | Tạm để lại. Test của T1/T2 vẫn lấy giá trị kỳ vọng thẳng từ CSV; bộ ca để đo AC1/AC2/AC8 sẽ hỏi lại anh ở bước 8 |
| 6 | **Đồng ý** thêm `short_description` | Xong: cột mới trong `program_overview_2026.csv` (68/68, các cột cũ không đổi), `crawl_program_pages.py` ghi cột này khi crawl lại, `build_db.py` nạp vào `programs.short_description` (68/70 ngành; EM4, TROY-BA đã dừng tuyển nên không có trang 2026). `validate_links` 0 lỗi, `pytest backend` 6/6 |

---

## Việc nhỏ bên lề (anh làm lúc nào cũng được)

- Bộ 120 câu còn thiếu Q99–Q104.
- Cột "Tài liệu tham chiếu" của Q10 nên thêm `trang_tuyen_sinh` (bài điểm chuẩn 2026).
- Q8 ghi lệ phí TSA 450.000đ, khác dữ liệu đã chốt 500.000đ. Không ảnh hưởng gì vì cột đáp án không dùng để chấm; chỉ ghi lại để khỏi bất ngờ.
