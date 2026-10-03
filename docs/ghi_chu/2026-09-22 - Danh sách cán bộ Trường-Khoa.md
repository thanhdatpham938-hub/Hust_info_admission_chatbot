# Ghi chú: Danh sách cán bộ các Trường/Khoa

**Ngày:** 2026-09-22 · **Trạng thái:** đang chờ quyết định

## Đã làm

Bóc được **56 bộ môn/đơn vị** trên 10 Trường/Khoa → field `departments` trong
`data/faculty/<code>/info.json`. Dùng HTML đã tải sẵn ở `data/raw/faculty/<code>/can_bo.html`,
không crawl lại. Script: `scripts/extract_departments.py`.

| Đơn vị | Số bộ môn | Ghi chú |
|---|---:|---|
| SOICT | 14 | |
| SCLS | 8 | |
| SME | 7 | |
| SEEE | 6 | |
| SMSE | 6 | |
| FED | 5 | |
| SEM | 3 | |
| SOFL | 3 | |
| SEP | 2 | |
| FAMI | 2 | Suy từ slug URL; trang thứ 3 (slug `n-3`) chưa rõ tên bộ môn |

## Vấn đề: có nên crawl danh sách cán bộ từng người không?

### Khảo sát thực tế (đã kiểm chứng trên HTML đã tải)

| Trường | Số cán bộ nhận dạng được trong HTML |
|---|---:|
| SEEE | 226 |
| SCLS | 198 |
| SMSE | 123 |
| SME | 23 |
| SOICT | 17 (thực tế nhiều hơn — bị cắt) |
| FED | 17 |
| SEP | 16 |
| FAMI | 9 |
| SEM | 3 |
| SOFL | 0 |

→ Khoảng một nửa số site **render danh sách bằng JavaScript**, `curl`/`requests` chỉ
thấy bộ lọc bộ môn. Muốn lấy đủ phải dùng **Playwright** (trình duyệt thật).

### 3 lý do nên cân nhắc trước khi làm

1. **PRD không yêu cầu.** Mục 3.D liệt kê bảng `faculties` cần: tên, địa chỉ,
   *bộ môn trực thuộc*, ngành đào tạo, mô tả ngắn, thông tin liên hệ — **không có
   danh sách cán bộ**.
2. **Chỉ lấy được một nửa nếu không dùng Playwright**, tức dữ liệu sẽ lệch giữa
   các trường: trường thì đủ 226 người, trường thì 0.
3. **Dữ liệu chóng cũ.** Cán bộ vào/ra liên tục — đúng vấn đề của thông báo
   Khoa/Viện ở PRD mục 4.5, nơi PRD đã chọn giải pháp **link-only** thay vì crawl.

### Đề xuất

Giữ link trang cán bộ trong `faculties.official_channel_url`, để bot trả link khi
được hỏi "trường X có giảng viên nào" — thay vì lưu danh sách tên người.

**Chỉ nên crawl đầy đủ bằng Playwright nếu** muốn bot trả lời được dạng câu hỏi
"ai đang nghiên cứu lĩnh vực Y", "giảng viên nào dạy môn Z" — tức mở rộng phạm vi
so với PRD hiện tại.

## Việc còn treo liên quan

- Trang thứ 3 của FAMI (`danh-sach-giang-vien/n-3/`) chưa xác định được tên bộ môn
- 3 trang cán bộ phụ của SOFL (`danh-muc-can-bo5,6,7`) đã tải về nhưng chưa bóc —
  cả 3 đều có title chung "Khoa Ngoại ngữ", không phân biệt được bộ môn
