# PLAN — T7 `rag_search`: retrieval văn bản (v1)

**Ngày:** 2026-10-11 · **Trạng thái:** anh đã trả lời mục 10 (2026-10-11) — **đã thay bằng `PLAN - T7 retrieval (v2).md`**; bản này giữ làm lịch sử · Bước 7 (cuối) của `PLAN - Tools (v1).md` mục 9 · Dùng lại: Qdrant `hust_rag_2026_1` (641 chunk, `text-embedding-3-large`), `ToolResult`, Entity Resolution · Đi trước: `PLAN - Embedding (v1).md` (mục 6, 7, "Đã thực hiện")

Mỗi quyết định có dòng **Vì sao**. Các kết quả thử ở mục 2 là số đo thật ngày 2026-10-11 (script nháp trong scratchpad, không phải code sản phẩm).

**Phạm vi:** T7 chỉ **tìm** đoạn văn bản liên quan và trả kèm thông tin trích dẫn. **Không gọi LLM sinh chữ**; chỉ gọi API embedding để đổi câu hỏi thành vector. Prompt cho Router/Synthesizer và việc viết câu trả lời là Tuần 4.

---

## 1. Hiện trạng

| Thành phần | Có |
|---|---|
| Kho vector | Qdrant `hust_rag_2026_1`: 641 chunk, vector `dense` 3072 chiều |
| Payload có chỉ mục | `year`, `document_type`, `program_code` (152 chunk), `faculty_code` (190), `cohort` (14: 7 `<=K70`, 7 `K71+`), `dieu_no`, `chunk_id`, `is_latest`, `versioned`; full-text trên `text` (lọc `MatchText`) |
| Tài liệu nhiều năm (`versioned`) | Đề án 2024/2025/2026 và bài điểm chuẩn 2024/2025/2026; **chỉ bản 2026** mang `is_latest = true` |
| Trường để trích dẫn | `document_title`, `heading`, `chuong`, `dieu_no`, `khoan_no`, `muc_no`, `page_no`, `source_url`, `verification_status` |
| Đo lần trước (2026-10-04) | Dense thuần, top-5, mức tài liệu: **hit@5 = 81%** (48/59 câu, bỏ câu đã biết thiếu dữ liệu). 11 câu trượt |

## 2. Thử nghiệm 2026-10-11 — điều rút ra

| Câu | Cách | Kết quả | Rút ra |
|---|---|---|---|
| Q10 (môn chính hệ số 2) | dense + chỉ bản mới | top-5 toàn quy định XTTN, bài điểm chuẩn ở #5 | — |
| Q10 | **+ nhánh lọc chữ "môn chính", gộp RRF** | **#1 `ts::diem-chuan-2026-3`** (công thức môn chính), #3 `dean2026::m3-1` | Nhánh lọc cụm từ chuyên ngành có tác dụng (R3) |
| Q18 (điều kiện học bạ) | dense + chỉ bản mới nhất | Không ra chunk điều kiện nào. **Đính chính 2026-10-11:** bản 2026 **có** điều kiện này (`dean2026::m1.2`, `m1.3`, `xttn2026::d3k1`, `d4k1`: "điểm TBC các môn văn hóa từng năm học lớp 10, 11, 12 đạt từ 8,00"); trượt vì **khác cách gọi** — câu hỏi nói "học bạ", văn bản viết "điểm trung bình chung (TBC)" | Cần từ điển **cách gọi tương đương** cho nhánh cụm từ (R3) |
| Q18 | RRF (bản mới, mọi bản, **cụm "TBC" trong bản mới**) | `xttn2026::d3k1` lên #2, `d4k1` #5 | Nhánh cụm từ nên áp cả lọc "bản mới" khi không nêu năm |
| Lệ phí tuyển sinh | tìm chữ "lệ phí" trong đề án / bài tuyển sinh | **Chỉ** có ở `dean2024::m1.9`, `m2.9` | Có thông tin chỉ nằm ở bản cũ → **không được lọc cứng "chỉ bản mới"** (R2) |
| Q12, Q20 (công thức ĐGTD, điểm ưu tiên) | RRF bản mới + mọi bản | `ts::diem-chuan-2026-4` lên #1 (Q20) / #4 (Q12) — đúng chunk có công thức ĐGTD 2026 | Bộ 120 câu chỉ ghi nguồn đề án 2026 nên lần chấm cũ báo trượt **oan** (giống Q10) |
| Q80 (so sánh IT1 / IT2) | lọc riêng từng ngành, top-3 mỗi ngành | IT1: `nganh::it1-1`, `-2`; IT2: `nganh::it2-1`, `-2` | Tìm riêng từng ngành rồi gộp (R1) |
| Q84 (chuẩn đầu ra tiếng Anh) | dense | #1 `nnk70::d5` (K70), #2 `nnk71::d5` (K71) | Ra cả hai khoá → phải báo để hỏi lại khoá (R5) |
| Q106 (Trường Vật liệu, việc làm) | lọc `faculty_code = SMSE` | toàn chunk ngành MS1, MS-E3 | — |
| Q106 | **RRF (lọc Trường) + (lọc Trường và loại "giới thiệu đơn vị")** | **#1 `donvi::smse-1`** | Hỏi về Trường thì ưu tiên chunk giới thiệu Trường (R1) |
| Ngoài phạm vi | "Điểm chuẩn ĐHQGHN 2025" | cosine **0,645** — cao hơn nhiều câu hợp lệ (0,48–0,62) | **Ngưỡng điểm không bắt được** câu trường khác; phải để Router (OTHER_UNIVERSITY) lo (R6) |
| Ngoài phạm vi | "Thời tiết Hà Nội hôm nay" | cosine **0,380** | Ngưỡng bắt được câu lạc đề hẳn |

---

## 3. Đầu vào

```python
class RagSearchInput(BaseModel):
    query: str                          # câu hỏi (Router có thể viết lại gọn, Tuần 4)
    programs: list[str] = []            # 0–3 ngành (cụm người dùng gõ) -> lọc program_code
    faculties: list[str] = []           # 0–3 Trường/Khoa -> lọc faculty_code
    years: list[int] = []               # nêu năm -> chỉ lấy tài liệu nhiều năm đúng năm đó
    cohort: str | None = None           # "K71", "K70", "khoá 2026"... -> lọc quy định ngoại ngữ
    document_types: list[DocType] = []  # tuỳ chọn: so_tay_sinh_vien, quy_che_dao_tao, de_an_tuyen_sinh...
    top_k: int = 5                      # tối đa 10
```

## 4. Đầu ra

```python
class RetrievedChunk(BaseModel):
    rank: int; chunk_id: str
    document_title: str; document_type: str; document_no: str | None; year: int
    heading: str; chuong: str | None; dieu_no: str | None; khoan_no: str | None; muc_no: str | None
    page_no: int | None; source_url: str; verification_status: str
    cohort: str | None; program_code: str | None; faculty_code: str | None
    is_latest: bool; versioned: bool
    dense_score: float                   # cosine với câu hỏi (cho ngưỡng, R6)
    text: str
    citation: Source                     # dựng sẵn: "Tên tài liệu — Điều/mục — Trang N" + source_url (PRD 12)

class RagSearchData(BaseModel):
    chunks: list[RetrievedChunk]
    top_dense_score: float
    low_confidence: bool                 # top_dense_score < ngưỡng (R6)
    phrases_used: list[str]              # cụm từ chuyên ngành đã lọc (R3)
    cohorts_found: list[str]             # có cả <=K70 và K71+ mà chưa biết khoá -> cần hỏi lại (R5)
    notes: list[str]
```

Ví dụ trích dẫn dựng sẵn (PRD 12):
- Văn bản pháp quy: *"Quy chế đào tạo trình độ đại học — Điều 15 — Trang 18"* + link
- Sổ tay: *"Sổ tay sinh viên 2026 — <tên mục> — Trang 30"* + link
- Trang web: *"Công bố điểm chuẩn đại học 2026 — <tên mục>"* + link (không có số trang)

---

## 5. Quá trình xử lý và quyết định

**Quá trình:**
1. Phân giải `programs`, `faculties` bằng Entity Resolution (như T1–T6).
2. Đổi `query` thành vector (một lần gọi embedding).
3. Dựng các **nhánh tìm** (Qdrant `Prefetch`), gộp bằng **RRF**:
   - nhánh "mọi bản" (dense, chỉ áp các lọc cứng: năm nếu nêu, khoá nếu nêu, loại tài liệu nếu có);
   - nhánh "bản mới nhất" (thêm `is_latest = true` hoặc `versioned = false`) — chỉ khi không nêu năm (R2);
   - nhánh cụm từ (thêm `MatchText`) — khi câu hỏi có cụm từ chuyên ngành (R3);
   - có ngành: **mỗi ngành một lượt tìm riêng** (top-3/ngành) rồi gộp; có Trường/Khoa: RRF (lọc Trường) + (lọc Trường và `gioi_thieu_don_vi`) (R1).
4. Lấy `dense_score` (cosine) cho từng chunk từ nhánh "mọi bản"; `top_dense_score` để so ngưỡng (R6).
5. Dựng `citation` cho từng chunk; kiểm khoá (R5).

| # | Quyết định | Vì sao |
|---|---|---|
| R1 | Lọc theo thực thể: **ngành → tìm riêng từng ngành** (top-3/ngành); **Trường/Khoa → ưu tiên chunk giới thiệu đơn vị** | Q80: tìm chung thì ngành nhiều chunk khớp hơn chiếm hết chỗ. Q106: chỉ lọc Trường thì toàn chunk ngành, chunk giới thiệu Trường (nơi có thông tin chung) bị đẩy xuống |
| R2 | **Ưu tiên** bản mới nhất bằng nhánh riêng gộp RRF, **không lọc cứng**; nêu năm thì lọc đúng năm | Có thông tin **chỉ** nằm ở bản cũ: lệ phí tuyển sinh chỉ có trong đề án 2024 (`dean2024::m1.9`); lọc cứng thì câu "lệ phí thi ĐGTD" mất nguồn. Gộp RRF giữ bản mới lên trên mà vẫn còn bản cũ. `is_latest`/`versioned` đã có sẵn trong payload, không phải nhúng lại. (Bản đầu plan lấy Q18 làm ví dụ — **sai**, xem mục 2) |
| R3 | Nhánh lọc **cụm từ chuyên ngành** cố định (môn chính, hệ số, điểm sàn, điểm ưu tiên, điểm thưởng, cảnh báo học tập, buộc thôi học, học bổng, học kỳ hè, học lại, bảo lưu, chuẩn đầu ra, …) + mã tổ hợp (`[A-D]\d\d`, `K0\d`) + "Điều N". Kèm **từ điển cách gọi tương đương**: cách người dùng nói → cách văn bản viết (vd "học bạ" → "TBC" / "điểm trung bình chung"). Không nêu năm thì nhánh này cũng chỉ tìm trong bản mới | Q10 (lọc "môn chính") và Q18 (lọc "TBC") đều được cải thiện trong thử nghiệm. Nhánh này chỉ **cộng phiếu** trong RRF, không loại chunk khác, nên cụm từ không có trong tài liệu cũng không làm mất kết quả |
| R4 | Kết quả trả **đủ trường trích dẫn** và `citation` dựng sẵn từ metadata | PRD 12: citation lấy từ metadata, LLM không được tự tạo; AC4 cần Tên tài liệu + Vị trí + Đường dẫn |
| R5 | Có chunk quy định ngoại ngữ của **cả** K70 lẫn K71 mà người dùng chưa nêu khoá → `cohorts_found = ["<=K70", "K71+"]` + ghi chú "cần hỏi khoá"; nêu khoá thì lọc `cohort` (giữ cả chunk không gắn khoá) | PRD 3.1.C: chuẩn đầu ra chưa rõ khoá thì phải hỏi lại. Q84 ra cả `nnk70::d5` và `nnk71::d5` |
| R6 | `low_confidence` khi `top_dense_score < 0,40` (**ngưỡng tạm**); khi đó `status = not_found`, mã lỗi `LOW_RETRIEVAL_CONFIDENCE` (PRD 24), vẫn trả chunk để gỡ lỗi. Ghi lại phân bố điểm của cả bộ 120 câu; ngưỡng chính thức chốt ở Tuần 4 | PRD 13.1: không dùng cosine như xác suất; ngưỡng đặt từ tập đo. Đo được: câu hợp lệ 0,48–0,62, câu lạc đề 0,38. **Câu "trường khác" (0,645) ngưỡng không bắt được** — đó là việc của Router |
| R7 | Ngành mơ hồ → **hỏi lại** như T1/T3 (**chờ anh duyệt**, mục 10) | Phần giới thiệu ngành chuẩn và tiên tiến khác nhau (ngôn ngữ, học phí, đối tác). Trả lẫn hai ngành dễ làm bot gán mô tả ngành này cho ngành kia |
| R8 | Code tách 2 lớp: `backend/app/rag/retriever.py` (Qdrant + embedding, không biết gì về ngành/Trường) và `backend/app/tools/rag_tool.py` (T7: phân giải thực thể, gọi retriever, đóng `ToolResult`) | `retriever.py` dùng lại được cho đo lường và các nơi khác; T7 giữ cùng khuôn với T1–T6 |
| R9 | Client Qdrant và OpenAI dạng **async**; thư viện ghim cùng phiên bản với `requirements-ingest.txt` (`qdrant-client==1.19.0`, `openai==1.109.1`) | Thống nhất với pool Postgres async (D8 plan Postgres). Lệch phiên bản client/server Qdrant có thể báo lỗi API |

---

## 6. Ca kỳ vọng — **anh duyệt từng dòng**

Mức **chunk** (chính xác hơn mức tài liệu của bộ 120 câu). Các dòng có dấu ✓ là kết quả đã thấy trong thử nghiệm 2026-10-11.

| # | Đầu vào | Kỳ vọng trong top-5 |
|---|---|---|
| R-01 | Q10 "hệ số 2 môn chính … THPT" | Có `ts::diem-chuan-2026-3` **và** `dean2026::m3-1`; `phrases_used` có "môn chính" ✓ |
| R-02 | Q12 "công thức ĐGTD có cộng điểm ưu tiên" | Có `ts::diem-chuan-2026-4` ✓ |
| R-03 | Q20 "điểm ưu tiên trong phương thức ĐGTD" | `ts::diem-chuan-2026-4` ở #1 ✓ |
| R-04 | Q18 "điều kiện học bạ tối thiểu" | Có ít nhất 1 trong `xttn2026::d3k1`, `xttn2026::d4k1`, `dean2026::m1.2`, `dean2026::m1.3`; `phrases_used` có "TBC" (từ "học bạ") ✓ |
| R-05 | Q18 + `years=[2026]` | **Không** có chunk đề án 2024, 2025 |
| R-04b | "Lệ phí đăng ký dự thi đánh giá tư duy là bao nhiêu" | Có `dean2024::m1.9` (thông tin chỉ có ở bản cũ, R2) |
| R-06 | Q80 + `programs=["IT1","IT2"]` | Có ít nhất 1 chunk `program_code = IT1` **và** 1 chunk `IT2` ✓ |
| R-07 | Q106 + `faculties=["Trường Vật liệu"]` | `donvi::smse-1` ở #1 ✓ |
| R-08 | Q84 (không nêu khoá) | Có `nnk70::d5` và `nnk71::d5`; `cohorts_found = ["<=K70","K71+"]` ✓ |
| R-09 | Q84 + `cohort="K71"` | Có `nnk71::d5`, **không** có chunk `<=K70` |
| R-10 | "Thời tiết Hà Nội hôm nay" | `low_confidence = true`, `LOW_RETRIEVAL_CONFIDENCE` ✓ (0,38) |
| R-11 | "Điểm chuẩn ĐHQGHN 2025" | **Không** coi là lỗi của T7: `low_confidence = false` (0,645). Test ghi lại điều này để nhắc Router phải chặn |
| R-12 | "Ngành Kỹ thuật Ô tô học những gì" + `programs=["Kỹ thuật Ô tô"]` | `ambiguous` TE1 / TE-E2 (nếu anh duyệt R7) |
| R-13 | Mọi chunk trả về | Có `source_url`; chunk nguồn PDF có `page_no`; `citation.title` không rỗng (AC4) |
| R-14 | **Đo bộ 120 câu** (mức tài liệu) | hit@5 **≥ 81%** (không tệ hơn trước); kỳ vọng Q10 và Q18 chuyển sang trúng (Q18 bằng tài liệu 2026, nếu anh thêm `qui-dinh-ve-xttn-nam-2026-ky` vào cột tham chiếu của Q18) |

---

## 7. Đo lường và test

| Loại | Cần gì | Nội dung |
|---|---|---|
| Không marker | Không mạng | Tách cụm từ (R3), dựng bộ lọc (R2, R5), dựng `citation`, đọc khoá — chạy cùng `pytest backend` |
| Marker `rag` | Qdrant + `OPENAI_API_KEY` | 15 ca mục 6; chạy tay `pytest -m rag`, khoảng 0,001 USD |
| Script đo | như trên | `scripts/eval_retrieval.py`: chạy bộ 120 câu qua **retriever của backend** (không phải `search_chunks.py`), ghi hit@5 + phân bố `top_dense_score` vào `docs/ghi_chu/` |

**Vì sao viết script đo mới:** `search_chunks.py --eval` đo cách tìm dense thuần. Nếu đo bằng nó thì con số không phản ánh retriever thật của bot. Giữ `search_chunks.py` làm mốc so sánh.

## 8. File đụng tới

```
backend/app/rag/retriever.py           mới: Retriever (embedding + Qdrant + nhánh RRF + citation)
backend/app/rag/phrases.py             mới: danh sách cụm từ chuyên ngành + tách từ câu hỏi
backend/app/schemas/rag.py             mới
backend/app/tools/rag_tool.py          mới: T7
backend/app/schemas/common.py          + ErrorCode.LOW_RETRIEVAL_CONFIDENCE
backend/requirements.txt               + qdrant-client, openai (ghim như ingest)
backend/tests/test_rag_unit.py         mới (không mạng)
backend/tests/test_rag_search.py       mới (marker rag, 15 ca)
scripts/eval_retrieval.py              mới
```

## 9. Thứ tự và ước lượng

| Bước | Việc | Ước lượng |
|---|---|---|
| 1 | `retriever.py` + `phrases.py` + test không mạng | ~2 giờ |
| 2 | T7 `rag_tool.py` + 15 ca `rag` | ~1,5 giờ |
| 3 | `eval_retrieval.py`, đo bộ 120 câu, ghi phân bố điểm | ~1 giờ |
| 4 | Ghi "Đã thực hiện", cập nhật tài liệu | ~20 phút |

**Tổng: khoảng 5 giờ.**

---

## 10. Cần anh duyệt

1. **Bảng ca kỳ vọng mục 6** (15 ca).
duyệt
2. **R7 — ngành mơ hồ trong RAG:** hỏi lại như T1/T3 (khuyến nghị), hay lấy chunk của **tất cả** ứng viên rồi để bot trình bày cả hai?
Hãy hỏi lại
3. **R6 — ngưỡng tạm 0,40** cho "không đủ tin cậy", chốt chính thức ở Tuần 4.
duyệt
4. **Sửa cột "Tài liệu tham chiếu"** của Q10, Q12, Q20 trong bộ 120 câu: thêm `trang_tuyen_sinh` (bài điểm chuẩn 2026 là nơi có công thức). Không sửa thì lần đo sau vẫn báo trượt oan. Đây là file của anh: anh tự sửa, hay để tôi sửa? 
bạn sửa đi
5. **Bổ sung chunk RAG "Các mức học phí khác"** của QĐ học phí 2025–2026 và 2026–2027 (học lại, học kỳ hè ×1,5, hệ số lớp ít sinh viên). Hiện RAG chỉ có bản 2024–2025. Thêm 2 chunk và chỉ nhúng 2 chunk này (chi phí gần bằng 0), không nhúng lại toàn bộ.
các thông tin về mức học phí khác của các năm 2026 và 2026 đều đã có thông tin trong file pdf QDHP của cả ở 2 năm
