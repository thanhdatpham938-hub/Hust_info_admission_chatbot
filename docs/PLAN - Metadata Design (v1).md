# PLAN — Thiết kế metadata (v1)

> **Đã có bản v2 (2026-09-26): `PLAN - Metadata Design (v2).md`.** Số liệu hiện trạng bên dưới là của corpus cũ (573 chunk); giữ file này làm lịch sử và vì phần "Kết quả kiểm tra xung đột" vẫn còn giá trị.

**Ngày:** 2026-09-23 · **Trạng thái:** bản nháp để anh đọc và sửa · Gắn với PRD v1.2 mục 11.3, 12, 26

## Vì sao phải làm trước khi embed

Metadata được nhúng kèm vector. Sửa metadata sau khi đã embed 573 chunk thì phải nhúng lại
toàn bộ — mất tiền API và mất luôn mọi kết quả đánh giá đã chạy trước đó. Đây là việc **rẻ
nếu làm bây giờ, đắt nếu làm sau**, nên xếp trước Tuần 2.

## Hiện trạng: 6 điểm lệch đã đo được

| # | Vấn đề | Số liệu thật |
|---|---|---|
| 1 | **Không có `chunk_id`** | 0/573 chunk có định danh riêng |
| 2 | Thiếu `dataset_version` và `collection_date` | 0/573 chunk (PRD mục 26 bắt buộc) |
| 3 | `verification_status` chỉ có ở 3 nguồn | 43/573 chunk |
| 4 | `page_no` thiếu ở nguồn PDF/scan | 262/573 có — nhưng **80 chunk từ PDF vẫn trống**: đề án 2024 (37), quy chế TSA (35), KKHT (7), học phí (1) |
| 5 | `year` thiếu | 523/573 — thiếu 50: giới thiệu Trường/Khoa (38) và trang tuyển sinh (12) |
| 6 | `document_type` có 12 giá trị, lẫn cấp độ | 3 giá trị (`tsa_gioi_thieu`, `tsa_cam_nang`, `cong_bo_diem_chuan`) thực ra cùng một nguồn |

QCDT, Sổ tay và XTTN đã có đủ `page_no` — chỗ thiếu chỉ nằm ở 4 nguồn PDF chưa gắn trang
lúc bóc. 231 chunk còn lại thuộc nguồn web nên không cần số trang (PRD v1.2 mục 12).

Bên CSV cũng lệch: **20/20 file thiếu `dataset_version`**, 12 file thiếu `source`, 10 file
thiếu `collection_date`, 10 file thiếu `source_url`, 5 file thiếu `verification_status` —
và hai cột `source` / `source_url` đang dùng thay thế nhau chứ không phải bổ sung nhau.

---

## Phần 1 — `chunk_id`: thứ quan trọng nhất đang thiếu

Không có định danh chunk thì: citation không truy ngược được về đúng đoạn, bộ test không
ghim được "câu hỏi này phải lấy chunk nào", và khi nhúng lại không biết chunk nào đã đổi.

**Quy ước đề xuất:** `<doc_slug>::<locator>` — người đọc hiểu được, máy sinh lại y hệt mỗi
lần chạy (không dùng số thứ tự chạy, vì thêm một chunk ở giữa là lệch toàn bộ phía sau).

| Loại nguồn | Mẫu | Ví dụ |
|---|---|---|
| Văn bản có Điều/khoản | `<doc>::d<điều>k<khoản>` | `qcdt2025::d19k2` |
| Văn bản có Điều, không tách khoản | `<doc>::d<điều>` | `kkht2022::d3` |
| Sổ tay (theo mục + trang) | `<doc>::p<trang>-<thứ tự trong trang>` | `sotay2026::p42-1` |
| Đề án (theo mục đánh số) | `<doc>::m<mã mục>` | `dean2024::m1.10a` |
| Trang ngành | `nganh::<mã ngành>-<phần>` | `nganh::IT1-1` |
| Trang web khác | `<doc>::<slug mục>` | `tsa2026::cau-truc-de-thi` |

**Ràng buộc:** duy nhất toàn corpus, chỉ chữ thường/số/`-`/`::`, không dấu tiếng Việt,
và **ổn định giữa 2 lần chạy** — đây là điều kiện để bộ test ghim được kết quả mong đợi.

---

## Phần 2 — Từ điển trường metadata

Chia 3 nhóm theo mục đích, vì trộn lẫn là lý do khiến hiện trạng lệch lạc như bây giờ.

### Nhóm A — Định danh & nguồn gốc (bắt buộc với MỌI chunk)

| Trường | Kiểu | Ý nghĩa | Hiện có? |
|---|---|---|---|
| `chunk_id` | string | Định danh duy nhất, theo Phần 1 | **Chưa có** |
| `document_title` | string | Tên tài liệu hiển thị trong citation | ✔ 573/573 |
| `document_type` | enum | Lọc theo loại tài liệu (Phần 3) | ✔ 573/573 |
| `source_kind` | enum | `pdf_scan` / `pdf_text` / `web` — **quyết định luật citation và luật `page_no`** | **Chưa có** |
| `source_url` | string | Link về nguồn | ✔ 573/573 |
| `dataset_version` | string | `2026.1` | **Chưa có** |
| `collection_date` | date | Ngày thu thập | **Chưa có** |
| `verification_status` | enum | `vision_extracted` / `pdf_text` / `html_parsed` / `web_extracted` / `manual_verified` | 43/573 |

> `source_kind` là trường mới tôi đề xuất thêm ngoài PRD. Lý do: PRD mục 12 quy định
> citation khác nhau theo loại nguồn, và mục 11.3 quy định `page_no` chỉ bắt buộc với
> PDF/scan. Nếu không có trường này thì cả hai luật đó phải suy ra bằng cách đoán từ tên
> file — tức là logic ngầm, sai lúc nào không biết.

### Nhóm B — Định vị trong tài liệu (bắt buộc theo loại nguồn)

| Trường | Bắt buộc khi | Hiện có |
|---|---|---|
| `dieu_no` | tài liệu có cấu trúc Điều | 134 chunk |
| `khoan_no` | chunk là một khoản riêng | 47 chunk |
| `chuong` | tài liệu có Chương | 111 chunk |
| `muc_no` | đề án tuyển sinh (mục 1.10a…) | **chưa có, đang nhét trong `heading`** |
| `heading` | mọi chunk | ✔ 573/573 |
| `page_no` | `source_kind` ∈ {`pdf_scan`, `pdf_text`} | 262 chunk (thiếu 80) |

### Nhóm C — Lọc trước khi tìm kiếm (tuỳ nguồn)

| Trường | Dùng để | Hiện có |
|---|---|---|
| `year` | Lọc theo năm tuyển sinh | 523/573 |
| `program_code` | Hỏi 1 ngành → lọc thẳng, không tìm theo ngữ nghĩa | 151 |
| `faculty_code` | Hỏi 1 Trường/Khoa | 38 |
| `document_no` | Số hiệu văn bản (5445/QĐ-ĐHBK) | 133 |

**Nhóm C đáng giá nhất về chất lượng trả lời.** Câu "ngành IT1 học mấy năm" nếu lọc
`program_code = IT1` trước rồi mới tìm thì luôn đúng ngành; nếu tìm theo ngữ nghĩa trên
toàn bộ 573 chunk thì rất dễ trả về ngành khác có mô tả gần giống.

---

## Phần 3 — Gom lại `document_type`

12 giá trị hiện tại lẫn hai cấp: có cái là *loại tài liệu*, có cái là *một bài viết cụ thể*.
Đề xuất còn 8, và chuyển phần chi tiết xuống `document_title`:

| Giá trị chốt | Gộp từ | Chunk |
|---|---|---|
| `quy_che_dao_tao` | giữ nguyên | 76 |
| `so_tay_sinh_vien` | giữ nguyên | 171 |
| `de_an_tuyen_sinh` | giữ nguyên | 52 |
| `quy_dinh` | `quy_dinh_hoc_bong_kkht` + `quy_dinh_xttn` + `quy_dinh_hoc_phi` | 23 |
| `quy_che_thi_tsa` | giữ nguyên | 35 |
| `gioi_thieu_nganh` | giữ nguyên | 151 |
| `gioi_thieu_don_vi` | `gioi_thieu_truong` | 38 |
| `tin_tuyen_sinh` | `cong_bo_diem_chuan` + `tsa_gioi_thieu` + `tsa_cam_nang` | 27 |

Lý do gộp: Router sẽ lọc theo `document_type`. Ba giá trị `cong_bo_diem_chuan` /
`tsa_gioi_thieu` / `tsa_cam_nang` đều là bài đăng trên trang tuyển sinh, tách ra chỉ làm
luật lọc phức tạp mà không thêm khả năng gì. Phân biệt chi tiết vẫn còn ở `document_title`.

**Cần anh quyết:** có tách `quy_dinh_hoc_bong_kkht` ra riêng không? Học bổng là chủ đề
sinh viên hỏi nhiều, để riêng thì lọc nhanh hơn — nhưng chỉ có 7 chunk.

---

## Phần 4 — Chuẩn metadata cho bảng CSV

Mọi file trong `data/processed/` phải có đủ 5 cột cuối, thứ tự cố định:

| Cột | Quy tắc |
|---|---|
| `source` | Nhãn nguồn đọc được, dùng in trong citation — vd `Đề án tuyển sinh 2024 - Bảng 9` |
| `source_url` | Link nếu nguồn có trên web; rỗng nếu nguồn là PDF nội bộ |
| `collection_date` | Ngày thu thập |
| `verification_status` | Cùng từ vựng với RAG |
| `dataset_version` | `2026.1` |

Hiện `source` và `source_url` đang dùng thay thế nhau — file thì có cái này, file thì có
cái kia. **Phải có cả hai**: `source` để hiển thị cho người đọc, `source_url` để bấm vào.
Nguồn PDF nội bộ thì `source_url` rỗng là hợp lệ, nhưng `source` thì không được rỗng.

Việc cần làm: bổ sung cột cho 20 file — 20 file thiếu `dataset_version`, 12 thiếu `source`,
10 thiếu `collection_date`, 10 thiếu `source_url`, 5 thiếu `verification_status`.

---

## Phần 5 — Script và luật kiểm tra

### `scripts/normalize_chunks.py` (mới)

Đọc 12 file `.chunks.jsonl` → chuẩn hoá → ghi ra `data/rag/normalized/`. **Giữ nguyên file
gốc**, không ghi đè, để còn đối chiếu khi nghi ngờ.

Việc script làm: sinh `chunk_id` · gắn `source_kind` theo bảng cấu hình từng nguồn · điền
`dataset_version` + `collection_date` · gắn `verification_status` cho 530 chunk đang thiếu ·
gom `document_type` theo Phần 3 · bù `year` cho 50 chunk thiếu · tách `muc_no` khỏi `heading`
cho đề án · xếp lại thứ tự trường cho dễ đọc.

### `scripts/validate_metadata.py` (mới)

| Luật | Mức |
|---|---|
| `chunk_id` duy nhất toàn corpus | Lỗi |
| Đủ 8 trường Nhóm A | Lỗi |
| `source_kind = pdf_*` nhưng thiếu `page_no` | Lỗi |
| `document_type` / `verification_status` / `source_kind` ngoài từ vựng | Lỗi |
| `source_url` sai định dạng URL | Lỗi |
| CSV thiếu 1 trong 5 cột chuẩn | Lỗi |
| `chunk_id` đổi so với lần chạy trước | Cảnh báo |
| Chunk quá dài/quá ngắn bất thường | Cảnh báo |
| Còn bản ghi `verification_status = vision_extracted` ở bảng điểm chuẩn/học phí | Cảnh báo |

Làm như `validate_aliases.py`: **thử ngược bằng lỗi cố ý** để chắc validator thật sự bắt
được, chứ không phải chạy sạch vì nó không kiểm gì. Lần làm từ điển alias đã cho thấy chạy
sạch mà không thử ngược thì vô nghĩa — validator lúc đó bỏ lọt 5 lỗi thật.

---

## Phần 6 — Việc phải làm tay, không script được

`page_no` cho **80 chunk** nguồn PDF/scan: đề án 2024 (37), quy chế TSA (35), KKHT (7),
học phí (1). QCDT, Sổ tay và XTTN đã có đủ trang nên không phải đụng tới.

Cách làm: khi bóc lại từ PDF thì PyMuPDF trả về số trang của từng khối văn bản — nối số đó
vào chunk ngay lúc bóc, không đoán ngược từ nội dung. Với bản scan TSA đã chép tay bằng
vision thì phải gắn trang thủ công theo ảnh từng trang.

Đây là điều kiện để đạt AC4, nên không bỏ qua được.

---

## Thứ tự thực hiện

| Bước | Việc | Ước lượng |
|---|---|---|
| 1 | Anh duyệt Phần 2 và Phần 3 (từ vựng + trường bắt buộc) | — |
| 2 | Viết `normalize_chunks.py`, chạy ra `data/rag/normalized/` | ~2h |
| 3 | Bù `page_no` cho 80 chunk nguồn PDF/scan | ~2h |
| 4 | Thêm 5 cột chuẩn cho 20 file CSV | ~1h |
| 5 | Viết `validate_metadata.py` + thử ngược bằng lỗi cố ý | ~1,5h |
| 6 | Chạy toàn bộ, chốt `dataset_version = 2026.1` | ~0,5h |

Xong bước 6 mới được phép embed. Trước đó chưa.

## Ba chỗ cần anh quyết

1. **`chunk_id` theo quy ước ở Phần 1** — hay anh muốn dùng hash cho gọn? (Hash thì ngắn và
   chắc chắn duy nhất, nhưng nhìn vào không biết là chunk nào, lúc debug sẽ khổ.)
2. **Có tách `quy_dinh_hoc_bong_kkht` thành loại riêng không** (Phần 3).
3. **`page_no` cho bản scan TSA** — gắn tay 35 chunk, hay chấp nhận citation chỉ có số Điều
   và bỏ số trang cho riêng tài liệu này?

---

# Kết quả kiểm tra xung đột & trùng lặp (2026-09-24)

Chạy trước khi anh duyệt plan. Bốn hướng kiểm: (1) số liệu lặp giữa CSV và RAG, (2) cùng
một quy định ở nhiều tài liệu có nói khác nhau không, (3) dữ liệu ngoài phạm vi năm,
(4) đo trùng lặp văn bản giữa 573 chunk.

## Trả lời ngắn cho 2 câu hỏi của anh

**Dữ liệu có trùng nhau quá nhiều không?** Không. Chỉ **29/573 chunk (5%)** dính vào ít
nhất một cặp trùng đáng kể (Jaccard ≥ 0,35), tổng 15 cặp. Mức này lành.

**Nó có ảnh hưởng gì không?** Phần trùng thì không, **nhưng tìm ra 1 lỗi nặng không liên
quan tới trùng lặp** — xem mục A1. Lỗi này phải sửa trước khi nạp DB.

## A. Xung đột thật, không phải chuyện khác năm

### A1. NGHIÊM TRỌNG — 15/68 ngành: CSV trả sai điểm chuẩn 0,5 điểm

Đề án 2026 quy định: với ngành xét tuyển tổ hợp thuộc **cả hai nhóm**, điểm chuẩn nhóm
`A00, A01, B00, D07, K01` **cao hơn 0,5 điểm** so với nhóm `D01, D04, DD2`.

Bảng `admission_scores` hiện chỉ lưu **một điểm cho mỗi (ngành, năm, phương thức)**, và
điểm đó là của tổ hợp D01. Hệ quả: 15 ngành trả sai khi người dùng hỏi theo tổ hợp nhóm A.

| Mã | Tổ hợp ngành đó xét | CSV đang trả | Đúng cho nhóm A/K |
|---|---|---|---|
| EM1 | A00, A01, D01, K00, K01 | 24,56 | **25,06** |
| EM2 | A00, A01, D01, K00, K01 | 25,07 | **25,57** |
| EM3 | A00, A01, D01, K00, K01 | 24,12 | **24,62** |
| EM5 | A00, A01, D01, K00, K01 | 24,48 | **24,98** |
| EM-E13 | A01, D01, D07, K00, K01 | 23,38 | **23,88** |
| EM-E14 | A01, D01, D07, K00, K01 | 24,56 | **25,06** |
| EM-E17 | A01, D01, D07, K00, K01 | 20,06 | **20,56** |
| ED2 / ED3 / ED5 | A00, A01, D01, K00, K01 | 23,75 / 23,20 / 23,25 | **+0,5** |
| FL1 / FL2 / FL3 / FL4 | có cả D01 và K01 | 23,00 / 20,75 / 25,50 / 22,98 | **+0,5** |
| TROY-IT | A00, A01, D01, K00, K01 | 24,44 | **24,94** |

Quy tắc +0,5 này **chỉ nằm trong văn bản RAG**, không có trong bảng số. Đây không phải lỗi
transcribe — validator không thể bắt được, vì từng con số đều đúng với nguồn; cái sai là
**mô hình dữ liệu không biểu diễn được chiều "tổ hợp"**.

Bài báo công bố điểm chuẩn 2025 nêu quy tắc tương tự, nên **2025 cũng bị**, nhưng chưa
kiểm được vì 2025 không có bảng tổ hợp theo ngành.

**Ba cách sửa, cần anh chọn:**

| Cách | Việc phải làm | Đánh giá |
|---|---|---|
| Thêm cột `score_group_a` | Mỗi dòng có thêm điểm nhóm A | Nhanh nhất, nhưng nhét 2 sự thật vào 1 dòng |
| Tách dòng theo nhóm tổ hợp | 1 dòng = (ngành, năm, phương thức, **nhóm tổ hợp**) | Đúng mô hình nhất, khớp cách người dùng hỏi; phải sinh thêm ~15 dòng/năm |
| Lưu quy tắc riêng, tính lúc trả lời | Bảng `score_adjustment_rules` | Gọn, nhưng bot phải cộng trừ — trái nguyên tắc "không để LLM tự tính" |

Tôi nghiêng về **cách 2**: câu hỏi thật của học sinh luôn là "khối A00 ngành EM1 bao nhiêu
điểm", nên tổ hợp là một chiều của sự thật, không phải chú thích.

### A2. Cột năm không đồng nhất giữa 3 bảng học phí

| Bảng | Cột năm | Giá trị |
|---|---|---|
| `program_overview_2026` | `year` | `2026` |
| `tuition_by_year` | `academic_year` | `2024-2025` |
| `tuition_credit` | `academic_year` | `2024-2025` |

Hỏi "học phí IT1" sẽ ra 3 câu trả lời khác nhau: 28–40 triệu/năm (2026), 24–30 triệu/năm
(2024-2025), 550 nghìn/tín chỉ (2024-2025). **Theo anh thì khác năm là không sao** — đúng,
nhưng chỉ đúng nếu bot so sánh được năm. Hiện một bảng dùng `year=2026`, hai bảng dùng
`academic_year=2024-2025`: bot lọc `year = 2026` sẽ **âm thầm bỏ mất** hai bảng kia, hoặc
lấy cả vào mà không biết là số của năm khác.

→ Bổ sung vào Phần 4: thống nhất **mọi bảng đều có cột `year`** (năm tuyển sinh, số nguyên),
giữ thêm `academic_year` khi nguồn ghi dạng `2024-2025`.

### A3. Trùng số giữa hai nghĩa khác nhau — ngưỡng GPA

`GPA ≥ 3,6 và điểm rèn luyện ≥ 90` xuất hiện ở **hai chỗ với hai nghĩa khác nhau**:

- Quy định KKHT, Điều 3 → **điều kiện xét học bổng loại A**
- Sổ tay sinh viên 2026, mục 5.3.7 → **điều kiện được cộng điểm rèn luyện**

Con số không mâu thuẫn, nhưng hỏi "điều kiện học bổng loại A" mà retrieval trúng chunk Sổ
tay thì sẽ trích dẫn bảng cộng điểm rèn luyện — trả lời sai ngữ cảnh mà nhìn vào vẫn thấy
"hợp lý". Cách xử lý: ưu tiên `document_type = quy_dinh` cho câu hỏi về học bổng, và giữ
`document_title` trong citation để người đọc tự thấy nguồn là văn bản nào.

## B. Chỗ tôi tự tạo trùng lặp — cần anh quyết

Học phí, thời gian đào tạo, bằng tốt nghiệp của cả 68 ngành đang nằm ở **cả hai tầng**:
`program_overview_2026.csv` và chunk "Thông tin nhanh" trong RAG. Đã đối chiếu: **khớp
100%, không lệch một giá trị nào** (cùng một nguồn bóc ra).

Không mâu thuẫn, nhưng **vi phạm đúng nguyên tắc tôi vừa viết vào PRD mục 3.C** ("bảng số
đi PostgreSQL, văn xuôi đi RAG, không để trùng ở cả hai nơi"). Hai lựa chọn:

1. **Bỏ dòng "Thông tin nhanh" khỏi chunk RAG**, chỉ giữ ở CSV — đúng nguyên tắc, nhưng
   chunk RAG mất ngữ cảnh: đang đọc đoạn giới thiệu ngành mà không thấy học phí/thời gian.
2. **Giữ, và ghi rõ trong PRD rằng đây là ngoại lệ có chủ ý**: RAG giữ bản mô tả để đọc
   hiểu, CSV là nguồn duy nhất được trích dẫn khi trả lời câu hỏi về số.

Tôi nghiêng về **cách 2** nhưng phải nói rõ trong PRD, vì để im thì người làm sau đọc PRD
sẽ thấy dữ liệu trái với nguyên tắc mà không hiểu vì sao.

## C. Điểm chuẩn nằm trong văn bản RAG — 8 chunk

Các bài công bố điểm chuẩn có nhắc số cụ thể trong văn kể: *"IT-E10 có điểm chuẩn cao nhất
là 29,54"*, *"IT1: 29,27"*… Đã đối chiếu: **giá trị khớp CSV**, không mâu thuẫn.

Rủi ro không phải sai số mà là **sai tầng trả lời**: nếu bot lấy số từ RAG thì AC1 (tool
accuracy 100%) bị đi đường tránh, và không có gì bảo đảm số trong văn kể luôn đầy đủ. Xử lý
bằng luật Router, không bằng metadata: **intent hỏi điểm chuẩn thì luôn đi SQL, không bao
giờ lấy số từ RAG**; chunk văn kể chỉ dùng để giải thích cách tính, điểm ưu tiên, nhận xét
phổ điểm.

Ngoài ra bài 2024 có nhắc điểm chuẩn **năm 2023** (83,97 / 29,42) — ngoài phạm vi dataset
2024–2026. Không xoá (nó là một câu trong bài gốc), nhưng phải bảo đảm bot không dùng số
này để trả lời như dữ liệu chính thức, theo đúng US6.

## D. Đo trùng lặp: 15 cặp, 29/573 chunk (5%)

| Cặp trùng | Jaccard | Bản chất | Tách được bằng |
|---|---|---|---|
| Đề án 2025 ↔ 2026, mục "Các phương thức tuyển sinh" | 0,78 | Khác năm, nội dung gần giống | `year` |
| TE3 ↔ TE-EP, ET2 ↔ ET-E5, EV1 ↔ EV2 (cơ hội việc làm) | 0,40–0,80 | Ngành chuẩn và tiên tiến dùng chung mô tả | `program_code` |
| QCDT Điều 15 ↔ Điều 24 (điểm trung bình toàn khóa) | 0,66 | Một cho cử nhân, một cho kỹ sư | `dieu_no` |
| Sổ tay ↔ giới thiệu Trường Kinh tế | 0,36 | Cùng chủ đề, khác tài liệu | `document_type` |

**Kết luận quan trọng:** mức trùng lặp lành — **nhưng nó lành chính vì có metadata tách ra**.
Cặp đề án 2025/2026 giống nhau 78%: hỏi "phương thức tuyển sinh 2026" mà không lọc `year`
thì rất dễ nhận chunk 2025 và trả lời bằng quy định năm cũ. Nghĩa là `year`, `program_code`,
`dieu_no` không phải metadata "cho đẹp" — chúng là thứ duy nhất giữ cho 5% trùng lặp này
không biến thành trả lời sai.

## Bổ sung vào danh sách việc

| Bước | Việc | Ước lượng |
|---|---|---|
| 0 | **Chốt cách biểu diễn điểm chuẩn theo tổ hợp (A1)** rồi sinh lại bảng điểm chuẩn 2026 (và 2025 nếu bóc được tổ hợp) | ~2h sau khi anh chọn |
| 4b | Thống nhất cột `year` cho mọi bảng (A2) | ~0,5h |
| 4c | Quyết định về trùng "Thông tin nhanh" (B) và ghi vào PRD | ~0,5h |

Bước 0 xếp trước tất cả: sai điểm chuẩn là loại lỗi người dùng phát hiện được ngay và mất
lòng tin lập tức, trong khi metadata sai thì còn sửa được âm thầm.

---

# Đã thực hiện (2026-09-24)

## 1. Điểm chuẩn theo tổ hợp — xong, theo cách anh chốt

`admission_scores_2026.csv`: **272 → 287 dòng**. Tổ hợp giờ là một chiều dữ liệu thật:
1 dòng = (ngành, năm, phương thức, **nhóm tổ hợp**). Cột mới:

| Cột | Nội dung |
|---|---|
| `combination_group` | `ky_thuat` / `kinh_te_gd_nn` / rỗng (XTTN, ĐGTD không dùng tổ hợp môn) |
| `subject_combinations` | Các mã tổ hợp của đúng nhóm đó, vd `A00;A01;K01` |
| `score_note` | Câu giải thích cho học sinh, có sẵn trong dữ liệu để bot trích thẳng |

Đối chiếu với 2 ví dụ trong bài công bố chính thức: EM1 `D01 = 24,56` → `K01/A00/A01 = 25,06`;
FL4 `D01;DD2 = 22,98` → `K01 = 23,48`. **Khớp tuyệt đối.**

**Đính chính một chi tiết anh nhắc:** chiều lệch là **nhóm kỹ thuật (A00, A01, B00, D07, K01)
cao hơn** nhóm kinh tế/giáo dục/ngoại ngữ (D01, D04, DD2) 0,5 điểm — không phải khối D cao
hơn khối A. Nội dung `score_note` đã ghi theo chiều đúng.

2025 cũng có quy tắc này (bài công bố 2025 ghi nhóm kỹ thuật gồm thêm A02, D26, D28, D29)
nhưng **chưa áp dụng được vì không có bảng tổ hợp theo ngành của năm 2025** — chỉ 2026 có.
Muốn làm 2025 thì phải bóc tổ hợp từng ngành của năm đó trước.

Validator đã sửa theo: khoá chống trùng thêm `combination_group`, và phép so sánh liên năm
lấy **mức thấp hơn** của ngành có 2 nhóm (đó mới là con số công bố), nếu không sẽ báo lệch giả 0,5 điểm.

## 2. Bảng tổ hợp: phát hiện thiếu mã DD2 nhờ đối chiếu chéo

Viết `verify_subject_combinations.py` bóc tổ hợp từ **68 trang ngành** (nguồn thứ hai, độc
lập với trang accordion đã dùng trước đây). Hai nguồn khớp **292/293 dòng** — lệch đúng một
chỗ: **FL4 thiếu mã DD2**, trong khi đề án 2026 ghi rõ năm 2026 có 8 tổ hợp gồm DD2.

Đã bổ sung DD2 = *Toán, Ngữ văn, Tiếng Hàn* vào cả bảng tổ hợp và bảng tham chiếu. Nhờ vậy
FL4 mới ra đúng `D01;DD2 = 22,98`.

## 3. Học phí 2026 theo ngành — bảng mới `tuition_2026.csv`

68 ngành, tách từ chuỗi chữ trên trang ngành thành số so sánh được: `amount_min`,
`amount_max`, `unit`, `is_approximate`, `terms_per_year`, giữ `amount_text` gốc để citation.
**63 ngành tính /năm, 5 ngành tính /học kỳ** (ET-LUH, ME-LUH, ME-NUT, ME-GU: 24–30 triệu/học
kỳ; TROY-IT: 33 triệu/học kỳ). `terms_per_year` chỉ điền cho TROY-IT (=3, theo đề án 2024),
các chương trình còn lại để trống vì **chưa có nguồn nào ghi số học kỳ/năm** — không đoán.

Đối chiếu với bảng nhóm năm 2024:

| Nhóm | 2024 | 2026 |
|---|---|---|
| Chuẩn | 24–30 tr/năm | 22–40 tr/năm (38 ngành) |
| ELITECH | 33–42 tr/năm | 35–68 tr/năm (22 ngành) |
| IT-E10 / EM-E14 | 64–67 tr/năm | ~68 / ~65 tr/năm |
| IPE (FL2) | 45 tr/năm | 55 tr/năm |

Chênh lệch **không phải mâu thuẫn dữ liệu**: hai bảng khác đơn vị so sánh (2024 là khoảng
chung theo nhóm cho khóa nhập học 2024, 2026 là mức của từng ngành). Riêng mức 22 tr/năm của
2026 thấp hơn sàn 2024 vì đó là ED5 — ngành mới mở, chưa tồn tại năm 2024. Trần tăng 10%/năm
vì vậy **không kiểm được bằng cách so hai khoảng này**; muốn kiểm phải theo dõi cùng một
ngành qua các năm.

Đã thêm cột `year` cho `tuition_by_year`, `tuition_credit`, `subject_combinations_ref` →
**20/20 bảng đều có `year`**, lọc theo năm được (việc 4b trong plan, xong).

## 4. Bug chuẩn hoá tiếng Việt: ký tự "đ" bị xoá

Phát hiện khi dò bộ 120 câu. Hàm chuẩn hoá dùng ở 4 script bỏ dấu bằng NFD rồi lọc
`[^a-z0-9]`. Nhưng **"đ" không phải tổ hợp dấu** nên NFD không tách nó ra, và bước lọc **xoá
luôn ký tự này**:

| Gõ vào | Trước | Sau khi sửa |
|---|---|---|
| Điểm chuẩn | `iem chuan` | `diem chuan` |
| Đăng ký | `ang ky` | `dang ky` |
| Điện tử | `ien tu` | `dien tu` |
| Đa phương tiện | `a phuong tien` | `da phuong tien` |

Hậu quả thật: người dùng gõ **không dấu** — cách gõ phổ biến nhất — sẽ không khớp được gì.
Gõ `dien tu vien thong` trước đây ra rỗng, nay ra `ET1, ET-E4, ET-LUH`. Đây đúng là yêu cầu
"chuẩn hóa dấu tiếng Việt" ở PRD mục 3.B, tức là đang fail một mục scope.

Đã sửa ở `crawl_programs.py`, `build_programs.py`, `validate_aliases.py`, `probe_questions.py`.
`validate_aliases.py` chạy lại: vẫn 0 lỗi 0 cảnh báo.

## 5. Dò bộ 120 câu hỏi của anh

Viết `probe_questions.py`. **Hai lần đầu đều cho kết quả sai, đáng ghi lại để không lặp:**

- Lần 1 đếm từ khoá thô → **119/120 "ĐỦ"**, gồm cả câu về tỷ lệ chọi và giá vé gửi xe vốn
  không có dữ liệu. Nguyên nhân: từ phổ biến ("ngành", "chương trình") khớp bừa.
- Lần 2 khớp theo cụm từ → **0/120 "ĐỦ"**, vì câu hỏi và văn bản diễn đạt khác nhau, khớp
  cụm nguyên văn gần như không bao giờ trúng.

→ **Phép đo tự động theo từ khoá không kết luận được "có trả lời được hay không".** Nó chỉ
dùng để lọc danh sách nghi vấn, còn kết luận phải dò từng chủ đề. Bộ test thật cho AC1–AC9
phải ghi **đáp án mong đợi + chunk_id/dòng CSV nguồn** cho từng câu, không thể tự sinh.

Dò theo chủ đề trên 20 nhóm câu, kết quả:

| Câu | Chủ đề | Kết luận |
|---|---|---|
| **100** | Tỷ lệ sinh viên có việc làm sau tốt nghiệp | **KHÔNG CÓ** dữ liệu |
| **38, 40** | Tỷ lệ chọi, số hồ sơ đăng ký theo ngành | **KHÔNG CÓ** — HUST không công bố số này |
| **59** | Chi phí sinh hoạt quanh trường | Gần như không có; vốn ngoài phạm vi HUST |
| **116** | Giá vé gửi xe theo tháng | Có nhắc chỗ để xe, **không có giá** |
| **119** | Trạm y tế, BHYT | Sổ tay chỉ có dòng mục lục, nội dung mỏng |
| 56 | Vay vốn học tập | **Có** — Sổ tay dẫn QĐ 157/QĐ-TTg và QĐ 29 cho ngành STEM |
| 111–115, 118, 120 | KTX, thư viện, CLB, NCKH, sinh hoạt công dân, tình nguyện | **Có** trong Sổ tay (9–14 chunk mỗi chủ đề) |
| 10, 13, 44, 84, 91, 94, 95, 102 | Hệ số môn chính, SAT/ACT, phổ điểm TSA, chuẩn tiếng Anh, song bằng, bảo lưu, chuyển ngành, thực tập | **Có** |

Tức là trong 120 câu, **5 câu không trả lời được** (100, 38, 40, 59, 116) và 1 câu mỏng (119).
Bốn trong năm câu đó hỏi số liệu **HUST không công bố** hoặc **ngoài phạm vi trường** — nên
cách xử lý đúng là fallback tường minh theo PRD mục 13.2, không phải đi thu thập thêm.
