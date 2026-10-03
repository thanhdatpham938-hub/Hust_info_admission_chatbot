# Trích xuất lại Sổ tay sinh viên 2026 (2026-09-26)

Script: `scripts/sotay_to_rag.py` → `data/rag/raw_chunks/So_tay_sinh_vien_2026.chunks.jsonl` + `.md`
(mục Sổ tay đã gỡ khỏi `scripts/pdf_to_rag_md.py`, không còn ghi đè).

Kết quả: **206 chunk**, 133.000 ký tự, trang in 2–109. Toàn corpus RAG: **622 chunk / 14 nguồn**.

## Lỗi của bản cũ (171 chunk) và cách sửa

| Lỗi | Nguyên nhân | Sửa |
| --- | --- | --- |
| Số trang sai | 1 trang PDF = 2 trang in (dàn trang đôi) | Cắt đôi mỗi trang PDF, lấy số trang in ở chân trang |
| Đoạn văn lộn xộn giữa 2 cột | Đọc theo dòng ngang qua cả 2 cột | Tìm khe cột theo toạ độ x, đọc hết cột trái rồi cột phải |
| Thiếu tiêu đề trang / tiêu đề cha | Chỉ nhận 1 cấp tiêu đề | 2 cấp theo cỡ chữ + vị trí: tiêu đề trang › tiêu đề mục; banner không có thân bài thành tiêu đề cha |
| Mất mục ngắn (điểm dừng xe bus, ô mẹo…) | Lọc thân bài < 40 ký tự | Gộp các mục ngắn liền nhau thành 1 chunk "Tiêu đề: nội dung" |
| Tên CLB / chữ IN HOA bị coi là tiêu đề | Chỉ dựa vào chữ hoa | Dựa vào cỡ chữ + màu; trang danh sách dùng override |
| Bảng bị trải phẳng | Không nhận bảng | `find_tables` → bảng markdown; bảng không kẻ ô nhận theo dòng thẳng hàng |
| Chữ dạng tổ hợp (NFD) ở tr. 50–51 | PDF lưu dấu tách rời | Chuẩn hoá NFC — nếu không, câu hỏi gõ bình thường sẽ không khớp |
| Tiêu đề rác "PHẦN 2 › ĐẢNG ỦY › …" | Trang bìa từng Phần bị đọc như mục | Bỏ qua trang bìa Phần (7, 48, 54, 58, 69) và trang bìa mục chỉ có chữ trang trí (1, 83, 90, 93, 100, 105) |
| Nhãn QR "Thông tin chi tiết xem tại đây" | Chữ cạnh mã QR, đường dẫn nằm trong ảnh | Xoá nhãn |

## Trang chép tay (override) — `data/raw/sotay_overrides/p<N>.md`

22 trang: 2, 3, 12, 23, 27, 28, 29, 30, 35, 45, 46, 49, 50, 51, 55, 56, 57, 94, 99, 102, 104, 107.
Mỗi file có chú thích `<!-- -->` ghi lý do. Nội dung **nguyên văn PDF**; chỉ tự đặt 4 tiêu đề
mà bản in không có: tr. 94 (điểm dừng xe buýt), 99 (fanpage CLB), 104 ("TÌNH BẠN, TÌNH YÊU"), 107 (Sekisho).

## Kiểm tra độ phủ

`coverage()` so từng dòng chữ trong PDF với nội dung chunk. Còn 13 dòng "mất", đều là dương tính giả:
- tr. 15: 3 mảnh ký tự icon ("ln ms", "vd cs", "eqhr");
- tr. 20–21: 10 ô bảng ĐRL (TC1–TC5, 6.x.x) — có trong chunk nhưng ở dạng `TC1 | …` nên phép so nguyên dòng không khớp.

## Chưa làm

- Các link "xem tại đây" nằm trong ảnh mã QR (PDF chỉ có 1 link thật). Muốn lấy cần cài thư viện đọc QR (opencv / pyzbar).
