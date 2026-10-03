# Kế hoạch CRAWL dữ liệu — HUST Info & Admission Assistant

**Phạm vi bản này: chỉ crawl + chuẩn hóa dữ liệu thô → file trung gian (CSV/JSON/Markdown).**
Việc nạp PostgreSQL/Qdrant, embedding, seed script là giai đoạn sau, không nằm trong bản kế hoạch này.

Đối chiếu PRD v1.1 mục 3.C (RAG) và mục 15.1 (schema). Phạm vi tuyển sinh: **2024–2026**.

## 0. Việc đã xong (không lặp lại)

- Phạm vi năm đã chốt 2024–2026, PRD đã cập nhật.
- Học bổng KKHT + cảnh báo/buộc thôi học: xác nhận nằm trong `QCDT_2025...pdf` (Điều 19, 25) và `So tay sinh vien_2026.pdf` — không cần nguồn riêng.
- `So tay sinh vien_2026.pdf`: có text layer thật, extract trực tiếp bằng `pdftotext -enc UTF-8`, không cần OCR.
- `link.md`: đã có đủ link "danh sách ngành đào tạo đại học" (index) cho cả 10 trường/khoa, tự phát hiện bằng cách crawl thử từ trang chủ.
- **Đã xác nhận bảng điểm chuẩn trên trang tin (ts.hust.edu.vn) là ẢNH** (không phải bảng HTML — bảng HTML duy nhất trên trang chỉ là phần chú thích công thức tính điểm), nhưng là ảnh render từ Excel/thiết kế, rõ nét, đọc trực tiếp bằng vision được, không phải ảnh chụp/scan mờ.
- **3 văn bản quy định mới đã bổ sung vào `data/raw/admission/` + link nguồn trong `link.md`**, đã kiểm tra nội dung:
  - `qui-dinh-ve-xttn-nam-2026-ky.pdf` — Quy định phương thức Xét tuyển tài năng, QĐ số 3030/QĐ-ĐHBK, 17/03/2026, "áp dụng từ năm 2026" → **mới nhất, dùng được ngay**.
  - `Quy định HB KKHT năm 2022.pdf` — QĐ số 3258/QĐ-ĐHBK-CTSV, 12/9/2022. File **scan, không có text layer** (0 font nhúng) nhưng đọc trực tiếp bằng vision được đầy đủ, rõ nét. Nội dung (học bổng A/B/C = 1.5/1.2/1 lần học phí, tiêu chuẩn GPA/ĐRL) **khớp với tóm tắt trong Sổ tay sinh viên 2026** → xác nhận vẫn còn hiệu lực, đây là bản đầy đủ (sổ tay chỉ tóm tắt).
  - ~~`03102023-quy-che-thi-tu-duy-dhbkhn.pdf`~~ (818/QĐ-ĐHBK, 03/10/2023) → **XÁC NHẬN ĐÃ LỖI THỜI**. Đã lần theo link "Quy chế thi ĐGTD chi tiết" trên chính trang giới thiệu TSA chính thức, tìm ra bản thay thế: **`10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf`** (Số 10461/QĐ-ĐHBK, ký 23/10/2024, 19 trang, PDF scan — đọc bằng vision, không có text layer). Dùng bản 2024 làm nguồn RAG chính cho quy chế thi TSA; giữ bản 2023 chỉ để tham khảo lịch sử, không ingest.
  - **Trang giới thiệu kỳ thi TSA** (`link.md`, đã thêm cả bản VI + EN) — đã kiểm tra, cả 2 đều hoạt động (200). **Ưu tiên dùng bản tiếng Việt** (`ts.hust.edu.vn/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa`, cập nhật 31-12-2026, nội dung tiếng Việt đầy đủ mô tả 3 năng lực tư duy đánh giá: Toán học, Đọc hiểu, Khoa học/Giải quyết vấn đề) làm nguồn RAG chính; bản EN chỉ dự phòng — khớp phạm vi ngôn ngữ PRD (chỉ tiếng Việt).
- **Kỹ thuật mới xác nhận: PDF không có text layer (scan) vẫn đọc được trực tiếp bằng vision (Read tool xử lý PDF theo từng trang ảnh)** — không bắt buộc phải có OCR engine riêng (PaddleOCR/Vision API) như dự tính ban đầu, chỉ cần khi số lượng file scan lớn (cần tự động hóa hàng loạt) hoặc ảnh quá mờ để đọc bằng mắt/vision.
- ~~Phát hiện trùng file~~ — ĐÃ XONG: `QCDT_2025_5445_QD-DHBK (1).pdf` (giống byte-by-byte 100% bản gốc) đã được xóa.
- Quyết định: **giữ lại** `03102023-quy-che-thi-tu-duy-dhbkhn.pdf` (bản 2023 đã lỗi thời) trong `data/raw/admission/` để tham khảo lịch sử, nhưng **không ingest vào RAG** — chỉ dùng `10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf` làm nguồn chính thức cho quy chế thi TSA.

## TRẠNG THÁI THỰC THI (cập nhật 2026-09-21)

### Đã xong

| Hạng mục | Kết quả |
|---|---|
| Điểm chuẩn 2024 / 2025 / 2026 | `data/processed/admission_scores_{2024,2025,2026}.csv` — 128 / 260 / 272 dòng long-format, **0 lỗi validate** |
| Bảng ngành theo từng năm | `programs_2024.csv` (64 ngành), `programs_2025.csv` (65), `programs_2026.csv` (68) |
| 10 Trường/Khoa | `data/faculty/<code>/gioi_thieu.md` + `info.json` — 10/10 đơn vị, đã lọc sạch link spam cờ bạc |
| Mô tả ngắn từng ngành | `data/programs/<code>.json` — 60 file, 54/68 ngành ghép được trang CTĐT |
| Văn bản quy định → RAG | `data/rag/raw_chunks/`: QCDT 2025 (47 chunk theo Điều), XTTN 2026 (6 chunk), Sổ tay sinh viên 2026 (171 chunk theo mục) — kèm `.chunks.jsonl` có metadata citation |
| Bổ sung dòng FED vào `ma_nganh_truong.md` | Xong |

### Script đã viết (`scripts/`)

- `build_admission_scores.py` — wide (transcribe từ ảnh) → long format
- `build_programs.py` — sinh bảng ngành riêng cho từng năm
- `validate_admission_csv.py` — kiểm tra mã ngành, trùng dòng, điểm ngoài thang, lệch điểm giữa các năm (ngưỡng theo tỉ lệ thang điểm)
- `crawl_faculty.py` — crawl 10 Trường/Khoa, đọc link trực tiếp từ `link.md`
- `crawl_programs.py` — ghép link CTĐT với mã ngành + lấy mô tả ngắn
- `pdf_to_rag_md.py` — PDF → Markdown chunk theo Điều/mục + JSONL metadata

### Phát hiện trong quá trình làm

1. **Mã ngành khác nhau giữa các năm**: `TE-EP`/`TE-E2` (2024–2025) vs `TEEP`/`TEE2` (2026); `EM4` (Kế toán) và `TROY-BA` có ở 2024–2025 nhưng không còn ở 2026. Đã xử lý bằng cách tách bảng ngành theo từng năm.
2. **Bảng điểm chuẩn mỗi năm một định dạng khác**: 2024 chỉ có 2 cột điểm (TSA + THPT), 2025 có 4 cột, 2026 có 4 cột + cột Trường/Khoa. Không dùng chung 1 parser được.
3. **Cảnh báo lệch điểm phải tính theo tỉ lệ thang điểm**: ngưỡng cố định 5 điểm sinh 81 cảnh báo giả (5/100 = 5% là bình thường); đổi sang 1/6 thang điểm còn đúng 1 cảnh báo thật (FL2/DGTD 2025→2026) — đã đối chiếu ảnh gốc, xác nhận là biến động thật.
4. **Trang ts.hust.edu.vn bị chèn link spam cờ bạc** — crawler đã có bộ lọc, kiểm tra lại không file nào trong `data/faculty/` dính spam.

### Cập nhật đợt 2 — đã bóc xong các bảng chỉ tiêu / tổ hợp / học phí

| File mới | Dòng | Nguồn |
|---|---|---|
| `quotas_2025.csv`, `quotas_2026.csv` | 65 + 68 | Bảng HTML thật trên trang đề án tuyển sinh (không phải ảnh) |
| `program_methods_2025.csv`, `program_methods_2026.csv` | 195 + 204 | Cùng bảng trên, long format 1 dòng/(ngành, phương thức) |
| `subject_combinations_ref.csv` | 12 | Đề án 2025 — định nghĩa A00, A01, D01, K00 (TSA), K01... |
| `tuition_credit.csv` | 13 | `2024_2_QĐ học phí` Phụ lục I trang 3, đọc bằng vision |
| `program_aliases.csv` | 4 | Ghi nhận mã ngành viết khác nhau giữa các nguồn chính thức |

**Đối chiếu:** chỉ tiêu 2025 và 2026 khớp 100% với `programs_<năm>.csv` (65/65, 68/68); tổng chỉ tiêu 2026 cộng được đúng **9.880** như bảng gốc ghi.

### Phát hiện đợt 2

1. **Phụ lục 1 của đề án 2024 KHÔNG nằm trong file PDF** — PDF chỉ có phần thân 38 trang, kết thúc ở Bảng 17. Chỉ tiêu chi tiết từng ngành 2024 được dẫn "Xem phụ lục 1" nhưng phụ lục là tài liệu riêng → **vẫn thiếu chỉ tiêu 2024**, cần tìm nguồn khác.
2. **Cùng năm 2026, HUST ghi mã ngành khác nhau giữa 2 nguồn chính thức**: đề án tuyển sinh ghi `TE-EP`/`TE-E2`, còn bảng điểm chuẩn + `ma_nganh_truong.md` ghi `TEEP`/`TEE2`. Đã lập `program_aliases.csv` để chuẩn hoá — đây chính là dữ liệu cho bảng `entity_aliases` trong PRD mục 15.1.
3. **HTML của HUST có lỗi gõ**: mã `CH -E20`, `MI -E22` thừa dấu cách trước gạch nối, khiến 2 ngành (80 chỉ tiêu) bị loại khi parse. Parser đã chuẩn hoá khoảng trắng.
4. **Đề án 2024 (PDF) chứa 17 bảng** gồm cả học phí (Bảng 9-12) và quy đổi chứng chỉ IELTS/VSTEP (Bảng 5-8) — nhiều hơn dự kiến. Học phí ở đây ghi theo **khoảng giá cho cả nhóm** (chuẩn 24-30 tr/năm, Elitech 33-42 tr/năm, song bằng 24-29 tr/**học kỳ**), khác đơn vị với `tuition_credit.csv` (nghìn đồng/tín chỉ) → **bắt buộc giữ cột `unit` riêng**, không được trộn.
5. **Trang học phí trên web không có bảng HTML** (0 thẻ `<tr>`), dữ liệu nằm trong 2 ảnh → phải đọc bằng vision.

### Còn thiếu sau đợt 2

- [ ] Chỉ tiêu 2024 (nằm ở Phụ lục 1, chưa có file)
- [ ] Bảng 5-8 đề án 2024: quy đổi/điểm thưởng chứng chỉ IELTS, VSTEP → rất hay được hỏi
- [ ] Bảng 9-12 đề án 2024: học phí theo nhóm (khoảng giá/năm) — bổ sung cho `tuition_credit.csv`
- [ ] Trang 4 QĐ học phí: học phí chương trình hợp tác quốc tế + học phần ngoại ngữ
- [ ] Học phí từ ảnh trên trang web `hoc-phi-dai-hoc-chinh-quy`
- [ ] Bảng quy đổi chứng chỉ ngoại ngữ 2026 (ảnh `quydoi-cccnn-2026.png` trên trang đề án 2026)

### Cập nhật đợt 3 — chốt mã canonical + bảng quy đổi chứng chỉ

**Chốt mã ngành canonical: `TE-EP` / `TE-E2` (có gạch nối).** Căn cứ đối chiếu toàn bộ nguồn:

| Nguồn | 2024 | 2025 | 2026 |
|---|---|---|---|
| Bảng điểm chuẩn | TE-EP, TE-E2 | TE-EP, TE-E2 | **TEEP, TEE2** |
| Đề án tuyển sinh | TE-EP, TE-E2 | TE-EP, TE-E2 | TE-EP, TE-E2 |
| ma_nganh_truong.md | — | — | TEEP, TEE2 |

5/7 nguồn dùng dạng có gạch nối; đề án tuyển sinh cả 3 năm đều dùng dạng này; đúng quy ước chung của mọi mã khác (`IT-E10`, `EE-E8`, `ME-E1`...). Dạng `TEEP`/`TEE2` chỉ có ở ảnh điểm chuẩn 2026 và file chép lại từ ảnh đó.

**Hệ quả đã sửa được:** trước đó so sánh xuyên năm bị đứt ở 2026 — bot không trả lời được "điểm chuẩn ngành này 3 năm gần đây". Sau chuẩn hoá: TE-E2 THPT = 25.90 (2024) → 25.18 (2025) → 26.38 (2026).

Đã thêm `scripts/aliases.py` dùng chung cho mọi script build, alias ghi trong `program_aliases.csv`.

**Bảng quy đổi chứng chỉ ngoại ngữ — 2 bảng RIÊNG vì trả lời 2 câu hỏi khác nhau:**

| File | Dòng | Nội dung |
|---|---|---|
| `cert_bonus_conversion.csv` | 122 | Điểm thưởng + điểm quy đổi thang 10. 2024: IELTS/VSTEP (Bảng 5-8 PDF). 2026: **24 loại chứng chỉ** (IELTS, VSTEP, TOEIC 4 kỹ năng, TOEFL, DELF/DALF, JLPT, HSK, TOPIK, TestDaF...) |
| `cert_cefr_equivalence.csv` | 47 | Tương đương khung KNLNN VN (Bậc 3-6) / CEFR (B1-C2) — bảng của đề án 2025, **khác loại** với bảng điểm thưởng |

Lưu ý phát hiện: **mức quy đổi VSTEP đổi giữa 2024 và 2026** (2024: 7,0 được +3; 2026: 7.0-7.5 mới được +3, và mốc thấp nhất nâng từ 5,0 lên 5.5) → bắt buộc tách theo năm, không dùng chung một bảng.

### ✅ Quy chế thi TSA 2024 đã vào RAG (19 trang scan, đọc bằng vision)

`10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf` — PDF scan thuần (PyMuPDF đọc ra 0 ký tự,
9 ảnh/trang), không script hoá được nên đọc vision từng trang.

- Transcript gốc: `data/raw/tsa_quyche/transcript/*.md` — 53.421 ký tự
- Chunk RAG: `data/rag/raw_chunks/tsa_quyche.chunks.jsonl` — **35 chunk, đủ Điều 1–35, 8 chương I–VIII**
- Script tái sử dụng: `scripts/scan_md_to_rag.py` (dùng lại được cho KKHT 2022 và các PDF scan sau)

Nội dung có giá trị cho chatbot (trước đây hoàn toàn thiếu):
- Điều 4: bài thi gồm 3 phần (Tư duy Toán học, Đọc hiểu, Khoa học/Giải quyết vấn đề), thi trắc nghiệm trên máy tính
- Điều 13: đối tượng dự thi; **không được dự thi quá 01 lần trong 30 ngày**
- Điều 14: đăng ký tại https://tsa.hust.edu.vn
- Điều 15: vật dụng được mang vào phòng thi; **đến chậm quá 15 phút không được dự thi**
- Điều 23: 3 loại giấy tờ tùy thân được chấp nhận
- Điều 25: **gián đoạn quá 15 phút thì dừng kíp thi**
- Điều 29: giấy chứng nhận kết quả ký số, miễn phí; bản in giấy mất phí
- Điều 31: khiển trách trừ 25% điểm, cảnh cáo trừ 50%, đình chỉ hủy kết quả, cấm thi 02 năm

Ghi chú kỹ thuật: nội dung nhiều Điều trải dài qua nhiều trang scan nên transcript có
các mục "(tiếp)"; script tự gộp về đúng Điều gốc (41 chunk thô → 35 chunk sau gộp).

## KIỂM TRA CUỐI — còn thiếu những gì (2026-09-21)

### Độ phủ dữ liệu 68 ngành năm 2026

| Loại dữ liệu | Phủ |
|---|---|
| Điểm chuẩn | **68/68 (100%)** |
| Chỉ tiêu | **68/68 (100%)** |
| Phương thức xét tuyển | **68/68 (100%)** |
| Nhóm chương trình (để tra học phí) | **68/68 (100%)** |
| Mô tả ngắn | 56/68 (82%) |
| Link CTĐT | 60/68 (88%) |

12 ngành còn thiếu mô tả/CTĐT: TE2, TE-EP, TE-E2, BF1, CH-E20, CH-E11, BF-E12, BF-E19, MS2, MS-E3, MS5, TX1, TROY-IT.

### Link trong link.md: 50/59 đã dùng, 9 chưa

| Link chưa dùng | Lý do |
|---|---|
| `drive.google.com/.../quy chế TSA 2024` | Đã tải thành PDF local, chờ Đợt 2 (scan → vision) |
| `fami.../bo-mon-toan-ung-dung`, `fami.../n-3` | Trang cán bộ phụ — crawler mới lấy trang đầu |
| `sofl.../danh-muc-can-bo5,6,7` | Như trên |
| `ts.hust.edu.vn/en/p/faqs` | FAQ chỉ có bản EN, bản VI lỗi 500 |
| `ts.hust.edu.vn/en/tin-tuc/cam-nang...` | Đã thay bằng bản VI cùng nội dung |
| `ts.hust.edu.vn/tin-tuc/hoc-phi-dai-hoc-chinh-quy` | Dữ liệu nằm trong 2 ảnh, chưa đọc |

### Danh sách việc còn lại, theo mức độ quan trọng

**Quan trọng (ảnh hưởng câu trả lời của bot):**
1. Quy chế thi TSA 2024 — 19 trang scan, chưa vào RAG
2. Chỉ tiêu 2024 — nằm ở Phụ lục 1 không có trong file, **cần hỏi Ban Tuyển sinh**
3. Học phí từ 2 ảnh trên web + trang 4 QĐ học phí (hợp tác quốc tế, học phần ngoại ngữ)
4. Học phí theo nhóm từ Bảng 9-12 đề án 2024 (khoảng giá/năm và /học kỳ)

**Trung bình:**
5. 12 ngành thiếu mô tả ngắn / link CTĐT
6. Quy định HB KKHT 2022 — 2 trang scan, chưa vào RAG (nội dung đã có bản tóm tắt trong Sổ tay)
7. Danh sách bộ môn (`departments`) — HTML cán bộ đã tải sẵn, chưa parse; còn 5 trang cán bộ phụ chưa crawl

**Thấp:**
8. FAQ tuyển sinh — chờ HUST sửa lỗi 500 ở bản tiếng Việt

### Lỗi nhất quán đã phát hiện và sửa trong lần kiểm tra này

Đổi mã canonical `TEEP → TE-EP` đã áp dụng cho các script build nhưng **bỏ sót thư mục `data/programs/`** — file vẫn tên `TEEP.json` nên báo cáo độ phủ tưởng ngành này thiếu CTĐT. Đã chuẩn hoá lại tên file và trường `program_code` bên trong.

### ✅ Đợt 1 ĐÃ XONG — RAG tăng từ 300 lên 359 chunk

| Nguồn mới | Chunk | Ký tự |
|---|---:|---:|
| `de_an_tuyen_sinh_2024` | 33 | 24.522 |
| `de_an_tuyen_sinh_2026` | 8 | 8.626 |
| `de_an_tuyen_sinh_2025` | 7 | 6.969 |
| `tsa_pages` (giới thiệu TSA + cẩm nang 2026) | 10 | 12.601 |

**Tổng RAG hiện tại: 359 chunk / ~295.000 ký tự** từ 8 nguồn.

Script mới: `de_an_to_rag.py`, `crawl_pages.py`.

**3 vấn đề gặp và cách xử lý:**

1. **Bảng lẫn vào chunk** — đề án đánh số mục (1.4., 2.3.) trùng dạng với dòng bảng (1.1, 6.7 kèm số liệu). Giải: bộ lọc `looks_like_table_row` (≥3 cụm số thì không phải tiêu đề) + bỏ toàn bộ vùng sau "Bảng N -" và xoá thẻ `<table>` khi parse HTML. Kiểm chứng: 0 dòng bảng lọt vào cả 3 file.
2. **Mục ngắn bị mất** — các mục như "1.2. Phạm vi tuyển sinh: Toàn quốc", "1.4. Tổng chỉ tiêu dự kiến: 9260" dưới ngưỡng 200 ký tự nên bị loại. Giải: gộp vào mục kế tiếp thay vì bỏ. Đã kiểm chứng 3 dữ kiện này đều còn trong chunk.
3. **Crawl TSA lấy nhầm sidebar** — chọn container "nhiều chữ nhất" nên dính cả danh sách tin liên quan (kèm số lượt xem). Giải: ưu tiên container cụ thể `<div class="description">` trước, chỉ lùi về regex rộng khi không có.

**Ghi chú kỹ thuật:** `ts.hust.edu.vn` không gửi đủ chuỗi chứng chỉ trung gian → `requests` báo `CERTIFICATE_VERIFY_FAILED` dù `curl` verify được. Đã dùng curl làm fallback thay vì tắt `verify` — không hạ thấp bảo mật.

## GIAI ĐOẠN 3 — Kế hoạch xử lý dữ liệu tiếp theo

Hiện trạng: **300 chunk RAG** (4 nguồn) + **15 file CSV / 1.587 dòng** structured. Còn 5 nguồn chưa chunk và một số bảng chưa bóc.

### Đợt 1 — Hoàn tất RAG phần tự động hoá được (≈88.000 ký tự)

Đây là phần làm được bằng script, không cần đọc thủ công.

| Việc | Nguồn | Script | Đầu ra |
|---|---|---|---|
| 1.1 Đề án tuyển sinh 2024 | PDF 61.081 ký tự, có text layer | `de_an_to_rag.py` | `data/rag/raw_chunks/de_an_tuyen_sinh_2024.*` |
| 1.2 Đề án 2025 + 2026 | HTML đã tải sẵn ở `data/raw/de_an/` (14.297 + 13.390 ký tự) | cùng script trên | `de_an_tuyen_sinh_{2025,2026}.*` |
| 1.3 Trang TSA | Giới thiệu kỳ thi (bản **tiếng Việt**) + Cẩm nang TSA 2026 | `crawl_pages.py` (tách module bóc nội dung từ `crawl_faculty.py`) | `data/rag/raw_chunks/tsa_gioi_thieu.*` |

Cách chunk cho đề án: **không có cấu trúc Điều**, dùng chunker theo tiêu đề mục (đã có sẵn `chunk_by_heading`), nhưng phải **loại bỏ phần bảng** đã bóc sang CSV ở Giai đoạn 2 — tránh cùng một bảng vừa nằm trong Postgres vừa nằm trong vector DB, vì bot sẽ trả lời hai đằng khác nhau.

### Đợt 2 — 21 trang PDF scan (nút thắt duy nhất, phải đọc bằng vision)

| Tài liệu | Trang | Cách làm |
|---|---:|---|
| Quy chế thi TSA 2024 (10461/QĐ-ĐHBK) | 19 | Render PyMuPDF 170dpi → đọc **từng lô 4-5 trang** → gõ lại Markdown theo Điều → đưa qua pipeline metadata sẵn có |
| Quy định HB KKHT 2022 (3258/QĐ-ĐHBK-CTSV) | 2 | Cùng quy trình, 1 lô |

Viết `scripts/scan_pdf_to_md.py` để quy trình lặp lại được. Kiểm soát chất lượng bắt buộc: đếm số Điều đọc được so với mục lục văn bản; spot-check các con số (mức điểm, thời hạn, tỉ lệ). Đánh `verification_status = vision_extracted` cho tới khi có người đối chiếu.

### Đợt 3 — Hoàn tất dữ liệu bảng còn thiếu

| Việc | Ghi chú |
|---|---|
| 3.1 Học phí theo nhóm chương trình | Bảng 9-12 đề án 2024 (khoảng giá triệu đồng/**năm** và /**học kỳ**) → `tuition_program_group.csv`. **Bắt buộc giữ cột `unit` riêng** — trộn với `tuition_credit.csv` (nghìn đồng/tín chỉ) sẽ lệch cả chục lần |
| 3.2 Học phí CT hợp tác quốc tế + học phần ngoại ngữ | Trang 4 QĐ học phí — bổ sung vào `tuition_credit.csv` |
| 3.3 Học phí trên web | 2 ảnh ở trang `hoc-phi-dai-hoc-chinh-quy`, đọc bằng vision |
| 3.4 Chỉ tiêu 2024 | **Đang thiếu nguồn** — nằm ở Phụ lục 1 không có trong PDF. Cần hỏi Ban Tuyển sinh hoặc tìm bản công bố riêng |
| 3.5 14 ngành thiếu link CTĐT | Thêm mục `# link CTĐT theo mã ngành` dạng `MÃ \| URL` vào `link.md`, cho `crawl_programs.py` đọc override trước khi chạy thuật toán ghép |
| 3.6 3 ngành mô tả rỗng (BF1, MS2, TX1) | Nới quy tắc bóc: thử `<div>` nội dung và `<meta name="description">` khi không có `<p>` đủ dài |
| 3.7 Danh sách bộ môn | Parse `data/raw/faculty/<code>/can_bo.html` (đã tải sẵn, **không cần crawl lại**) → field `departments` trong `info.json` |

### Đợt 4 — Kiểm định trước khi embed

| Việc | Vì sao cần |
|---|---|
| 4.1 `normalize_chunks.py` | Gộp mọi `*.chunks.jsonl` về **một schema thống nhất** đúng tên field PRD mục 11.3: `document_title, document_type, year, article_no (=dieu_no), section (=chuong/heading), page_no, source_url`. Hiện mỗi nguồn hơi khác nhau (chunk giới thiệu có `faculty_code`, chunk quy chế có `chuong/dieu_no`) |
| 4.2 `validate_tables.py` | Validate cho `quotas_*`, `cert_*`, `tuition_*` giống `validate_admission_csv.py` đã có: mã ngành tồn tại, không trùng, số trong khoảng hợp lệ, tổng chỉ tiêu khớp con số công bố |
| 4.3 `coverage_report.py` | Bảng phủ theo từng ngành: điểm chuẩn / chỉ tiêu / tổ hợp / học phí / mô tả ngắn / CTĐT. Đây là cách trả lời khách quan câu "dữ liệu đã đủ chưa" thay vì cảm tính |
| 4.4 Spot-check thủ công | Chọn ngẫu nhiên ~20 dòng điểm chuẩn + 10 chunk quy chế, đối chiếu tận nguồn gốc, rồi mới đổi `verification_status` sang `manual_verified` |

### Thứ tự đề nghị

**Đợt 1 → Đợt 3 (mục 3.5–3.7) → Đợt 2 → Đợt 3 (còn lại) → Đợt 4.**

Lý do xếp 3.5–3.7 lên sớm: đó là phần dở dang của dữ liệu đã crawl, làm nhanh và gọn được backlog; còn Đợt 2 (21 trang scan) tốn công nhất nên để sau khi các phần tự động đã xong. Đợt 4 chạy cuối, nhưng `coverage_report.py` nên viết sớm để đo tiến độ sau mỗi đợt.

## GIAI ĐOẠN 2 — Kế hoạch cho phần còn lại

Nguyên tắc chung giữ nguyên từ Giai đoạn 1: **bảng số liệu → CSV long-format**, **văn bản → Markdown chunk + JSONL metadata**, mọi thứ đều có `source_url` + `collection_date` + `verification_status`.

### A. Đề án tuyển sinh — ưu tiên cao nhất (phần thiếu lớn nhất hiện nay)

Đây là tài liệu chứa *phương thức xét tuyển, điều kiện, đối tượng, cách tính điểm, chỉ tiêu, tổ hợp môn* — tức là phần trả lời phần lớn câu hỏi của thí sinh, hiện chưa lấy gì cả.

Nguồn: `Đề án tuyển sinh 2024 -FINAL.pdf` (local) · [đề án 2025](https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025) · [đề án 2026](https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026)

Tách làm **2 luồng riêng** vì bản chất dữ liệu khác nhau:

**A1. Phần văn bản → RAG** (`data/rag/raw_chunks/de_an_tuyen_sinh_<năm>.md` + `.chunks.jsonl`)
- PDF 2024: kiểm tra text layer trước (`pdftotext`), nếu có thì chunk theo mục/phần; nếu scan thì đi đường vision như mục B.
- Web 2025/2026: mở rộng crawler, bóc phần nội dung chính, bỏ menu/spam, chunk theo thẻ heading của trang.
- Metadata mỗi chunk: `document_title, document_type="de_an_tuyen_sinh", year, section, page_no (nếu từ PDF), source_url`.

**A2. Phần bảng → CSV** (2 bảng mới, tách riêng vì quan hệ dữ liệu khác nhau)

| File | Cột | Vì sao tách riêng |
|---|---|---|
| `data/processed/quotas_<năm>.csv` | `program_code, year, method_code, quota, quota_type, source_url, collection_date, verification_status` | Chỉ tiêu có thể ghi theo tổng ngành hoặc chia theo từng phương thức → cần `method_code` + `quota_type` để phân biệt, tránh cộng nhầm |
| `data/processed/subject_combinations_<năm>.csv` | `program_code, year, combination_code, is_primary, source_url, ...` | **1 ngành có nhiều tổ hợp** (A00, A01, D01...). Nếu nhồi vào 1 ô text thì không trả lời được câu "ngành nào xét tổ hợp A01?" — tách 1 dòng/tổ hợp thì chỉ cần `WHERE combination_code='A01'` |

Lưu ý: cột `subject_combination` trong `admission_scores_*.csv` hiện chỉ là **tổ hợp gốc dùng để quy đổi điểm** (A00/D01), KHÔNG phải danh sách tổ hợp xét tuyển đầy đủ. Sau khi có `subject_combinations_*.csv` thì đổi tên cột cũ thành `base_combination` để tránh chatbot trả lời nhầm.

Bảng dạng ảnh → đọc bằng vision như Giai đoạn 1; bảng HTML → parse trực tiếp. Validate bằng script tương tự `validate_admission_csv.py`: mã ngành phải có trong `programs_<năm>.csv`, chỉ tiêu > 0, tổng chỉ tiêu các phương thức không vượt tổng ngành.

### B. 2 PDF scan → RAG (chưa có text layer nên script hiện tại bỏ qua)

| File | Số trang | Cách làm |
|---|---|---|
| `Quy định HB KKHT năm 2022.pdf` | 2 (7 Điều) | Render trang → đọc vision → gõ lại Markdown theo Điều |
| `10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf` | 19 | Chia lô 4–5 trang/lần, cùng quy trình |

Đã có sẵn công cụ: PyMuPDF (đã cài ở Giai đoạn 1) render trang → PNG 200dpi → đọc.
Kiểm soát chất lượng bắt buộc: đếm số Điều đọc được so với mục lục của chính văn bản; spot-check các con số quan trọng (mức điểm, tỉ lệ, thời hạn). Đánh `verification_status = vision_extracted` cho tới khi có người đối chiếu.

Viết `scripts/scan_pdf_to_md.py` để quy trình này lặp lại được, không phải làm thủ công mỗi lần.

### C. Trang web tuyển sinh ngoài nhóm Trường/Khoa

`crawl_faculty.py` hiện chỉ chạy trên 10 đơn vị. Tách phần bóc nội dung thành module dùng chung rồi viết `scripts/crawl_pages.py` cho nhóm link tuyển sinh trong `link.md`:
- Giới thiệu kỳ thi TSA (**bản tiếng Việt**, không dùng bản EN)
- Cẩm nang thi TSA 2026
- FAQ tuyển sinh — hiện chỉ sống bản EN (`/en/p/faqs`), bản VI `/p/hoi-dap` đang lỗi 500. Thêm bước health-check: nếu bản VI trả 200 thì crawl VI, không thì ghi nhận đang thiếu, **không dịch bản EN** để tránh sai lệch nội dung quy chế.

### D. Học phí

| Nguồn | Đầu ra | Ghi chú |
|---|---|---|
| `2024_2_ QĐ học phí - 2024-2025.pdf` | `data/processed/tuition_credit.csv` | Học phí theo tín chỉ, theo nhóm chương trình |
| [Học phí các ngành](https://ts.hust.edu.vn/tin-tuc/hoc-phi-dai-hoc-chinh-quy) | `data/processed/tuition_program.csv` | Kiểm tra bảng HTML hay ảnh trước khi chọn cách bóc |

Schema thống nhất: `program_code (hoặc program_group), academic_year, amount, unit ("đồng/tín chỉ" | "đồng/năm" | "đồng/khóa"), note, source_url, collection_date, verification_status`.
Tách `unit` thành cột riêng là bắt buộc — trộn "đồng/tín chỉ" với "đồng/năm" trong một cột số sẽ khiến bot trả lời lệch cả chục lần.

### E. Hoàn thiện phần ngành & khoa còn dở

1. **14 ngành chưa ghép được trang CTĐT** (ME1, TE2, HE1, TEE2, CH1, BF2, EV1, CH-E20, CH-E11, BF-E12, BF-E19, MS-E3, MS5, TROY-IT): thêm mục `# link CTĐT theo mã ngành` vào `link.md` dạng `MÃ | URL`, cho `crawl_programs.py` đọc phần override này trước khi chạy thuật toán ghép tự động.
2. **3 ngành mô tả rỗng** (BF1, MS2, TX1): nới quy tắc lấy mô tả — thử `<div>` nội dung và `<meta name="description">` khi không có thẻ `<p>` nào đủ dài.
3. **Danh sách bộ môn**: parse `data/raw/faculty/<code>/can_bo.html` (đã tải sẵn, không cần crawl lại) → thêm field `departments` vào `info.json`. Mỗi site một cấu trúc nên làm theo từng site, ưu tiên các site có menu bộ môn rõ ràng.

### F. Báo cáo độ phủ dữ liệu — cách trả lời khách quan câu "đã đầy đủ chưa"

Viết `scripts/coverage_report.py`: với mỗi ngành trong `programs_<năm>.csv`, kiểm tra có đủ hay không:

```text
program_code | điểm chuẩn | chỉ tiêu | tổ hợp | học phí | mô tả ngắn | curriculum_url
```

Xuất bảng Markdown + tỉ lệ phủ từng cột. Đây là thước đo để biết khi nào dữ liệu đủ dùng, thay vì cảm tính — và cũng là cơ sở để quyết định ngành nào cần bổ sung thủ công.

### Thứ tự đề xuất

1. **A** (đề án tuyển sinh) — thiếu nhiều nhất, giá trị cao nhất
2. **D** (học phí) — câu hỏi phổ biến, khối lượng nhỏ
3. **B** (2 PDF scan) — hoàn thiện bộ tài liệu quy chế
4. **E** (ngành & bộ môn còn dở)
5. **C** (web TSA/FAQ)
6. **F** (coverage report) — chạy sau mỗi bước để đo tiến độ

## 1. Cách xử lý DỮ LIỆU BẢNG để chatbot truy xuất dễ nhất

Đây là phần quan trọng nhất vì sai ở đây = hỏng AC1 (Admission Accuracy) và AC5 (No Hallucination).

### Nguyên tắc: Long format (tidy data), không lưu bảng thô

Bảng gốc (cả trong ảnh lẫn PDF đề án) là dạng **wide** — mỗi ngành 1 hàng, mỗi phương thức 1 cột (VD ảnh điểm chuẩn 2025 có 4 cột điểm: THPT/thang 30, XTTN 1.2/thang 100, XTTN 1.3/thang 100, ĐGTD/thang 100). Dạng này dễ đọc cho người nhưng **xấu cho truy vấn** — bot phải "hiểu" cấu trúc cột mỗi lần.

→ Ngay khi crawl xong, chuyển mỗi bảng wide thành **long format**: 1 hàng = 1 tổ hợp (program_code, year, method_code). Đây cũng chính là format của bảng `admission_scores` trong PRD mục 15.1, nên sau này nạp DB gần như copy thẳng, không cần biến đổi lại.

Ví dụ transform từ ảnh điểm chuẩn 2025 (STT 2 — IT1):

| program_code | program_name | year | method_code | scale | score | subject_combination | source_url | collection_date | verification_status |
|---|---|---|---|---|---|---|---|---|---|
| IT1 | CNTT: Khoa học Máy tính | 2025 | THPT | 30 | 29.19 | A00 | ts.hust.edu.vn/... | 2026-09-21 | vision_extracted |
| IT1 | CNTT: Khoa học Máy tính | 2025 | XTTN_1.2 | 100 | 90.61 | A00 | ts.hust.edu.vn/... | 2026-09-21 | vision_extracted |
| IT1 | CNTT: Khoa học Máy tính | 2025 | XTTN_1.3 | 100 | 93.92 | A00 | ts.hust.edu.vn/... | 2026-09-21 | vision_extracted |
| IT1 | CNTT: Khoa học Máy tính | 2025 | DGTD | 100 | 83.39 | A00 | ts.hust.edu.vn/... | 2026-09-21 | vision_extracted |

Lý do dùng đúng 10 cột này:
- **`program_code`/`method_code` là mã, không phải tên** — khớp thẳng với `ma_nganh_truong.md` và bảng `admission_methods`, nên câu SQL của Admission Tool (PRD mục 10.2) là `WHERE program_code IN (...) AND year IN (...) AND method_code IN (...)` — index lookup thuần túy, không cần LLM suy luận trên bảng.
- **`scale` tách riêng khỏi `score`** — đúng pain point persona 5.1 (nhầm thang 30/100); bot luôn biết trả lời kèm thang điểm mà không cần đoán.
- **`subject_combination`** giữ ở granularity đúng: đề tuyển sinh nhóm theo khối "Tổ hợp gốc" (A00, D01...) áp dụng cho *nhiều* ngành cùng lúc — copy lặp lại xuống từng hàng ngành thay vì để bot tự tra bảng khác lúc trả lời.
- **`source_url`, `collection_date`, `verification_status`** — bắt buộc theo PRD mục 26 (data versioning); `verification_status` phân biệt `vision_extracted` (tôi đọc trực tiếp từ ảnh) và `manual_verified` (đã đối chiếu người) — bot/nhà phát triển biết mức tin cậy của từng dòng trước khi coi là nguồn chính thức.

### Cách trích xuất bảng ảnh — dùng vision trực tiếp, không cần OCR engine riêng

Đã thử nghiệm thật với ảnh điểm chuẩn 2025 (`bka1.jpg`, `bka2.jpg`): ảnh render rõ nét (không phải ảnh chụp), tôi đọc trực tiếp bằng khả năng vision và transcribe chính xác từng ô — **không cần PaddleOCR/Vision API riêng** như dự tính ban đầu. Quy trình mỗi bảng:
1. Tải ảnh về `data/raw/<nguồn>/<tên_ảnh>`.
2. Đọc ảnh trực tiếp, transcribe toàn bộ bảng thành CSV long-format theo đúng schema trên.
3. Chạy script validate (mục 2) để bắt lỗi transcribe trước khi đánh dấu xong — **không tự động tin 100% dù không dùng OCR**, vì vẫn là đọc thủ công/bán tự động.
4. Nếu ảnh mờ/độ phân giải thấp (khác với trường hợp đã thấy) → mới cần fallback OCR engine hoặc nhập tay đối chiếu PDF gốc.

### Script validate bắt buộc trước khi coi 1 bảng là "sẵn sàng dùng"

Viết 1 script Python nhỏ (`validate_admission_csv.py`) chạy trên mỗi file CSV long-format, kiểm tra:
- Mọi `program_code` phải tồn tại trong `ma_nganh_truong.md` (bắt lỗi gõ nhầm mã ngành).
- Không có cặp `(program_code, year, method_code)` trùng lặp.
- `score` nằm trong khoảng hợp lệ theo `scale` (0–30 hoặc 0–100).
- Đủ số dòng = (số ngành trong ảnh) × (số phương thức có cột điểm) — lệch số dòng nghĩa là transcribe thiếu.
- Cảnh báo (không chặn) nếu điểm năm sau thấp bất thường so với năm trước cùng ngành/phương thức (>5 điểm lệch) — để soát lại bằng mắt.

### Áp dụng tương tự cho các bảng khác
- **Chỉ tiêu, tổ hợp môn trong đề án tuyển sinh (PDF 2024, ảnh/HTML 2025-2026)** → cùng nguyên tắc long format: `program_code, year, quota, subject_combination_list`.
- **Học phí theo ngành/tín chỉ** → long format: `program_code (hoặc nhóm ngành), year, tuition_per_credit, tuition_per_year`.
- **Mã ngành (`ma_nganh_truong.md`)** → đã đúng dạng long sẵn (1 dòng/ngành), chỉ cần convert Markdown table → CSV, không cần transform thêm.

## 2. Crawl nội dung không phải bảng (RAG / structured text)

**Nhóm A — Trang tin đề án tuyển sinh 2025/2026** (ngoài bảng điểm/chỉ tiêu):
- Lấy phần văn bản mô tả phương thức xét tuyển, điều kiện, mốc thời gian → lưu Markdown sạch (bỏ HTML/CSS rác) → nguồn RAG.

**Nhóm B — Trang giới thiệu + danh sách ngành + cán bộ của 10 trường/khoa** (đã có đủ link trong `link.md`):
- Trang giới thiệu → đoạn mô tả ngắn, địa chỉ, liên hệ → `data/faculty/<code>/gioi_thieu.md` + tách riêng các field có cấu trúc (địa chỉ, liên hệ) vào `data/faculty/<code>/info.json`.
- Trang danh sách ngành đào tạo đại học (index) → follow từng ngành → mô tả ngắn 1-2 câu (rút gọn từ đoạn giới thiệu chương trình) + giữ nguyên `curriculum_url` trỏ về trang gốc → `data/programs/<code>.json` (`program_code, short_description, curriculum_url, faculty_code`).
- Trang cán bộ → chỉ trích danh sách tên bộ môn (không lưu từng giảng viên) → field `departments` trong `info.json`.
- Link web chính thức của trường → field `official_channel_url` trong `info.json`.

## 3. Quy ước lưu file (để bước nạp DB sau này không phải đoán cấu trúc)

```text
data/
  raw/                      # bản gốc chưa xử lý — HTML, ảnh — để truy vết nguồn
    admission_scores/2025/bka1.jpg, bka2.jpg, ...
    admission_scores/2025/page.html
    faculty/<code>/gioi_thieu.html
  processed/
    admission_scores_2024.csv   # long format, đúng schema mục 1
    admission_scores_2025.csv
    admission_scores_2026.csv
    tuition.csv
    programs.csv                 # từ ma_nganh_truong.md
  faculty/<code>/
    info.json                    # address, contact_info, departments, official_channel_url
    gioi_thieu.md                 # nội dung RAG (nếu cần trích dẫn mô tả dài)
  programs/<code>.json           # short_description, curriculum_url, faculty_code
```

## 4. Việc cần làm, theo thứ tự ưu tiên

1. Transcribe bảng điểm chuẩn 2025 (2 ảnh đã tải) → `data/processed/admission_scores_2025.csv` + chạy validate.
2. Crawl trang điểm chuẩn 2024 (ảnh, nếu có) và 2026 (đã crawl được chưa, tùy bài đã đăng) → cùng quy trình.
3. Crawl 10 trang giới thiệu + 10 trang danh sách ngành (link đã có) → `data/faculty/` và `data/programs/`.
4. Crawl bảng chỉ tiêu/tổ hợp môn trong đề án 2025/2026 (web) — kiểm tra định dạng ảnh hay HTML trước khi chọn cách trích.
5. Bổ sung dòng FED vào bảng viết tắt `ma_nganh_truong.md`.
6. Extract + chunk 4 văn bản quy định (XTTN 2026, KKHT 2022, Quy chế thi TSA 2024, QCDT 2025) theo Điều/Khoản, gắn metadata → nguồn RAG.
7. ~~Xác minh Quy chế thi TSA 2023 còn hiệu lực~~ — ĐÃ XONG: lỗi thời, đã thay bằng bản 10461/QĐ-ĐHBK/2024.
8. ~~Xóa file trùng `QCDT_2025_5445_QD-DHBK (1).pdf`~~ — ĐÃ XONG (bạn đã xóa).

## Bảng tài liệu PDF cần xử lý (cập nhật đầy đủ)

| File | Loại | Text layer? | Đích đến |
|---|---|---|---|
| `QCDT_2025_5445_QD-DHBK.pdf` | Quy chế đào tạo | Có | RAG |
| `So tay sinh vien_2026.pdf` | Sổ tay sinh viên | Có | RAG |
| `Đề án tuyển sinh 2024 -FINAL.pdf` | Đề án tuyển sinh | Có | `admission_scores`/`programs` + RAG |
| `2024_2_ QĐ học phí - 2024-2025.pdf` | Học phí tín chỉ | Có | Structured |
| `qui-dinh-ve-xttn-nam-2026-ky.pdf` | Quy định XTTN 2026 | Có | RAG |
| `Quy định HB KKHT năm 2022.pdf` | Quy định học bổng KKHT | **Không (scan)** — đọc bằng vision | RAG |
| ~~`03102023-quy-che-thi-tu-duy-dhbkhn.pdf`~~ | Quy chế thi TSA (2023, đã lỗi thời) | — | **Giữ lại file, không ingest** — chỉ lưu tham khảo lịch sử |
| `10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf` | Quy chế thi TSA (bản hiện hành) | Không (scan) — đọc bằng vision | RAG |
| `ma_nganh_truong.md` | Mã ngành | — | `programs`, `faculties` |

## Công cụ
- Vision (đọc ảnh trực tiếp) cho bảng điểm/chỉ tiêu dạng ảnh — không cần OCR engine riêng trừ khi ảnh mờ.
- `pdftotext -enc UTF-8` (đã có sẵn) cho PDF có text layer (QCDT, Sổ tay, đề án 2024).
- `curl`/`httpx` + regex hoặc BeautifulSoup cho crawl HTML.
- `pandas` để build/validate CSV long-format.
