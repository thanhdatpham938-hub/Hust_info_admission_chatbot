# PLAN — Thiết kế metadata (v2)

**Ngày:** 2026-09-26 · **Thay thế:** `PLAN - Metadata Design (v1).md` (viết 23–24/09, khi corpus còn 573 chunk; giữ lại làm lịch sử, phần "Kết quả kiểm tra xung đột" ở v1 vẫn còn giá trị) · Gắn với PRD v1.2 mục 11.3, 12, 26 · Đi kèm: `PLAN - Data Linking (v1).md`

Mỗi quyết định trong file có dòng **Vì sao** — để người đọc sau (kể cả anh sau 2 tháng) biết lý do chứ không chỉ biết kết quả, và biết khi nào lý do đó hết đúng thì nên đổi.

---

## 1. Từ v1 đến nay đã đổi những gì

Ba ngày qua corpus thay đổi nhiều (Sổ tay trích lại, thêm quy định ngoại ngữ, sửa lỗi chữ), nên số liệu của v1 không dùng được nữa.

| Hạng mục v1 | Trạng thái 2026-09-26 |
|---|---|
| Corpus 573 chunk / 12 nguồn | **622 chunk / 14 nguồn** (thêm 2 quy định ngoại ngữ 14 chunk; Sổ tay 171 → 206) |
| Bước 0: điểm chuẩn theo tổ hợp | ✅ Xong (2025 + 2026, cột `combination_group`) |
| 4b: mọi bảng có cột `year` | ✅ Xong (24/24 bảng) |
| 4c: trùng "Thông tin nhanh" RAG ↔ CSV | ✅ Chốt cách 2 — giữ, ghi là ngoại lệ trong PRD |
| `source_url` của RAG | ✅ 622/622 là link thật (3 PDF nội bộ đã có link, đối chiếu trùng từng byte) |
| Chữ tổ hợp NFD | ✅ Sửa ở Sổ tay, trang ngành, giới thiệu Khoa → 0 chunk còn lỗi |
| `chunk_id`, `dataset_version`, `collection_date` | ❌ Vẫn 0/622 |
| `verification_status` | ❌ Vẫn 43/622 |
| `page_no` nguồn PDF | ❌ Vẫn thiếu 80 chunk (cùng 4 nguồn như v1) |
| `year` | ❌ Thiếu 50 (giới thiệu Khoa 38, trang tuyển sinh 12) |
| 3 quyết định chờ anh (v1) | Vẫn chờ — v2 đưa khuyến nghị cụ thể ở mục 7 |

**Lỗi mới phát hiện khi đo lại:**

| # | Lỗi | Số chunk | Nguyên nhân |
|---|---|---|---|
| N1 | Khoá cấu hình nội bộ `stop_at`, `layout` lọt vào metadata | 14 (2 quy định ngoại ngữ) | `pdf_to_rag_md.py` chép nguyên dict cấu hình vào chunk |
| N2 | Chunk quá dài (> 2.500 ký tự) | 12 | Điều luật dài không tách khoản (XTTN Điều 2, 4; TSA Điều 9, 15, 24, 31); bảng ĐRL Sổ tay |
| N3 | `document_type` 13 giá trị | — | v1 đếm 12; thêm `quy_dinh_ngoai_ngu` |

---

## 2. Hiện trạng đo lại (622 chunk)

| Trường | Có | Thiếu ở đâu |
|---|--:|---|
| `document_title`, `document_type`, `source_url`, `heading`, `text` | 622 | — |
| `year` | 572 | giới thiệu Trường/Khoa 38, trang tuyển sinh 12 |
| `page_no` | 311 | **nguồn PDF thiếu 80**: đề án 2024 (37), quy chế TSA (35), KKHT (7), học phí (1). Nguồn web (231) không cần |
| `program_code` | 151 | chỉ trang ngành — đúng |
| `faculty_code` | 38 | chỉ giới thiệu Khoa; **trang ngành chưa có** (xem Data Linking) |
| `dieu_no` / `khoan_no` / `chuong` | 148 / 47 / 317 | đúng theo cấu trúc tài liệu |
| `verification_status` | 43 | 579 |
| `chunk_id`, `source_kind`, `dataset_version`, `collection_date` | 0 | toàn bộ |

Bên CSV (24 bảng): thiếu `dataset_version` 21 bảng · `collection_date` 11 · `source_url` 10 · `source` 13 · `verification_status` 5 · `year` 0.

---

## 3. Chunk ID

**Quyết định (khuyến nghị):** `<doc_slug>::<locator>`, sinh lại y hệt mỗi lần chạy.

| Nguồn | Mẫu | Ví dụ |
|---|---|---|
| Văn bản có Điều / khoản | `<doc>::d<điều>[k<khoản>]` | `qcdt2025::d19k2`, `nnk71::d4` |
| Sổ tay | `sotay2026::p<trang in>-<thứ tự>` | `sotay2026::p30-2` |
| Đề án | `dean<năm>::m<mã mục>` | `dean2024::m1.10a` |
| Trang ngành | `nganh::<mã ngành>-<phần>` | `nganh::IT1-2` |
| Giới thiệu Khoa | `donvi::<mã Khoa>-<phần>` | `donvi::SOICT-3` |
| Bài tuyển sinh | `ts::<slug bài>-<phần>` | `ts::diem-chuan-2026-3` |
| Chunk bị tách vì quá dài | thêm hậu tố `-<n>` | `tsa2024::d24-2` |

**Vì sao không dùng số thứ tự:** thêm 1 chunk ở giữa là lệch ID toàn bộ phía sau → bộ test ghim "câu hỏi này phải trúng chunk nào" vỡ hết.
**Vì sao không dùng hash:** hash ổn định và ngắn, nhưng nhìn `a3f9…` không biết là đoạn nào — mỗi lần debug phải tra ngược. Với 622 chunk, lợi ích "ngắn gọn" không đáng bằng việc đọc log là hiểu ngay.
**Vì sao Sổ tay dùng trang in:** bản trích lại đã gắn số trang in (2–109) — đúng số người dùng thấy khi mở sổ tay; số trang PDF (1 trang PDF = 2 trang in) sẽ khiến citation lệch.
**Khi nào nên đổi:** nếu một nguồn đổi cấu trúc (vd đề án 2027 bỏ mã mục) thì locator của nguồn đó đổi theo — chỉ ảnh hưởng nguồn đó.

---

## 4. Từ điển trường

### Nhóm A — Định danh & nguồn gốc (bắt buộc mọi chunk)

`chunk_id` · `document_title` · `document_type` · `source_kind` · `source_url` · `dataset_version` · `collection_date` · `verification_status`

**Vì sao thêm `source_kind` (`pdf_text` / `pdf_scan` / `web`):** PRD mục 12 quy định citation khác nhau theo loại nguồn, mục 11.3 quy định `page_no` chỉ bắt buộc với PDF. Không có trường này thì hai luật đó phải đoán từ tên file — logic ngầm, sai lúc nào không biết.

### Nhóm B — Định vị trong tài liệu

`heading` (mọi chunk) · `page_no` (bắt buộc khi `source_kind` là PDF) · `chuong`, `dieu_no`, `khoan_no` (khi tài liệu có) · `muc_no` (đề án — tách ra khỏi `heading`).

**Vì sao tách `muc_no`:** hiện mã mục "1.10a" nằm lẫn trong `heading`; muốn lọc/citation theo mục phải cắt chuỗi — dễ sai.

### Nhóm C — Lọc trước khi tìm

`year` · `program_code` · `faculty_code` · `document_no` · **`cohort` (mới)**

**Vì sao thêm `cohort`:** hai quy định ngoại ngữ **cùng còn hiệu lực**: bản K71 (10828) áp dụng từ khóa 71, bản K70 (10728) cho khóa 70 trở về trước. Cả hai đều có `year` hợp lệ nên lọc theo năm không phân biệt được. Giá trị: `K71+` / `<=K70`; rỗng với tài liệu áp dụng chung.
**Vì sao Nhóm C quan trọng nhất về chất lượng:** v1 đã đo — đề án 2025 và 2026 giống nhau 78% ở mục phương thức; thiếu `year` thì hỏi 2026 rất dễ nhận chunk 2025.

### Luật điền giá trị còn thiếu

| Trường | Luật | Vì sao |
|---|---|---|
| `year` của giới thiệu Khoa (38) | = năm thu thập (2026) | Theo quy ước anh đã chốt: dữ liệu crawl từ web Trường/Khoa mặc định là mới nhất |
| `year` của trang tuyển sinh (12, bài giới thiệu TSA) | = 2026 | Cùng quy ước; các bài có năm trong tiêu đề (điểm chuẩn 2024/25/26) đã có `year` |
| `faculty_code` của trang ngành (151) | lấy từ bảng `programs` qua `program_code` | Không suy từ nội dung — một nguồn duy nhất (xem Data Linking) |
| `verification_status` (579) | theo cách bóc: `html_parsed` (web), `pdf_text` (PDF có chữ), `vision_extracted` (scan), `manual_override` (Sổ tay trang chép tay) | Người dùng/đánh giá cần biết đoạn nào máy đọc, đoạn nào người chép |

**Từ vựng `verification_status` bổ sung 2 giá trị:** `manual_override` (22 trang Sổ tay chép tay) và `third_party` (cột môn chính lấy từ tuyensinh247). **Vì sao:** hai loại này độ tin cậy khác hẳn phần còn lại, gộp vào `html_parsed` là che mất rủi ro.

---

## 5. `document_type`: 13 → 9 giá trị

| Giá trị chốt | Gộp từ | Chunk |
|---|---|--:|
| `quy_che_dao_tao` | giữ | 76 |
| `so_tay_sinh_vien` | giữ | 206 |
| `de_an_tuyen_sinh` | giữ | 52 |
| `quy_dinh` | `quy_dinh_xttn` + `quy_dinh_hoc_phi` + `quy_dinh_hoc_bong_kkht` | 23 |
| `quy_dinh_ngoai_ngu` | giữ riêng | 14 |
| `quy_che_thi_tsa` | giữ | 35 |
| `gioi_thieu_nganh` | giữ | 151 |
| `gioi_thieu_don_vi` | `gioi_thieu_truong` | 38 |
| `tin_tuyen_sinh` | `cong_bo_diem_chuan` + `tsa_gioi_thieu` + `tsa_cam_nang` | 27 |

**Vì sao gộp 3 loại bài tuyển sinh:** cùng một nguồn (trang ts.hust.edu.vn), Router lọc theo `document_type` — tách 3 giá trị chỉ làm luật lọc rối mà không thêm khả năng gì. Chi tiết vẫn còn ở `document_title`.
**Vì sao giữ `quy_dinh_ngoai_ngu` riêng:** chủ đề chuẩn đầu ra TOEIC/IELTS là nhóm câu hỏi riêng, và đây là lần duy nhất ta **đã thiếu dữ liệu vì gộp lẫn** (lỗ hổng TOEIC 24/09). Để riêng thì Router lọc thẳng được.
**Vì sao KKHT gộp vào `quy_dinh` (trả lời câu hỏi v1):** chỉ 7 chunk; câu hỏi học bổng còn trúng Sổ tay (mục học bổng) — tách riêng không giúp tìm đủ. Rủi ro nhầm ngưỡng GPA với bảng điểm rèn luyện (A3 ở v1) xử lý bằng `document_title` trong citation, không bằng tách loại.

---

## 6. Script & kiểm tra

### `scripts/normalize_chunks.py` (mới)

Đọc 14 file `data/rag/raw_chunks/*.chunks.jsonl` → ghi `data/rag/normalized/`. **Không ghi đè file gốc.**
**Vì sao không ghi đè:** 14 file gốc do 8 script khác nhau sinh ra; nếu normalize ghi đè thì lần chạy lại script gốc sẽ xoá metadata, và khi nghi ngờ không còn bản để đối chiếu.

Việc làm theo thứ tự: bỏ khoá rác (N1) → tách chunk dài (N2) → sinh `chunk_id` → gắn `source_kind`, `dataset_version`, `collection_date`, `verification_status`, `cohort` theo bảng cấu hình từng nguồn → gộp `document_type` → bù `year`, `faculty_code` → tách `muc_no` → chuẩn NFC lần cuối → xếp thứ tự trường.

**Luật tách chunk dài (N2):** > 2.500 ký tự thì tách theo khoản/điểm (a, b, c…) hoặc theo dòng bảng; mỗi mảnh giữ nguyên dòng `[tiêu đề]` đầu chunk.
**Vì sao ngưỡng 2.500:** PRD mục 11.2 đặt `MAX_CHUNK_CHARS = 2500`; 12 chunk vượt là do bóc Điều không tách khoản — Điều 24 quy chế TSA dài 5.011 ký tự, embedding một khối như vậy thì mọi câu hỏi về coi thi đều "hơi giống" nó.

### `scripts/validate_metadata.py` (mới)

| Luật | Mức |
|---|---|
| `chunk_id` duy nhất toàn corpus | Lỗi |
| Đủ 8 trường Nhóm A | Lỗi |
| `source_kind` là PDF mà thiếu `page_no` | Lỗi |
| Giá trị ngoài từ vựng (`document_type`, `verification_status`, `source_kind`, `cohort`) | Lỗi |
| `source_url` không phải `http(s)://` | Lỗi |
| Chữ không phải NFC | Lỗi |
| Có khoá ngoài từ điển trường (bắt được N1) | Lỗi |
| `chunk_id` đổi so với lần chạy trước | Cảnh báo |
| Chunk > 2.500 hoặc < 80 ký tự | Cảnh báo |

**Thử ngược bằng lỗi cố ý** trước khi tin validator (như `validate_aliases.py`). **Vì sao:** lần làm từ điển alias, validator chạy sạch mà vẫn bỏ lọt 5 lỗi thật — chạy sạch chỉ có nghĩa khi đã chứng minh nó bắt được lỗi.

### CSV — 6 cột chuẩn cho mọi bảng dữ liệu

`year` · `source` · `source_url` · `collection_date` · `verification_status` · `dataset_version`

**Vì sao cần cả `source` lẫn `source_url`:** `source` là nhãn người đọc ("Đề án 2024 – Bảng 9"), `source_url` là link bấm được — trước đây hai cột dùng thay nhau nên file có cái này thiếu cái kia. Nay cả 3 PDF nội bộ đã có link nên **mọi bảng đều điền được `source_url`**.
Ngoại lệ: `entity_aliases`, `program_aliases` là bảng tra cứu tự lập, không phải dữ liệu nguồn → chỉ cần `dataset_version`.

---

## 7. `page_no` cho 80 chunk PDF

| Nguồn | Chunk | Cách | Ước lượng |
|---|--:|---|---|
| Đề án 2024 | 37 | Bóc lại bằng PyMuPDF (PDF có chữ), gắn trang theo khối văn bản | tự động |
| KKHT 2022 | 7 | Bản scan (2 trang, không có lớp chữ) chép bằng vision → gắn tay theo ảnh | ~10 phút |
| Học phí 2024–2025 | 1 | PDF có chữ (7 trang); chunk "các mức học phí khác" nằm ở Phụ lục I | ~2 phút |
| Quy chế thi TSA | 35 | Bản scan (19 trang, không có lớp chữ) chép bằng vision → gắn tay theo ảnh | ~1 giờ |

**Khuyến nghị cho TSA:** gắn tay. **Vì sao:** AC4 yêu cầu citation có số trang với nguồn PDF; quy chế TSA là nguồn chính cho nhóm câu hỏi về kỳ thi. Bỏ số trang riêng tài liệu này thì phải ghi ngoại lệ vào PRD — rẻ hơn về công nhưng tạo một luật đặc biệt phải nhớ mãi.

---

## 8. Thứ tự thực hiện

| Bước | Việc | Ước lượng |
|---|---|---|
| 1 | Anh chốt mục 9 | — |
| 2 | Sửa dữ liệu nền theo `PLAN - Data Linking` bước 1–2 (mã Khoa, tên ngành) | ~1h |
| 3 | Viết `normalize_chunks.py` → `data/rag/normalized/` | ~2h |
| 4 | Bù `page_no` 80 chunk | ~1,5h |
| 5 | Thêm 6 cột chuẩn cho CSV | ~1h |
| 6 | `validate_metadata.py` + thử ngược | ~1,5h |
| 7 | Chạy toàn bộ, chốt `dataset_version = 2026.1` | ~0,5h |

**Vì sao bước 2 (nối dữ liệu) đứng trước normalize:** `faculty_code` của 151 chunk trang ngành lấy từ bảng `programs`; bảng này đang gán sai TE1 và thiếu TROY-IT. Normalize trước thì lỗi đó nhân lên vào metadata đã nhúng.
**Vì sao phải xong bước 7 mới embed:** metadata nằm cùng vector — sửa sau khi embed là nhúng lại toàn bộ và mất mọi kết quả đánh giá đã chạy.

## 9. Cần anh quyết

1. `chunk_id` dạng `<doc>::<locator>` (khuyến nghị) hay hash.
2. `document_type` 9 giá trị như mục 5 (KKHT gộp vào `quy_dinh`, ngoại ngữ để riêng).
3. `page_no` TSA: gắn tay 35 chunk (khuyến nghị) hay ghi ngoại lệ.

---

# Đã thực hiện (2026-09-27)

Anh chốt: `chunk_id` dạng `<doc>::<locator>`, `document_type` 9 giá trị, gắn tay `page_no` cho quy chế TSA. Phần Data Linking để sau.

## Kết quả

| Hạng mục | Trước | Sau |
|---|---|---|
| Chunk | 622 (có 12 chunk > 2.500 ký tự) | **637** trong `data/rag/normalized/` — 11 chunk dài được tách thành 26 đoạn; dài nhất 2.371 ký tự |
| `chunk_id` | 0 | 637, **0 trùng**, dạng `qcdt2025::d19k2`, `sotay2026::p30-2`, `nganh::it1-2`, `tsa2024::d24-3` |
| `page_no` nguồn PDF | thiếu 80 | **404/404** chunk PDF có trang |
| `verification_status` | 43 | 637: `pdf_text` 301 · `html_parsed` 233 · `manual_override` 54 · `vision_extracted` 49 |
| `document_type` | 13 giá trị | 9 giá trị |
| `year` | thiếu 50 | đủ 637, kiểu số nguyên |
| `faculty_code` trang ngành | 0/151 | 152/152 |
| `cohort` | — | 7 chunk `K71+`, 7 chunk `<=K70` |
| Khoá rác `stop_at`, `layout` | 14 chunk | 0 |
| CSV: 6 cột chuẩn | thiếu ở 21 bảng | đủ ở 22 bảng dữ liệu; 2 bảng tra cứu có `dataset_version` |

Kiểm tra: `validate_metadata.py` → **0 lỗi**, 2 cảnh báo (bảng học phí 2024 còn là `vision_extracted` — đã soát tay theo danh sách ngày 24/09, chưa đổi nhãn). Tự thử ngược: **19/19 lỗi cài cố ý bị bắt**. Chạy trên chunk gốc chưa chuẩn hoá thì báo đúng các con số hiện trạng đã đo (50 thiếu `year`, 579 thiếu `verification_status`, 151 chunk ngành thiếu `faculty_code`…) — chứng tỏ luật đo đúng thứ cần đo.

## Các lựa chọn phát sinh trong lúc làm — và vì sao

| Lựa chọn | Vì sao |
|---|---|
| `page_no` = **số trang của file PDF**, không phải số in trên trang | QCDT, XTTN, quy định ngoại ngữ vốn đã dùng số trang PDF (đã kiểm: 105/105 Điều nằm đúng trang). Người dùng mở PDF thấy số này trên thanh trang. Riêng Sổ tay giữ **số trang in** vì 1 trang PDF chứa 2 trang in. |
| Trang TSA/KKHT tra tay theo ảnh, ghi thành bảng `PAGE_BY_DIEU` trong script | Hai bản scan không có lớp chữ nên không tự dò được. Ghi thành bảng (không sửa tay vào file chunk) để lần chạy lại không mất, và người khác kiểm lại được bằng ảnh `data/raw/tsa_quyche/p*.png`. |
| Trang đề án 2024 dò tự động từ lớp chữ PDF | PDF có chữ; mỗi chunk lấy trang xuất hiện nhiều nhất của các dòng chỉ có ở một trang, bỏ trang lạc xa > 2 — cách đầu (tìm tuần tự) hỏng vì bảng 12 trang (5–17) không có trong chunk. Kết quả 37/37 chunk, thứ tự trang tăng dần. |
| Đoạn tách dài lặp lại dòng `[tiêu đề]` và **dòng tiêu đề cột** nếu cắt giữa bảng | Mảnh không có tiêu đề thì đọc riêng không biết thuộc Điều nào / cột nào là gì. Sửa luôn `sotay_to_rag.py` — comment ở đó nói có lặp tiêu đề bảng nhưng code không làm. |
| `chunk_id` sinh **trước** khi tách | Sinh sau thì các mảnh bị coi là trùng khoá và nhận hai lần hậu tố (`d24-1-1`). |
| Bỏ `program_name` khỏi chunk | Theo PLAN Data Linking: 49/68 ngành đang có nhiều tên; tên chỉ nên sống ở bảng danh mục. Nội dung chunk vẫn có tên ngành trong dòng `[tiêu đề]`. |
| `faculty_code` trang ngành lấy từ `programs_2026.csv` | File `data/programs/*.json` đang gán sai TE1 → FED và thiếu mã TROY-IT; bảng danh mục thì đúng. |
| Sửa `source_url` bảng tổ hợp sang trang từng ngành | Là ngoại lệ duy nhất ghi đè giá trị cũ: link cũ trỏ trang danh mục chung, citation không dẫn được đúng ngành. |
| Dòng `chua_ro` của bảng công thức để trống `source_url` | Dòng do mình đặt ra (rule_derived), không có nguồn; validator cho phép trống **chỉ khi** `verification_status = rule_derived`. |

## Lỗi phát hiện thêm và đã sửa

- **Rác trang web trong đề án 2025/2026:** chunk cuối chứa danh sách "Có thể bạn sẽ thích" (vd "Vũ Văn Bình - Bạn trẻ gương mặt hiền khô làm lợi cho Viettel…"). Sửa tận gốc ở `de_an_to_rag.py`: dừng ở dòng "Lưu tin".
- **`validate_aliases.py` hỏng khi thử ngược:** so số cột với hằng số 7 (báo sai toàn bộ khi bảng thêm cột) và **crash** khi gặp dòng thiếu ô. Nay dòng lệch cột được báo lỗi và bỏ qua ở các bước sau.

## Thứ tự chạy lại khi dữ liệu nguồn thay đổi

```
(script bóc nguồn nào đổi thì chạy script đó: sotay_to_rag, de_an_to_rag, crawl_program_pages --offline, ...)
python scripts/add_main_subject.py        # nếu chạy lại verify_subject_combinations --write
python scripts/normalize_csv_meta.py      # script bóc ghi đè CSV -> bù lại 6 cột chuẩn
python scripts/normalize_chunks.py        # -> data/rag/normalized/
python scripts/validate_metadata.py       # phải 0 lỗi; cảnh báo W1 nếu chunk_id đổi
```

**Bước embed đọc `data/rag/normalized/`, không đọc `data/rag/raw_chunks/*.chunks.jsonl`.**

## Quyết định 2026-09-29: giữ học phí trong dòng "Thông tin nhanh" của chunk ngành

Học phí 2026 nằm ở cả `tuition_2026.csv` và 68 chunk ngành (khớp 68/68). Đã cân nhắc bỏ khỏi chunk; **anh chốt giữ nguyên.**

**Vì sao giữ được:**
- Chunk ngành có `year = 2026` → khi vào ngữ cảnh, con số luôn đi kèm năm.
- Chunk ngành và `tuition_2026.csv` cùng bóc từ trang ngành ts.hust.edu.vn trong một lần chạy → cập nhật năm sau thì cả hai đổi cùng lúc.
- `chunk_id` không chứa năm (`nganh::it1-1`) → lần bóc 2027 **thay thế** chunk 2026 cùng ID, không để hai phiên bản học phí cùng tồn tại trong kho vector.

**Điều kiện đi kèm (không được bỏ):**
- Cập nhật học phí = chạy lại crawl trang ngành rồi chạy lại chuỗi chuẩn hoá + embed; **không sửa tay riêng CSV**.
- Luật truy xuất: câu hỏi không nêu năm thì ưu tiên dữ liệu năm mới nhất (áp dụng chung cho học phí, đề án, điểm chuẩn).

## Quyết định 2026-09-29: chuỗi đem đi embed

Chuỗi embed = `<document_title> <year> | <heading>` + xuống dòng + `text`. Ví dụ: `Đề án tuyển sinh 2026 | 2. Các phương thức tuyển sinh` rồi đến nội dung. Trường `text` trong payload Qdrant giữ nguyên (để trích dẫn); chỉ vector được tính trên chuỗi đã ghép.

**Vì sao:** đo trùng lặp trên 637 chunk: đề án 2025 ↔ 2026 mục phương thức giống 79%, quy định ngoại ngữ K70 ↔ K71 có 3 Điều giống 100%. Không ghép năm/tên tài liệu thì các cặp này gần như cùng một vector, truy xuất lấy bừa một bên. Bộ lọc metadata (`year`, `cohort`) vẫn là tuyến chặn chính; ghép chuỗi là tuyến thứ hai khi câu hỏi không nêu năm.

Hạ tầng: Qdrant chạy Docker (`docker-compose.yml`, ghim `qdrant/qdrant:v1.19.1` khớp `qdrant-client` 1.19), collection `hust_rag_2026_1`. Kiểm tra môi trường: `python scripts/check_setup.py [--openai]`.
