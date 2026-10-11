# PLAN — T7 `rag_search`: retrieval văn bản (v2 — bản thực hiện)

**Ngày:** 2026-10-11 · **Trạng thái:** anh đã duyệt (mục 1, kể cả R-16) — **đã thực hiện 2026-10-11**, xem mục 7 · Thay cho `PLAN - T7 retrieval (v1).md` (giữ lại làm lịch sử: thử nghiệm, đính chính Q18, câu trả lời của anh) · Bước 7 (cuối) của `PLAN - Tools (v1).md` mục 9

Mỗi quyết định có dòng **Vì sao**. Số liệu thử nghiệm: mục 2 của v1 (đo thật 2026-10-11).

**Phạm vi:** T7 chỉ **tìm** đoạn văn bản liên quan và trả kèm thông tin trích dẫn. Không gọi LLM sinh chữ; chỉ gọi API embedding. Prompt và viết câu trả lời là Tuần 4.

---

## 1. Anh đã chốt (2026-10-11)

| # | Điểm | Anh chốt | Ảnh hưởng tới plan |
|---|---|---|---|
| 1 | Bảng ca kỳ vọng | **Duyệt** 15 ca | Mục 5 giữ nguyên; thêm 1 ca cho dữ liệu mới ở bước 0 (R-16, đánh dấu chờ duyệt) |
| 2 | Ngành mơ hồ trong RAG (R7) | **Hỏi lại** | T7 trả `ambiguous` như T1/T3 |
| 3 | Ngưỡng "không đủ tin cậy" | **Duyệt 0,40** (tạm, chốt chính thức ở Tuần 4) | R6 |
| 4 | Sửa cột tham chiếu bộ 120 câu | **Tôi sửa** | **Đã làm 2026-10-11:** Q10, Q12, Q20 thêm `trang_tuyen_sinh`; Q18 thêm `qui-dinh-ve-xttn-nam-2026-ky` (4 dòng, giữ CRLF) |
| 5 | Chunk "Các mức học phí khác" 2025–2026, 2026–2027 | Thông tin đã có trong hai PDF quyết định học phí | **Bước 0**: chép mục "5) Các mức học phí khác" của hai PDF thành 2 chunk mới |

---

## 2. Thiết kế (giữ từ v1, đã sửa theo đính chính)

### 2.1 Đầu vào / đầu ra

```python
class RagSearchInput(BaseModel):
    query: str
    programs: list[str] = []            # 0–3 ngành -> lọc program_code; mơ hồ -> hỏi lại
    faculties: list[str] = []           # 0–3 Trường/Khoa -> lọc faculty_code
    years: list[int] = []               # nêu năm -> tài liệu nhiều năm chỉ lấy đúng năm đó
    cohort: str | None = None           # "K71", "K70", "khoá 2026"... -> lọc quy định ngoại ngữ
    document_types: list[DocType] = []  # tuỳ chọn
    top_k: int = 5                      # tối đa 10

class RetrievedChunk(BaseModel):        # đủ trường trích dẫn + citation dựng sẵn (PRD 12)
    rank; chunk_id; document_title; document_type; document_no; year; heading
    chuong; dieu_no; khoan_no; muc_no; page_no; source_url; verification_status
    cohort; program_code; faculty_code; is_latest; versioned
    dense_score: float                  # cosine — dùng cho ngưỡng, KHÔNG dùng điểm RRF
    text: str; citation: Source

class RagSearchData(BaseModel):
    chunks; top_dense_score; low_confidence: bool
    phrases_used: list[str]             # cụm từ đã dùng để lọc, kể cả cụm đổi từ cách gọi tương đương
    cohorts_found: list[str]            # có cả <=K70 và K71+ mà chưa biết khoá -> cần hỏi lại
    notes: list[str]
```

### 2.2 Cách tìm (các nhánh gộp RRF)

| Nhánh | Lọc | Khi nào |
|---|---|---|
| A — mọi bản | các lọc cứng (năm/khoá/loại tài liệu nếu nêu) | luôn có; cũng là nơi lấy `dense_score` |
| B — bản mới nhất | A + (`is_latest` hoặc `versioned = false`) | khi **không** nêu năm |
| C — cụm từ | A (+ bản mới nếu không nêu năm) + `MatchText` | khi câu hỏi có cụm từ chuyên ngành hoặc cách gọi có trong từ điển tương đương |
| Ngành | `program_code = X`, top-3 **mỗi ngành**, gộp nối | khi có ngành |
| Trường/Khoa | RRF (lọc Trường) + (lọc Trường và `gioi_thieu_don_vi`) | khi có Trường/Khoa |

### 2.3 Quyết định

| # | Quyết định | Vì sao |
|---|---|---|
| R1 | Ngành → tìm riêng từng ngành; Trường/Khoa → ưu tiên chunk giới thiệu đơn vị | Q80: hai ngành đều có chunk. Q106: `donvi::smse-1` lên #1 |
| R2 | **Ưu tiên** bản mới nhất bằng nhánh B, **không lọc cứng**; nêu năm thì lọc đúng năm | Có thông tin chỉ nằm ở bản cũ: lệ phí tuyển sinh chỉ có trong `dean2024::m1.9`. (v1 từng lấy Q18 làm ví dụ — sai, đã đính chính) |
| R3 | Nhánh C dùng danh sách cụm từ chuyên ngành **và từ điển cách gọi tương đương** (cách người dùng nói → cách văn bản viết); không nêu năm thì nhánh C chỉ tìm bản mới | Q10 ("môn chính") và Q18 ("học bạ" → "TBC") đều cải thiện trong thử nghiệm. Nhánh C chỉ cộng phiếu, không loại chunk |
| R4 | Mỗi chunk có `citation` dựng sẵn từ metadata | PRD 12, AC4 |
| R5 | Có cả K70 lẫn K71 mà chưa biết khoá → `cohorts_found` + ghi chú "cần hỏi khoá"; nêu khoá → lọc `cohort` (giữ chunk không gắn khoá) | PRD 3.1.C |
| R6 | `top_dense_score < 0,40` → `low_confidence`, `status = not_found`, `LOW_RETRIEVAL_CONFIDENCE`; vẫn trả chunk để gỡ lỗi | **Anh duyệt.** Câu "trường khác" (0,645) ngưỡng không bắt được — việc của Router |
| R7 | Ngành mơ hồ → `ambiguous`, không tìm | **Anh duyệt: hỏi lại** |
| R8 | Hai lớp: `rag/retriever.py` (Qdrant + embedding) và `tools/rag_tool.py` (T7) | Retriever dùng lại cho script đo |
| R9 | Async; ghim `qdrant-client==1.19.0`, `openai==1.109.1` như `requirements-ingest.txt` | Lệch phiên bản client/server Qdrant có thể lỗi API |

**Từ điển cách gọi tương đương (khởi điểm, mở rộng khi đo):**

| Người dùng nói | Văn bản viết |
|---|---|
| học bạ, điểm học bạ | TBC, điểm trung bình chung |
| điểm cộng (chứng chỉ) | điểm thưởng |
| rớt môn, trượt môn | điểm F, học lại |
| đình chỉ, đuổi học | buộc thôi học |
| hệ số 2 | môn chính |

---

## 3. Bước 0 — bổ sung 2 chunk "Các mức học phí khác" (dữ liệu, trước khi code)

| Việc | Chi tiết |
|---|---|
| Nguồn | QĐ 10232/QĐ-ĐHBK (2025–2026), Phụ lục I mục 5, trang PDF 4; QĐ 12006/QĐ-ĐHBK (2026–2027), Phụ lục I mục 5, trang PDF 5. Link như trong `tuition_credit.csv` |
| Cách lấy chữ | Lấy từ lớp chữ PDF (có sẵn), đối chiếu ảnh trang |
| Nội dung | Học lại / cải thiện / ngoài khung / ngành 2 tính như mức thường; **học kỳ hè ×1,5** (trừ một số học phần, KSCS); sinh viên nước ngoài tự túc ×1,5; KSCS tính như CTĐT chuẩn tương ứng; lớp học lại ít sinh viên: 10–<20 SV hệ số 1,5, <10 SV hệ số 2,0 |
| Tệp | `data/raw/tuition_2025/transcript/*.md`, `data/raw/tuition_2026/transcript/*.md` (cùng khuôn với `data/raw/tuition/`) |
| Cấu hình | `scan_md_to_rag.py` thêm 2 nguồn; `normalize_chunks.py` thêm slug `hocphi2025`, `hocphi2026`, `kind = pdf_text`, `verification_status = pdf_text`, trang theo Điều |
| Phiên bản | Tên "Quy định học phí 2025-2026 / 2026-2027 - các mức học phí khác" cùng họ với bản 2024 → `versioned`; bản **2026–2027 thành `is_latest`**; chunk 2024 chuyển `is_latest = false` |
| Nhúng | Thêm chế độ `--add-missing` cho `embed_chunks.py`: chỉ nhúng chunk chưa có trong Qdrant, rồi **cập nhật payload** `is_latest`/`versioned` cho chunk cũ bị đổi cờ. 641 → **643** điểm |
| Kiểm | `validate_metadata` 0 lỗi; tự kiểm của `embed_chunks` (số điểm = 643) |

**Vì sao `--add-missing` thay vì `--recreate`:** anh đã duyệt "chỉ nhúng 2 chunk mới". Nhúng lại cả 641 chunk thì vector cũ đổi nhẹ (embedding không hoàn toàn tất định, cosine 0,9966–1,0), làm số đo hit@5 lần này không so được với lần trước. Phải cập nhật cờ của chunk 2024, nếu không nó vẫn mang `is_latest = true` và được nhánh B ưu tiên ngang bản 2026.

---

## 4. Bước thực hiện

| Bước | Việc | Ước lượng | Xong khi |
|---|---|---|---|
| 0 | 2 chunk học phí khác + `--add-missing` (mục 3) | ~1 giờ | Qdrant 643 điểm; `hocphi2026::d5` là `is_latest` |
| 1 | `rag/phrases.py` (cụm từ + từ điển tương đương), `rag/retriever.py` (nhánh A/B/C, ngành, Trường, citation, cosine); test không mạng | ~2 giờ | Test tách cụm, dựng bộ lọc, dựng citation, đọc khoá xanh |
| 2 | `schemas/rag.py`, `tools/rag_tool.py` (T7), `ErrorCode.LOW_RETRIEVAL_CONFIDENCE`; 16 ca marker `rag` | ~1,5 giờ | 16 ca mục 5 xanh |
| 3 | `scripts/eval_retrieval.py`: bộ 120 câu qua retriever backend → hit@5 + phân bố `top_dense_score` vào `docs/ghi_chu/` | ~1 giờ | hit@5 ≥ 81%; có bảng phân bố điểm |
| 4 | Ghi "Đã thực hiện"; cập nhật `cautrucduan.md`, `memory.md`, `PLAN - Tools` | ~20 phút | |

**Tổng: khoảng 6 giờ.**

---

## 5. Ca kỳ vọng (đã duyệt 2026-10-11) + 1 ca mới

| # | Đầu vào | Kỳ vọng trong top-5 |
|---|---|---|
| R-01 | Q10 "hệ số 2 môn chính … THPT" | Có `ts::diem-chuan-2026-3` **và** `dean2026::m3-1`; `phrases_used` có "môn chính" |
| R-02 | Q12 "công thức ĐGTD có cộng điểm ưu tiên" | Có `ts::diem-chuan-2026-4` |
| R-03 | Q20 "điểm ưu tiên trong phương thức ĐGTD" | `ts::diem-chuan-2026-4` ở #1 |
| R-04 | Q18 "điều kiện học bạ tối thiểu" | Có ít nhất 1 trong `xttn2026::d3k1`, `xttn2026::d4k1`, `dean2026::m1.2`, `dean2026::m1.3`; `phrases_used` có "TBC" |
| R-04b | "Lệ phí đăng ký dự thi đánh giá tư duy là bao nhiêu" | Có `dean2024::m1.9` |
| R-05 | Q18 + `years=[2026]` | Không có chunk đề án 2024, 2025 |
| R-06 | Q80 + `programs=["IT1","IT2"]` | Có chunk `IT1` **và** chunk `IT2` |
| R-07 | Q106 + `faculties=["Trường Vật liệu"]` | `donvi::smse-1` ở #1 |
| R-08 | Q84 (không nêu khoá) | Có `nnk70::d5` và `nnk71::d5`; `cohorts_found = ["<=K70","K71+"]` |
| R-09 | Q84 + `cohort="K71"` | Có `nnk71::d5`, không có chunk `<=K70` |
| R-10 | "Thời tiết Hà Nội hôm nay" | `low_confidence = true`, `LOW_RETRIEVAL_CONFIDENCE` |
| R-11 | "Điểm chuẩn ĐHQGHN 2025" | `low_confidence = false` (ghi lại để nhắc Router phải chặn) |
| R-12 | "Ngành Kỹ thuật Ô tô học những gì" + `programs=["Kỹ thuật Ô tô"]` | `ambiguous` TE1 / TE-E2 |
| R-13 | Mọi chunk trả về | Có `source_url`; chunk nguồn PDF có `page_no`; `citation.title` không rỗng |
| R-14 | Đo bộ 120 câu (mức tài liệu) | hit@5 ≥ 81%; Q10, Q12, Q18, Q20 trúng |
| **R-16** *(anh duyệt 2026-10-11)* | "Học phí học kỳ hè tính thế nào" | Có `hocphi2026::d5` (bản mới nhất), xếp trên `hocphi2024::d5` nếu cả hai cùng có |

---

## 6. File đụng tới

```
data/raw/tuition_2025/transcript/*.md, data/raw/tuition_2026/transcript/*.md   mới (bước 0)
scripts/scan_md_to_rag.py, scripts/normalize_chunks.py                          + 2 nguồn học phí
scripts/embed_chunks.py                                                         + --add-missing
backend/app/rag/phrases.py, backend/app/rag/retriever.py                        mới
backend/app/schemas/rag.py, backend/app/tools/rag_tool.py                       mới
backend/app/schemas/common.py                                                   + LOW_RETRIEVAL_CONFIDENCE
backend/requirements.txt                                                        + qdrant-client, openai
backend/tests/test_rag_unit.py, backend/tests/test_rag_search.py                mới
scripts/eval_retrieval.py                                                       mới
backend/tests/eval/120_question_check_data.md                                   ĐÃ SỬA (Q10, Q12, Q18, Q20)
```

---

## 7. Đã thực hiện (2026-10-11)

### Kết quả

| Bước | Kết quả |
|---|---|
| 0 | 2 chunk mới `hocphi2025::d5` (QĐ 10232, trang 4-5), `hocphi2026::d5` (QĐ 12006, trang 5), `verification_status = pdf_text`; nguồn `data/raw/qd_hoc_phi_2025_2026/`, `qd_hoc_phi_2026_2027/`. `embed_chunks.py --add-missing`: nhúng **đúng 2 chunk**, `hocphi2024::d5` chuyển `is_latest = false`, không chunk cũ nào đổi nội dung; Qdrant **643 điểm** |
| 1 | `backend/app/rag/phrases.py` (19 cụm từ, 8 cách gọi tương đương, mã tổ hợp, "Điều N"), `backend/app/rag/retriever.py`; `tests/test_rag_unit.py` 11 test không mạng |
| 2 | `schemas/rag.py`, `tools/rag_tool.py`, `ErrorCode.LOW_RETRIEVAL_CONFIDENCE`; `tests/test_rag_search.py` **15/15** (16 ca mục 5; R-14 đo bằng script) |
| 3 | `scripts/eval_retrieval.py` → `docs/ghi_chu/2026-10-11 - Ket qua retrieval T7.md`. 59 câu (bỏ câu đã biết thiếu dữ liệu): **dense thuần 85% → T7 88%**; trúng thêm Q10, Q18; **không câu nào trượt thêm**. Q12, Q20 trúng ở cả hai cách nhờ cột tham chiếu đã sửa |
| Tổng | `pytest backend` **281 passed** (mặc định bỏ qua ca `rag`); `pytest -m rag` 15 passed; `validate_metadata` 0/0, `validate_links` 0 lỗi |

**Phân bố điểm (căn cứ ngưỡng R6):** câu hợp lệ thấp nhất 0,460; câu lạc đề 0,279–0,380 → ngưỡng tạm **0,40 tách được**. Câu về **trường khác** (ĐHQGHN 0,645; NEU 0,524) **không** bị ngưỡng chặn — đúng như dự đoán, việc của Router (Tuần 4).

### Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| Tên nguồn 2 chunk mới | `qd_hoc_phi_2025_2026`, `qd_hoc_phi_2026_2027` (bản đầu đặt `tuition_2025`, `tuition_2026`) | Lần đo đầu bắt được: tên `tuition_2026` **trùng** với `tuition_2026.csv` mà bộ 120 câu ghi làm tham chiếu cho câu học phí → script coi Q46, Q47, Q58 là câu RAG, ra "Q46 trúng thêm" **giả**. Đổi tên xong số câu về đúng 77; `chunk_id` không đổi nên không phải nhúng lại |
| Bỏ "hệ số" đơn lẻ khỏi cụm từ | Chỉ giữ "hệ số 2" → "môn chính" trong từ điển tương đương | "hệ số" có trong quy định XTTN (hệ số quy đổi chứng chỉ) — chính là lý do Q10 lệch tài liệu trước đây |
| Nhiều cụm từ cùng lúc | Nhánh C dùng **hoặc** giữa các cụm (`should`) | `MatchText` đòi đủ mọi từ của một cụm; ghép tất cả vào một điều kiện thì gần như không chunk nào khớp |
| `dense_score` | Truy vấn lại cosine cho đúng các chunk đã chọn (`HasIdCondition`) | Điểm RRF chỉ là thứ hạng (R6) |
| Ngành | Tìm riêng từng ngành, mỗi ngành `ceil(top_k / số ngành)` (tối thiểu 2), xen kẽ; không trộn kết quả chung | Câu hỏi gắn ngành là câu về ngành; trộn chunk chung dễ đẩy chunk của một ngành ra ngoài |
| `page_no` | Kiểu chuỗi | Có khoảng trang ("4-5") |
| Ca `rag` | Mặc định bỏ qua (cấu hình `addopts` trong `backend/pyproject.toml`), chạy tay `pytest -m rag` | Mỗi lần chạy gọi API embedding (tốn phí nhỏ); `pytest backend` hằng ngày không tốn tiền |
| `Retriever.search(spec, vec=None)` | Nhận vector có sẵn | Script đo dùng **một** lần embedding cho cả cách cũ và mới → so sánh công bằng, đỡ phí |
| `localhost` → `127.0.0.1` trong Retriever | Đổi tự động | Cùng bẫy IPv6 đã gặp với Postgres |

### Câu vẫn trượt — ghi cho Tuần 4

| Câu | Vì sao trượt | Ai xử lý |
|---|---|---|
| Q106 | Câu không gắn Trường nên chạy nhánh chung | Router truyền `faculties=["Trường Vật liệu"]` → ca R-07 đã cho ra đúng #1 |
| Q73 | Ghi chú kiểm 120 câu (2026-09-26) đã nói nguồn nên là `nganh_dao_tao`; top-1 đúng là `nganh_dao_tao` | Sửa cột tham chiếu (nếu anh muốn) |
| Q39, Q41 | Số liệu (thang điểm FL2, điểm thưởng ĐGTD) do T3/T5 trả, không cần RAG | Router gọi T3/T5 |
| Q24, Q61, Q74 | Lẫn đề án 2026 với quy định XTTN / quy chế đào tạo (tài liệu na ná nhau) | Đo lại khi có Router viết lại câu hỏi |
