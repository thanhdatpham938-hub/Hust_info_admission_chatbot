# PLAN — Kết nối các bảng dữ liệu (v1)

**Ngày:** 2026-09-26 · **Trạng thái:** bản nháp để anh đọc và sửa · Gắn với PRD v1.2 mục 10.3 (khớp thực thể), 15.1 (schema) · Đi kèm: `PLAN - Metadata Design (v2).md`

Mỗi quyết định có dòng **Vì sao**.

## Vì sao cần kế hoạch riêng cho việc nối bảng

Câu hỏi thật của học sinh hay đi qua **nhiều bảng cùng lúc**:

- "IT1 xét tổ hợp nào, tính điểm thế nào, điểm chuẩn 3 năm gần đây?" → tổ hợp + công thức + điểm chuẩn
- "Các ngành của Trường Kinh tế năm 2026 lấy bao nhiêu điểm, học phí bao nhiêu?" → Trường/Khoa + ngành + điểm + học phí
- "Em có IELTS 6.5 thì được quy đổi mấy điểm, có đủ chuẩn đầu ra ngành IT-EP không?" → chứng chỉ + quy đổi + chuẩn đầu ra theo nhóm ngành

Mỗi bảng đúng riêng lẻ vẫn chưa đủ: nếu **khoá nối** giữa chúng lệch (tên ngành viết 2 kiểu, mã Khoa sai, tên chứng chỉ khác nhau) thì phép nối âm thầm trả thiếu dòng — loại lỗi khó thấy nhất vì câu trả lời vẫn "trông đúng".

---

## 1. Hiện trạng đo được (2026-09-26)

### Đã tốt

| Kiểm tra | Kết quả |
|---|---|
| `program_code` ở 10 bảng số liệu → danh mục ngành cùng năm | **0 mã mồ côi** |
| 68 file `data/programs/*.json` ↔ danh mục ngành 2026 | khớp 68/68 |
| Mã tổ hợp trong bảng tổ hợp và bảng điểm chuẩn → bảng giải nghĩa tổ hợp | 0 mồ côi |
| `formula_type` → bảng công thức | 0 mồ côi |
| `entity_aliases` → mã ngành | 0 mồ côi |

**Vì sao được như vậy:** từ đầu mọi bảng đều dùng `program_code` làm khoá và mã đã được chuẩn hoá (TEEP → TE-EP, "CH -E20" → CH-E20 qua `program_aliases`). Phần này giữ nguyên.

### Chỗ sẽ gây lỗi khi nối

| # | Vấn đề | Số liệu | Hậu quả nếu để nguyên |
|---|---|---|---|
| L1 | **Không có bảng Trường/Khoa làm chuẩn.** CSV ngành chỉ có `faculty_name` (vd "Trường CNTT&TT"), `info.json` của Khoa ghi tên khác ("Trường CNTT và TT"); JSON ngành gán **TE1 → FED** (sai, TE1 thuộc Trường Cơ khí) và **TROY-IT không có mã** | 10 Khoa, 2 ngành sai/thiếu | Hỏi "ngành của Trường Cơ khí" thiếu TE1; chunk trang ngành không gắn được `faculty_code` |
| L2 | **Một mã ngành, nhiều tên** giữa các bảng | 49/68 mã có ≥ 2 tên (vd IT-E7: "Công nghệ thông tin (Global ICT)" / "Công nghệ Thông tin Global ICT") | Bot hiển thị tên khác nhau trong cùng một câu trả lời; ai nối bằng tên thay vì mã sẽ trượt |
| L3 | **Phương thức khác độ chi tiết:** bảng phương thức ghi `XTTN`, bảng điểm chuẩn ghi `XTTN_1.2` / `XTTN_1.3` | 3 bảng | "IT1 có xét XTTN không?" nối sang điểm chuẩn bằng `=` sẽ ra rỗng |
| L4 | **Danh mục ngành đổi theo năm:** EM4, TROY-BA chỉ có 2025; 5 ngành mới 2026; FL3 mới từ 2025 | 64 / 65 / 68 ngành | Hỏi "TROY-BA 2026" phải trả lời "năm 2026 không tuyển", không phải "không có dữ liệu" |
| L5 | **Bảng khoá bằng chữ tự do, không bằng mã:** `tuition_by_year.program_codes` ("36 ngành (Cơ điện tử, …)"), `tuition_credit.programs_listed`, `language_exit_requirement.program_group` ("CTĐT chuẩn (trừ nhóm ngành ngôn ngữ)") | 3 bảng, 55 dòng | Không trả lời được "học phí tín chỉ ngành IT1" hay "chuẩn đầu ra ngành IT-EP" bằng truy vấn — phải để LLM đọc chữ rồi đoán |
| L6 | **Tên chứng chỉ không thống nhất** giữa 3 bảng chứng chỉ: `Aptis Esol` / `Aptis ESOL` / `APTIS ESOL` | 3 bảng | Nối "chứng chỉ → quy đổi → chuẩn đầu ra" trượt ở chỗ khác hoa/thường |
| L7 | **Từ điển alias chỉ có ngành** (168 dòng) và nhóm ngành (6); **không có Trường/Khoa, chứng chỉ** | — | "Trường CNTT", "SoICT", "viện điện" không nhận ra được |
| L8 | FL1–FL4 xét ĐGTD (có trong bảng phương thức và điểm chuẩn TSA) nhưng **thiếu dòng tổ hợp K00** | 4 ngành | Hỏi "FL1 xét ĐGTD không" theo bảng tổ hợp ra "không" — sai |
| L9 | Tổ hợp theo ngành **chỉ có năm 2026**; 2024–2025 không có | — | Đã biết từ trước (v1); câu hỏi tổ hợp năm cũ phải fallback theo PRD 13.2 |

---

## 2. Mô hình đích

Chia hai loại bảng: **bảng danh mục** (mỗi thực thể một dòng, là nơi duy nhất giữ tên/thuộc tính) và **bảng số liệu** (chỉ giữ mã + số, nối về danh mục).

**Vì sao tách như vậy:** L1, L2, L6 đều cùng một gốc — cùng một thứ (ngành, Khoa, chứng chỉ) được ghi tên ở nhiều nơi. Chỉ cho tên sống ở **một** bảng thì lệch tên không thể xảy ra nữa, và sửa tên chỉ sửa một chỗ.

### 2.1 Bảng danh mục

| Bảng | Khoá chính | Cột chính | Lấy từ |
|---|---|---|---|
| `faculties` (mới) | `faculty_code` | tên chuẩn, tên ngắn, website, link giới thiệu | 10 file `data/faculty/*/info.json` |
| `programs` (gộp 3 file `programs_<năm>`) | `program_code` | tên chuẩn, `faculty_code`, `program_group` (chuẩn / Elitech / PFIEV / liên kết), ngôn ngữ, bằng | `programs_2026` + `program_overview_2026` + quotas (`program_group`) |
| `program_years` (mới) | (`program_code`, `year`) | ngành có tuyển năm đó không | `programs_2024/25/26` |
| `admission_methods` (mới) | `method_code` | tên hiển thị, `parent_method` (`XTTN_1.2` → `XTTN`), thang điểm | cố định 6 dòng |
| `combinations` | `combination_code` | các môn | `subject_combinations_ref` (đã có) |
| `scoring_formulas` | `formula_type` | công thức, thang | đã có (`scoring_formulas_2026`) |
| `certificates` (mới) | `cert_code` (vd `IELTS_ACADEMIC`) | tên hiển thị | gom từ 3 bảng chứng chỉ |

**Vì sao `programs` là một bảng cho mọi năm, kèm `program_years`:** mã ngành ổn định qua năm (IT1 năm 2024 và 2026 là một ngành); để 3 file danh mục riêng thì mỗi lần hỏi liên năm phải gộp tay. `program_years` giải quyết L4: phân biệt được "không tuyển năm đó" với "không có dữ liệu".
**Vì sao tên chuẩn lấy từ `programs_2026`:** đây là tên trong đề án 2026 — văn bản chính thức mới nhất. Các tên khác (trên ảnh điểm chuẩn, trang ngành) giữ lại trong `entity_aliases` để vẫn nhận ra khi người dùng gõ.
**Vì sao `admission_methods` có `parent_method`:** giữ được cả hai độ chi tiết (L3) — "có xét XTTN không" hỏi ở cấp cha, "điểm chuẩn XTTN 1.3" hỏi ở cấp con, không phải chọn bỏ một bên.
**Vì sao cần `certificates`:** 3 bảng chứng chỉ phục vụ 3 mục đích khác nhau (quy đổi điểm tuyển sinh / tương đương CEFR / chuẩn đầu ra) — PRD 15.1 đã cảnh báo không được trộn. Giữ 3 bảng riêng, chỉ dùng chung **mã** chứng chỉ để nối (L6).

### 2.2 Bảng số liệu (chỉ giữ mã)

| Bảng | Khoá | Nối về |
|---|---|---|
| `admission_scores` (gộp 3 năm) | `program_code`, `year`, `method_code`, `combination_group` | programs, admission_methods |
| `quotas` | `program_code`, `year` | programs |
| `program_methods` | `program_code`, `year`, `method_code` | programs, admission_methods |
| `program_combinations` | `program_code`, `year`, `method_code`, `combination_code` (+ `main_subject`, `formula_type`) | programs, combinations, scoring_formulas |
| `tuition_program` | `program_code`, `year` | programs |
| `tuition_rules` | `rule_id`, `year` | qua bảng cầu `tuition_rule_members` |
| `cert_bonus_conversion` / `cert_cefr_equivalence` / `cert_equivalence_output` | `cert_code`, `cert_value`, `year` | certificates |
| `language_exit_requirement` | `req_id`, `year`, `cohort` | qua bảng cầu `language_req_members` |
| `admission_fees` | `fee_type`, `year` | — |

**Vì sao gộp 3 năm điểm chuẩn thành một bảng có cột `year`:** câu hỏi xu hướng ("điểm IT1 3 năm") là một truy vấn thay vì ba; schema đã giống nhau hoàn toàn.
**Vì sao bỏ `program_name` khỏi bảng số liệu:** đây chính là chỗ sinh ra 49 mã nhiều tên (L2). Giữ bản gốc ở `data/processed/` để đối chiếu nguồn; bảng nạp vào DB chỉ có mã.

### 2.3 Bảng cầu cho các quy định theo nhóm ngành (L5)

Học phí tín chỉ 2024–2025 và chuẩn đầu ra ngoại ngữ **không quy định theo từng ngành mà theo nhóm** ("CTĐT chuẩn trừ nhóm ngôn ngữ", "nhóm 550 nghìn/tín chỉ"). Thêm bảng cầu `(rule_id, program_code)` liệt kê tường minh ngành nào thuộc nhóm nào.

**Vì sao làm bảng cầu thay vì để LLM đọc chữ:** nguyên tắc PRD — số liệu trả lời phải đến từ truy vấn, LLM không tự suy. "IT-EP có thuộc 'Chương trình tiên tiến ELITECH tăng cường ngoại ngữ' không?" là suy luận mà mô hình dễ sai, trong khi con người gán một lần là xong.
**Vì sao làm tay, không script:** các nhóm được mô tả bằng chữ tự do ("và các CTĐT chuẩn khác", "trừ nhóm ngành ngôn ngữ"). Script so tên sẽ gán sai ở đúng những chỗ mơ hồ nhất. 55 dòng nhóm → ước chừng 68 ngành × 2 bảng, làm tay kèm cột `note` ghi căn cứ.
**Rủi ro phải ghi rõ:** bảng cầu là **diễn giải của mình** từ văn bản, nên `verification_status = rule_derived` và citation vẫn trỏ về văn bản gốc.

---

## 3. Nối RAG với bảng

RAG và SQL không nối bằng JOIN mà bằng **metadata dùng chung mã**:

| Chunk | Mang mã | Dùng để |
|---|---|---|
| Trang ngành (151) | `program_code` + `faculty_code` (bổ sung) | Hỏi ngành X → lọc chunk đúng ngành trước khi tìm |
| Giới thiệu Khoa (38) | `faculty_code` | Hỏi Trường Y → lọc chunk đúng Khoa |
| Đề án, bài tuyển sinh | `year` | Lọc đúng năm |
| Quy định ngoại ngữ | `year` + `cohort` | Phân biệt K71 / K70 |

**Quy tắc trả lời:** câu hỏi có số (điểm, học phí, chỉ tiêu, quy đổi) → **số từ SQL**, RAG chỉ để giải thích và trích dẫn văn bản. **Vì sao:** v1 (mục C) đã phát hiện số điểm chuẩn xuất hiện cả trong văn kể RAG; lấy số từ RAG là đi đường tránh AC1 và không có gì bảo đảm văn kể đủ.

Luồng một câu hỏi, ví dụ "IT1 tính điểm thế nào, năm ngoái bao nhiêu điểm?":

1. `entity_aliases`: "IT1" → `program_code = IT1`
2. SQL: `program_combinations` ⨝ `combinations` ⨝ `scoring_formulas` → tổ hợp + môn chính + công thức
3. SQL: `admission_scores` where `year = 2025` → điểm theo phương thức / nhóm tổ hợp
4. RAG: lọc `document_type = tin_tuyen_sinh`, `year = 2025` → đoạn "Hướng dẫn cách xác định Điểm Xét" để trích dẫn
5. Trả lời: số từ bước 2–3, citation từ bước 4 + `source_url` của dòng SQL

---

## 4. Kiểm tra: `scripts/validate_links.py` (mới)

| Luật | Mức | Bắt được |
|---|---|---|
| Mọi khoá ngoại tồn tại ở bảng danh mục | Lỗi | mã mồ côi |
| Mọi ngành có đúng 1 `faculty_code` hợp lệ | Lỗi | L1 (TE1, TROY-IT) |
| `program_name` chỉ xuất hiện ở bảng `programs` | Lỗi | L2 tái phát |
| Mỗi (ngành, năm) trong `program_years` có đủ: chỉ tiêu, phương thức, điểm chuẩn | Cảnh báo | dữ liệu thủng theo năm |
| Ngành có phương thức X thì có tổ hợp của phương thức X | Cảnh báo | L8 (FL + ĐGTD) |
| `method_code` con có `parent_method` tồn tại | Lỗi | L3 |
| Chứng chỉ trong 3 bảng đều có `cert_code` | Lỗi | L6 |
| Mọi ngành, Khoa đều có ít nhất 1 alias | Cảnh báo | L7 |
| Mọi ngành trong năm có mặt trong bảng cầu học phí / chuẩn đầu ra | Cảnh báo | L5 thiếu gán |

Như `validate_aliases.py`: **thử ngược bằng lỗi cố ý** (đổi mã Khoa của 1 ngành, xoá 1 alias…) để chắc validator bắt được.

---

## 5. Thứ tự thực hiện

| Bước | Việc | Ước lượng | Vì sao ở vị trí này |
|---|---|---|---|
| 1 | Tạo `faculties`; gán `faculty_code` cho 68 ngành từ `faculty_name` của danh mục; **sửa TE1 → SME, TROY-IT → FAMI** | ~0,5h | Mọi thứ phía sau (chunk ngành, alias Khoa) cần mã Khoa đúng |
| 2 | Tạo `programs` + `program_years`; chọn tên chuẩn; đưa các tên khác vào `entity_aliases` | ~1h | Gỡ L2 trước khi bỏ `program_name` khỏi bảng số liệu |
| 3 | `admission_methods` + `certificates`; thêm cột mã vào 3 bảng chứng chỉ | ~1h | Việc cơ học, rủi ro thấp |
| 4 | Thêm dòng K00 cho FL1–FL4 (căn cứ: bảng phương thức + điểm chuẩn TSA) | ~10 phút | Sửa dữ liệu, ghi `verification_status = rule_derived` |
| 5 | Alias Trường/Khoa (~40 dòng: tên đầy đủ, tên cũ "Viện…", viết tắt SoICT, SEEE…) | ~1h | Cần có trước khi test câu hỏi theo Khoa |
| 6 | Bảng cầu học phí tín chỉ + chuẩn đầu ra ngoại ngữ (làm tay) | ~2h | Phần tốn công nhất, làm khi khung đã ổn |
| 7 | `scripts/build_db.py`: nạp toàn bộ vào SQLite (kiểm thử) theo schema mục 2 | ~1,5h | Chạy thật mọi phép nối trước khi lên PostgreSQL |
| 8 | `validate_links.py` + thử ngược | ~1,5h | Chốt trước khi sang metadata bước 3 |

**Vì sao nạp SQLite trước dù PRD chọn PostgreSQL:** SQLite không cần dựng server, chạy được trong script kiểm tra và bộ test; cú pháp JOIN hai bên như nhau. Khi schema ổn thì chuyển sang PostgreSQL chỉ là đổi chuỗi kết nối.
**Vì sao `data/processed/*.csv` vẫn là bản gốc:** các script bóc dữ liệu đang ghi vào đó; DB là sản phẩm **sinh ra** từ CSV (`build_db.py` chạy lại được), nên sửa dữ liệu chỉ ở một chỗ.

---

## 6. Cần anh quyết

1. **Tên chuẩn của ngành** lấy theo đề án 2026 (khuyến nghị) hay theo trang giới thiệu ngành?
2. **EM4, TROY-BA** (chỉ tuyển 2025): giữ trong `programs` như ngành đã dừng tuyển (khuyến nghị — để trả lời đúng "năm nay không tuyển") hay bỏ?
3. **Bảng cầu học phí tín chỉ 2024–2025** có làm không? Học phí 2026 theo ngành đã có ở `tuition_2026`; bảng tín chỉ chỉ cần nếu anh muốn trả lời "bao nhiêu tiền một tín chỉ" (số năm 2024–2025, phải kèm ghi chú năm).
