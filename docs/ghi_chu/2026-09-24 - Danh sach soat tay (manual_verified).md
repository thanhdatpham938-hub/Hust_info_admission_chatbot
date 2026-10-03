# Danh sách bản ghi cần soát tay

**Ngày:** 2026-09-24 · Gắn với PRD v1.2 mục 26

## `manual_verified` nghĩa là gì, và vì sao anh phải làm

Nhãn này nghĩa là **có một người đã mở nguồn gốc ra và so tận mắt với dữ liệu**. Tôi
không tự gắn nhãn này được, vì mọi lần đọc của tôi đều là máy đọc — kể cả khi đọc hai lần.

Không phải toàn bộ ~2.400 dòng dữ liệu cần soát. Tôi đã chia theo mức rủi ro: bảng nào
bóc từ **ảnh/scan** và chứa **con số người dùng hay đối chiếu** thì mới đáng công soát tay.
Bảng bóc từ HTML thì lỗi transcribe gần như không xảy ra.

---

## Mức 0 — KHÔNG cần soát: đã đọc kép

Tôi đọc lại **độc lập** từ ảnh gốc rồi so từng ô với file dữ liệu. Ô nào hai lần đọc khớp
nhau thì xác suất cả hai cùng sai một kiểu là rất thấp.

| Bảng | Số ô so | Kết quả |
|---|--:|---|
| `admission_scores_2024` | 128 | 1 ô lệch — **FL1 ĐGTD**: file ghi 52.01, lần đọc lại ra 50.29. Phóng to ảnh ×3 → đúng là **52.01**, lần đọc lại của tôi sai (chép nhầm số của dòng FL2 ngay dưới) |
| `admission_scores_2025` | 260 | 260/260 khớp |
| `admission_scores_2026` | 272 | 272/272 khớp |

Các dòng này nay gắn nhãn **`vision_double_read`** — mạnh hơn `vision_extracted` nhưng
vẫn chưa phải `manual_verified`. Nếu anh muốn lên `manual_verified` cho phần điểm chuẩn,
chỉ cần soát **ô FL1 ĐGTD 2024** là đủ, vì đó là ô duy nhất từng có bất đồng.

---

## Mức 1 — PHẢI soát tay (xếp theo rủi ro giảm dần)

Tất cả đều là **một lần đọc duy nhất từ ảnh**, chưa có lần đọc thứ hai.

### 1. `cert_equivalence_output_2026` — 153 dòng · RỦI RO CAO NHẤT

- **Mở:** `data/raw/tuition/ngoaingu_p8_bang21.png` (hoặc PDF `data/raw/admission/Quy_dinh_ngoai_ngu_K71_2026.pdf`, trang 8)
- **So với:** `data/processed/cert_equivalence_output_2026.csv`
- **Vì sao rủi ro cao:** bảng 14 cột, nhiều ô gộp (IELTS 3.5 phủ Bậc 2.2–2.3; KET phủ Bậc 2.1–2.3), nhiều ô gạch chéo. Lớp text của PDF trả về lệch cột nên tôi phải đọc bằng ảnh.
- **Soát kỹ nhất hàng Bậc 3.1 và 3.2** — đó là ngưỡng chuẩn đầu ra CTĐT chuẩn, bot sẽ trả lời hàng này nhiều nhất.

### 2. `cert_bonus_conversion` năm 2026 — 110 dòng

- **Mở:** ảnh `quydoi-cccnn-2026.png` trên trang đề án 2026 (nguồn ghi trong cột `source`)
- **So với:** các dòng `year = 2026` trong `data/processed/cert_bonus_conversion.csv`
- 24 loại chứng chỉ trong một ảnh. Dòng IELTS 2026 đã đối chiếu được với bảng cùng loại của
  năm khác nên đáng tin hơn — **ưu tiên các chứng chỉ ít gặp**: TOPIK, JLPT, DELF, TestDaF, HSK.

### 3. Ba bảng tiền — 47 dòng

| Bảng | Dòng | Nguồn để mở |
|---|--:|---|
| `tuition_credit` | 30 | QĐ học phí 2024, Phụ lục I trang 3 |
| `tuition_by_year` | 11 | Đề án tuyển sinh 2024, Bảng 9–12 (trang 26, 27, 29) |
| `admission_fees` | 6 | Đề án tuyển sinh 2024, mục 1.9 (trang 26) |

Rủi ro không cao về transcribe nhưng **hậu quả cao nhất nếu sai** — sai học phí là thứ phụ
huynh phát hiện ngay. Soát kỹ cột `unit` (/năm hay /học kỳ).

### 4. `cert_cefr_equivalence` — 47 dòng

- **Mở:** ảnh `image_2b.png` trên trang đề án 2025
- **So với:** `data/processed/cert_cefr_equivalence.csv`

### 5. Một dòng đã đánh dấu từ trước

- `language_exit_requirement_2026`, dòng **IT-EP**: Bảng 5.2 (trang Phụ lục V) có 2 cột
  PFIEV | CNTT Việt-Pháp. Tôi suy ra dòng "cử nhân: DELF B1" áp dụng cho cả hai cột nhưng
  chưa chắc. Mở PDF xem dòng đó có kẻ ô gộp qua 2 cột không.

---

## Mức 2 — Soát theo mẫu: số suy ra từ quy tắc (27 dòng)

Nhãn `rule_derived` — **không có trên bảng công bố**, do tôi tính: điểm nhóm tổ hợp kỹ
thuật = điểm công bố + 0,5.

| Năm | Dòng | Độ tin |
|---|--:|---|
| 2026 | 15 | Cao — ngành nào xét tổ hợp nào lấy từ bảng tổ hợp 2026 (đã đối chiếu chéo 292/293) |
| 2025 | 12 | **Thấp hơn** — 2025 không có bảng tổ hợp theo ngành, tôi mượn danh sách tổ hợp của 2026 |

Đã đối chiếu được với ví dụ trong bài báo chính thức: **EM3 2025** (D01 = 24,30 → A00/A01/K01
= 24,80) và **EM1, FL4 2026** — khớp tuyệt đối. Nên **chỉ cần soát 12 dòng 2025**, và câu hỏi
cần trả lời là: *năm 2025 các ngành này có thật sự xét tổ hợp khối A không?* Nếu anh tìm được
thông tin tổ hợp 2025 theo ngành thì tôi thay proxy bằng số thật.

Hai ngành 2025 **cố ý không tách**: EM4 và TROY-BA — không có trong danh mục 2026 nên không
có gì để mượn. Giữ nguyên một mức điểm, không đoán. 

---

## Mức 3 — Không cần soát từng dòng

Bóc từ HTML/web, không qua ảnh:

- `quotas_*`, `program_methods_*` — HTML đề án, tổng chỉ tiêu 2026 khớp số công bố 9.880
- `subject_combinations_2026` — **đã đối chiếu chéo 2 nguồn độc lập**, khớp 292/293 (lệch
  duy nhất là mã DD2, đã bổ sung)
- `program_overview_2026`, `tuition_2026` — trang ngành chính thức
- `entity_aliases`, `programs_*` — không cần nhãn này; `validate_aliases.py` kiểm tính nhất quán

---

## Tổng khối lượng thực tế cho anh

| Mức | Dòng | Cách soát |
|---|--:|---|
| 1 — bắt buộc | ~358 | mở ảnh, so cả bảng |
| 2 — theo mẫu | 12 | trả lời 1 câu hỏi về tổ hợp 2025 |
| Tùy chọn | 1 ô | FL1 ĐGTD 2024 để nâng điểm chuẩn lên `manual_verified` |

**Tôi có thể giảm Mức 1 thêm** bằng đúng cách vừa làm với điểm chuẩn: đọc lại độc lập
`cert_equivalence_output_2026` và `cert_bonus_conversion` 2026 rồi so từng ô. Với điểm chuẩn,
cách này rút 660 ô xuống còn **1 ô** phải phân xử. Anh chỉ còn phải soát những ô hai lần đọc
không khớp.
