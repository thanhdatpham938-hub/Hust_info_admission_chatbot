# Thống kê độ phủ dữ liệu theo ngành

**Ngày:** 2026-09-22 · 68 ngành năm 2026

## Độ phủ tổng thể

| Loại dữ liệu | Phủ | Ghi chú |
|---|---|---|
| Điểm chuẩn | 68/68 (100%) | 3 năm 2024–2026 |
| Chỉ tiêu | 68/68 (100%) | 2025, 2026 |
| Phương thức xét tuyển | 68/68 (100%) | XTTN / ĐGTD / THPT |
| **Tổ hợp xét tuyển** | **68/68 (100%)** | Mới bóc, 292 dòng, 8 tổ hợp |
| Nhóm CT (tra học phí) | 68/68 (100%) | |
| **Mô tả ngắn** | **68/68 (100%)** | Đã lấp 2026-09-23, trung vị 364 ký tự, nguồn thống nhất ts.hust.edu.vn |
| **Trang giới thiệu ngành (RAG)** | **68/68 (100%)** | 151 chunk, 189.231 ký tự |
| **Học phí theo ngành 2026** | **68/68 (100%)** | Mới — trước chỉ có học phí theo nhóm |
| **Thời gian đào tạo / bằng tốt nghiệp** | **68/68 (100%)** | Mới |
| Link CTĐT | 65/68 (95,6%) | Thiếu CH-E20, ED5, FL4 (ngành mới, trang chưa có link) |

## Cập nhật 2026-09-23 — đã lấp xong 5 ngành thiếu mô tả

Trước đây 5 ngành (MS1, MS-E3, MS5, TX1, TROY-IT) không lấy được mô tả vì trang CTĐT
của Trường Vật liệu / Khoa Toán-Tin không có thẻ `<p>` nào đủ dài. Thay vì nới quy tắc
bóc trên web của từng Trường, đã chuyển sang nguồn tốt hơn: **trang giới thiệu ngành
chính thức trên `ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/<slug>`** — cả 68
ngành đều có trang riêng theo cùng một template.

Script mới: `scripts/crawl_program_pages.py`, đọc link từ `data/link_dao_tao_nganh.md`.

Mỗi trang cho 6 nhóm thông tin mà trước đây chưa có:

| Mục trên trang | Đi về đâu |
|---|---|
| Ngôn ngữ đào tạo, bằng tốt nghiệp, thời gian đào tạo, học phí, thời gian tuyển sinh | `data/processed/program_overview_2026.csv` + chunk "Thông tin nhanh" |
| Giới thiệu ngành, đối tượng phù hợp, hình thức xét tuyển | RAG + `short_description` trong `data/programs/<mã>.json` |
| Khối kiến thức đặc trưng + link CTĐT chi tiết | RAG (URL nhúng thẳng vào text để bot trích dẫn được) |
| Cơ hội việc làm | RAG |
| Liên hệ tư vấn / đơn vị quản lý (SĐT, email, địa chỉ) | RAG |
| Tổ hợp, điểm chuẩn, chỉ tiêu | **BỎ** — đã có trong CSV, tránh bot trả lời hai kiểu |

Hai điểm đáng chú ý phát hiện khi bóc:

1. **Học phí trên trang ngành là số 2026 theo TỪNG ngành**, chi tiết hơn bảng nhóm năm
   2024 đang có: IT1 28–40 triệu/năm, IT-E10 ~68 triệu/năm, ED5 22–28 triệu/năm.
   Vẫn giữ đúng phân biệt đơn vị: 63 ngành tính **/năm**, 5 ngành quốc tế tính **/học kỳ**.
2. **Link ET-E16 trong file của anh bị trùng với EE-EP** (copy nhầm). Phát hiện được vì
   script đối chiếu "Mã xét tuyển" in trên trang với mã trong file — đã sửa thành
   `truyen-thong-so-va-ky-thuat-da-phuong-tien-chuong-trinh-tien-tien`. Đã đối chiếu
   toàn bộ 68 slug với trang index: khớp 68/68, không thừa không thiếu.

## Hai lỗi thuật toán ghép đã sửa trong lần rà soát này

**Lỗi 1 — không hiểu từ đồng nghĩa.** Website các trường gọi chương trình tiên tiến là
"ELITECH" hoặc "CTTT", còn bảng ngành ghi "(CT tiên tiến)". Điểm khớp rơi xuống 57%,
dưới ngưỡng 60% nên trượt. Đã quy 3 cách gọi về một token.

**Lỗi 2 — tên ngành ngắn gây khớp nhầm hàng loạt.** "Kỹ thuật Ô tô" (TE1) sau chuẩn hoá
chỉ còn **1 token có nghĩa là "thuat"** (vì "ky", "o", "to" đều ≤2 ký tự bị loại), nên
mọi tiêu đề chứa chữ "thuật" đều khớp TE1 với điểm tuyệt đối 1.0 và chiếm mất link của
ngành khác. Đã đổi sang ưu tiên **số token khớp tuyệt đối** trước rồi mới xét tỉ lệ, và
bỏ qua ngành có dưới 2 token đặc trưng.

Kết quả: ghép được **54/68 → 60/68**, số ngành thiếu dữ liệu **12 → 5**.

## Lưu ý kỹ thuật lặp lại 2 lần

Ký tự `\b` trong regex bị biến thành **ký tự backspace vô hình `\x08`** khi ghi file
(đã gặp ở `de_an_to_rag.py`, nay lặp lại ở `crawl_programs.py`). Regex im lặng không
khớp gì, nhìn source bằng mắt không phát hiện được, phải disassemble bytecode mới thấy.
→ Trong các script sau nên tránh `\b`, dùng lớp ký tự `[0-9]`/`[a-z]` hoặc so khớp
token trên chuỗi đã đệm khoảng trắng.

## Rà soát chất lượng mô tả (2026-09-23, lần 2)

Anh phát hiện `short_description` của BF-E12 là một **bảng song ngữ bị ép phẳng**, dính
liền không khoảng trắng ("...ELITECHTên chương trình:Name of program:..."). Truy ngược ra
3 lỗi:

**Lỗi 1 — quy tắc ghi đè sai.** Script chỉ thay mô tả cũ khi mô tả mới **dài hơn**. Các
mô tả bẩn lấy từ web từng Trường đều bị cắt cụt ở đúng 600 ký tự nên luôn dài hơn bản mới
từ ts.hust.edu.vn (trung vị 364 ký tự) → không bao giờ bị thay. Dính 5 ngành: BF1, BF2,
EV1, EV2, BF-E12, BF-E19 (đều thuộc Trường Hóa & KHSS). Đã sửa: **luôn ưu tiên bản
ts.hust.edu.vn**, không so sánh độ dài nữa. Giờ 68/68 ngành dùng chung một nguồn.

**Lỗi 2 — bỏ sót nội dung bọc trong `<center>`.** Trang CH1 và ED2 bọc đoạn giới thiệu
trong thẻ `<center>`, mà script chỉ quét con trực tiếp của `wrap_view` (`recursive=False`)
nên mất sạch mục "Giới thiệu chung" — 2 ngành này chỉ có 3 mục thay vì 4, và mô tả rơi về
bản bẩn cũ. Đã đổi sang quét mọi độ sâu, có chặn đếm trùng cho nội dung nằm trong `<li>`.
Kiểm lại: **0 chunk có đoạn lặp**.

**Lỗi 3 — lấy nhầm dòng liên kết.** TROY-IT có dòng "Xếp hạng ĐH Troy: https://usnews..."
dài 92 ký tự, đủ dài để bị nhầm là đoạn mô tả. Đã loại các dòng chứa URL và các dòng bắt
đầu bằng Địa chỉ/Điện thoại/Website/Email/Hotline/Xếp hạng/Fax, đồng thời ưu tiên đoạn nằm
ngay sau tiêu đề dạng "GIỚI THIỆU VỀ CHƯƠNG TRÌNH ..." — vì trang các CT quốc tế mở đầu
bằng phần giới thiệu **trường đối tác** chứ không phải ngành học.

### Lưu ý khi tự viết bộ dò văn bản bẩn

Bản dò đầu tiên của tôi dùng `[a-zà-ỹ][A-ZÀ-Ỹ]` để tìm chữ dính, **báo nhầm 67/68 ngành**.
Nguyên nhân: trong Unicode, dải `À-Ỹ` (U+00C0–U+1EF9) trùm luôn cả chữ **thường** có dấu
tiếng Việt, nên gần như câu nào cũng khớp. Phải dùng `a.islower() and b.isupper()` thì mới
đúng — dò lại ra đúng 5 ngành. Bộ dò này nay nằm trong `crawl_program_pages.py`
(`looks_glued`) và tự cảnh báo mỗi lần chạy.

### Kết quả sau khi sửa

| Chỉ số | Trước | Sau |
|---|---|---|
| Mô tả bẩn | 5 | **0** |
| Mô tả còn dùng nguồn web Trường cũ | 7 | **0** |
| Mô tả ngắn nhất | 92 ký tự (TROY-IT, là một dòng link) | **180 ký tự** |
| Chunk RAG | 149 / 185.754 ký tự | **151 / 189.231 ký tự** |

Đã kiểm thêm: cả 68 mô tả đều nhắc tới từ khoá trong tên ngành (0 ca lệch chủ đề), 0 chunk
dính spam cờ bạc, 0 chunk có đoạn lặp.

**Còn một hạn chế đã biết:** ME-NUT, ET-LUH, ME-LUH có mô tả nói về **trường đối tác**
(Nagaoka / Leibniz Hannover) thay vì về ngành học, vì trang gốc không có mục "Giới thiệu
về chương trình" riêng mà mở đầu luôn bằng phần giới thiệu trường. Văn bản vẫn sạch và
đúng chủ đề, phần mô tả ngành đầy đủ vẫn nằm trong chunk RAG. Nếu anh muốn mô tả tập trung
vào ngành thì phải viết tay 3 ngành này.
