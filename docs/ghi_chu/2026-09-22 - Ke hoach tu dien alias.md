# Kế hoạch từ điển alias (entity_aliases)

**Ngày:** 2026-09-22 · **Trạng thái:** ĐÃ CHỐT — anh duyệt ngày 2026-09-23, file
`data/processed/entity_aliases.csv` đã sinh xong (160 dòng, 105 alias, phủ 68/68 ngành).
Xem mục "Kết quả sinh file" ở cuối.

## Đính chính đánh giá trước đó

Trước đây tôi nói "chưa có từ điển alias nên phần lớn câu hỏi sẽ không resolve được" —
**đánh giá này SAI**. Đã kiểm chứng: khớp chuỗi trên `program_name` có sẵn đã giải quyết
được phần lớn tên tiếng Việt:

| Người dùng gõ | Kết quả | Có cần alias không? |
|---|---|---|
| Khoa học máy tính | IT1, TROY-IT | Không (nhưng trùng → cần hỏi lại) |
| Kỹ thuật máy tính | IT2 | Không |
| Toán tin | MI1 | Không |
| CNTT | IT1, IT2 | Không |
| Khoa học dữ liệu | IT-E10 | Không |
| Tự động hóa | EE2, EE-E8, EE-EP | Không (nhưng trùng) |
| **Computer Science** | **KHÔNG TÌM THẤY** | **CÓ** |

→ Phạm vi từ điển alias thu hẹp lại đáng kể so với dự tính ban đầu.

## Thực tế còn thiếu 3 nhóm

### Nhóm 1 — Alias tiếng Anh (PRD mục 3.B yêu cầu rõ)

Đã điền đủ **68/68 ngành** năm 2026 (nguồn `data/processed/programs_2026.csv`). Đây là
bản dịch nháp theo quy ước đặt tên thông dụng của HUST — **cột cuối đánh dấu ngành tôi
không chắc chắn về tên tiếng Anh chính thức, anh xem kỹ các dòng có "?"** trước khi
duyệt (đặc biệt nhóm Vật liệu, Cơ khí và các ngành mới mở 2026 vì chưa có brochure tiếng
Anh để đối chiếu).

**Trường CNTT&TT**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| IT1 | CNTT: Khoa học Máy tính | Computer Science | Có |
| IT2 | CNTT: Kỹ thuật Máy tính | Computer Engineering | Có |
| IT-E10 | Khoa học dữ liệu và Trí tuệ nhân tạo (CTTT) | Data Science and Artificial Intelligence | Có |
| IT-E15 | An toàn không gian số - Cyber Security (CTTT) | Cyber Security | Có (đã ghi rõ trong tên gốc) |
| IT-E7 | CNTT (Global ICT) | Global ICT | Có (đã ghi rõ trong tên gốc) |
| IT-EP | CNTT (Việt - Pháp) | Information Technology (Vietnam-France Program) | ? |
| IT-E6 | CNTT (Việt - Nhật) | Information Technology (Vietnam-Japan Program / HEDSPI) | ? |

**Trường Điện - Điện tử**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| EE1 | Kỹ thuật Điện | Electrical Engineering | Có |
| EE2 | Kỹ thuật Điều khiển - Tự động hoá | Control Engineering and Automation | Có |
| EE-E8 | ... (CTTT) | Control Engineering and Automation (Advanced Program) | Có |
| ET1 | Kỹ thuật Điện tử - Viễn thông | Electronics and Telecommunications Engineering | Có |
| ET-E4 | ... (CTTT) | Electronics and Telecommunications Engineering (Advanced Program) | Có |
| ET-E9 | Hệ thống nhúng thông minh và IoT (CTTT) | Smart Embedded Systems and IoT | ? |
| ET-E16 | Truyền thông số và Kỹ thuật đa phương tiện (CTTT) | Digital Communications and Multimedia Engineering | ? |
| ET-LUH | ĐT-VT hợp tác ĐH Leibniz Hannover | Electronics and Telecommunications (Vietnam-Germany, Leibniz University Hannover) | ? |
| EE-E18 | Hệ thống điện và năng lượng tái tạo (CTTT) | Electric Power Systems and Renewable Energy | ? |
| EE-EP | Tin học công nghiệp và Tự động hóa (PFIEV) | Industrial Informatics and Automation (Vietnam-France PFIEV) | ? |
| ET2 | Kỹ thuật Y sinh | Biomedical Engineering | Có |
| ET-E5 | ... (CTTT) | Biomedical Engineering (Advanced Program) | Có |

**Trường Cơ khí**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| ME1 | Kỹ thuật Cơ điện tử | Mechatronics Engineering | Có |
| ME-E1 | ... (CTTT) | Mechatronics Engineering (Advanced Program) | Có |
| ME2 | Kỹ thuật Cơ khí | Mechanical Engineering | Có |
| TE1 | Kỹ thuật Ô tô | Automotive Engineering | Có |
| TE-E2 | ... (CTTT) | Automotive Engineering (Advanced Program) | Có |
| TE2 | Kỹ thuật Cơ khí động lực | Transportation/Power Mechanical Engineering | ? |
| TE3 | Kỹ thuật Hàng không | Aerospace Engineering | ? |
| TE-EP | Cơ khí hàng không (PFIEV) | Aerospace Mechanical Engineering (Vietnam-France PFIEV) | ? |
| HE1 | Kỹ thuật Nhiệt | Heat Engineering / Thermal Engineering | ? |
| ME-LUH | Cơ điện tử hợp tác ĐH Leibniz Hannover | Mechatronics (Vietnam-Germany, Leibniz Hannover) | ? |
| ME-NUT | Cơ điện tử hợp tác ĐH Nagaoka | Mechatronics (Vietnam-Japan, Nagaoka University of Technology) | ? |
| ME-GU | Cơ khí - Chế tạo máy hợp tác ĐH Griffith | Mechanical Engineering - Manufacturing (Vietnam-Australia, Griffith University) | ? |

**Trường Hóa và Khoa học sự sống**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| CH1 | Kỹ thuật Hoá học | Chemical Engineering | Có |
| CH2 | Hoá học | Chemistry | Có |
| CH-E11 | Kỹ thuật Hóa dược (CTTT) | Chemical and Pharmaceutical Engineering | ? |
| CH-E20 | Hoá học Mỹ phẩm (CTTT) (mới) | Cosmetic Chemistry (Advanced Program) | ? (ngành mới 2026) |
| BF1 | Kỹ thuật Sinh học | Biological Engineering | Có |
| BF-E19 | Kỹ thuật sinh học (CTTT) | Biological Engineering (Advanced Program) | Có |
| BF2 | Kỹ thuật Thực phẩm | Food Engineering | Có |
| BF-E12 | Kỹ thuật Thực phẩm (CTTT) | Food Engineering (Advanced Program) | Có |
| EV1 | Kỹ thuật Môi trường | Environmental Engineering | Có |
| EV2 | Quản lý Tài nguyên và Môi trường | Environmental and Resource Management | ? |

**Trường Vật liệu**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| MS1 | Kỹ thuật Vật liệu | Materials Engineering | ? |
| MS-E3 | Khoa học và kỹ thuật vật liệu (CTTT) | Materials Science and Engineering (Advanced Program) | ? |
| MS2 | Kỹ thuật Vi điện tử và Công nghệ nano | Microelectronics and Nanotechnology Engineering | ? |
| MS3 | Công nghệ vật liệu Polyme và Compozit | Polymer and Composite Materials Technology | ? |
| MS5 | Kỹ thuật in | Printing Engineering | ? |
| TX1 | Công nghệ Dệt - May | Textile and Garment Technology | ? |

**Trường Kinh tế**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| EM1 | Quản lý năng lượng | Energy Management | ? |
| EM2 | Quản lý công nghiệp | Industrial Management | Có |
| EM3 | Quản trị kinh doanh | Business Administration | Có |
| EM5 | Tài chính - Ngân hàng | Finance and Banking | Có |
| EM-E13 | Phân tích kinh doanh (CTTT) | Business Analytics | Có |
| EM-E14 | Logistics và Quản lý chuỗi cung ứng (CTTT) | Logistics and Supply Chain Management | Có |
| EM-E17 | Kế toán (CTTT) (mới) | Accounting (Advanced Program) | ? (ngành mới 2026) |

**Khoa Toán - Tin**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| MI1 | Toán - Tin | Mathematics and Informatics | ? |
| MI2 | Hệ thống thông tin quản lý | Management Information Systems | Có |
| MI-E22 | Khoa học tính toán cho các hệ thống thông minh (CTTT) (mới) | Computational Science for Intelligent Systems | ? (ngành mới 2026) |
| TROY-IT | Khoa học máy tính - hợp tác ĐH Troy (Hoa Kỳ) | Computer Science (Vietnam-USA, Troy University) | ? |

**Khoa Vật lý Kỹ thuật**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| PH1 | Vật lý kỹ thuật | Engineering Physics | Có |
| PH2 | Kỹ thuật hạt nhân | Nuclear Engineering | Có |
| PH3 | Vật lý Y khoa | Medical Physics | Có |

**Khoa KH&CN Giáo dục**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| ED2 | Công nghệ giáo dục | Educational Technology | Có |
| ED3 | Quản lý giáo dục | Educational Management | Có |
| ED5 | Tâm lý học công nghiệp và tổ chức (mới) | Industrial and Organizational Psychology | ? (ngành mới 2026) |

**Khoa Ngoại ngữ**

| Mã | Tên tiếng Việt | alias (EN) đề xuất | Chắc chắn? |
|---|---|---|---|
| FL1 | Tiếng Anh KHKT và Công nghệ | English for Science and Technology | Có |
| FL2 | Tiếng Anh chuyên nghiệp quốc tế | Professional and International English | ? |
| FL3 | Tiếng Trung Khoa học và Công nghệ | Chinese for Science and Technology | Có |
| FL4 | Tiếng Hàn Khoa học và Công nghệ (mới) | Korean for Science and Technology | Có (ngành mới 2026) |

> Lưu ý: `Information Technology` một mình (không kèm mô tả Global ICT/Việt-Pháp/Việt-Nhật)
> nên trỏ về cả nhóm IT1/IT2/IT-E7/IT-EP/IT-E6 rồi cho bot hỏi lại, KHÔNG gán cứng vào 1 mã.

### Nhóm 2 — Tên trùng giữa CT chuẩn và CT tiên tiến

Đã rà lại bằng script so khớp tên (bỏ hậu tố "(CT tiên tiến)"/"(mới)") trên toàn bộ
68 ngành 2026: **7 cặp trùng tên tuyệt đối** (không phải 8 như bản nháp trước — "Kỹ
thuật Sinh học" trước đây bị đếm nhầm là ổn, thực ra nó CŨNG trùng, chỉ khác hoa/thường
BF1 "Sinh học" vs BF-E19 "sinh học").

Đây **không phải thiếu alias**, mà là ca cần **hỏi làm rõ** theo PRD mục 10.3. Người
dùng gõ tên chung sẽ trúng cả 2 mã:

| Tên gõ vào | Trùng | Ghi chú |
|---|---|---|
| Kỹ thuật Điều khiển - Tự động hoá | EE2, EE-E8 | chuẩn / tiên tiến |
| Kỹ thuật Điện tử - Viễn thông | ET1, ET-E4 | chuẩn / tiên tiến |
| Kỹ thuật Y sinh | ET2, ET-E5 | chuẩn / tiên tiến |
| Kỹ thuật Cơ điện tử | ME1, ME-E1 | chuẩn / tiên tiến |
| Kỹ thuật Ô tô | TE1, TE-E2 | chuẩn / tiên tiến |
| Kỹ thuật Sinh học | BF1, BF-E19 | chuẩn / tiên tiến |
| Kỹ thuật Thực phẩm | BF2, BF-E12 | chuẩn / tiên tiến |

Ngoài ra còn **1 nhóm gần-trùng** (tên không giống hệt nhau nhưng cùng gốc "Công nghệ
thông tin" nên người dùng dễ gõ chung) — nhóm này KHÔNG bắt được bằng so khớp chuỗi tự
động, phải xử lý riêng bằng alias:

| Tên gõ vào (chung chung) | Trùng | Ghi chú |
|---|---|---|
| Công nghệ thông tin / CNTT (không ghi rõ hệ) | IT-E7, IT-EP, IT-E6 | Global ICT / Việt-Pháp / Việt-Nhật |

→ Việc cần làm không phải thêm alias 1-1, mà là **cấu hình bước clarification**: khi
trúng nhiều mã thì bot hỏi "Anh/chị hỏi chương trình chuẩn hay chương trình tiên tiến?"
(nhóm 1) hoặc "Anh/chị hỏi hệ Global ICT, Việt-Pháp hay Việt-Nhật?" (nhóm CNTT).

### Nhóm 3 — Tên gọi thông dụng / viết tắt của sinh viên

Cần anh xác nhận vì tôi không nắm cách gọi nội bộ. Ví dụ tôi đoán:

| alias | mã ngành | Đúng không? |
|---|---|---|
| Bách khoa CNTT / BK CNTT | IT1 | ? |
| Điện tự động | EE2 | ? |
| Cơ điện tử tiên tiến | ME-E1 | ? |
| Việt Nhật / HEDSPI | IT-E6 | ? |
| Việt Pháp (CNTT) | IT-EP | ? |
| PFIEV | EE-EP, TE-EP | ? |
| Troy | TROY-IT, TROY-BA | ? |
| Vi mạch / bán dẫn | MS2 | ? |
| Đa phương tiện | ET-E16 | ? |

## Cấu trúc file đề xuất

`data/processed/entity_aliases.csv`

| Cột | Ý nghĩa |
|---|---|
| `alias` | Chuỗi người dùng gõ |
| `entity_type` | `program` hoặc `faculty` |
| `entity_code` | Mã ngành/mã trường |
| `alias_type` | `en` (tiếng Anh) / `colloquial` (thông dụng) / `abbrev` (viết tắt) / `code_variant` |
| `year` | Rỗng = áp dụng mọi năm |
| `note` | Căn cứ |

Gộp luôn 4 dòng đang có trong `program_aliases.csv` (biến thể mã TEEP→TE-EP) vào đây
với `alias_type = code_variant`.

## Việc cần anh làm

1. **Duyệt Nhóm 1** (68/68 alias tiếng Anh) — ưu tiên xem các dòng đánh dấu "?", nhất là
   Trường Vật liệu, Trường Cơ khí và 5 ngành mới mở 2026 (CH-E20, EM-E17, MI-E22, ED5, FL4)
2. **Xác nhận Nhóm 3** (tên thông dụng) — phần này tôi đoán, cần anh là người trong trường xác nhận
3. **Quyết định câu hỏi clarification cho Nhóm 2** — nên hỏi theo dạng nào

Sau khi anh chốt, tôi sinh file CSV và viết script kiểm tra (không alias nào trỏ tới mã
không tồn tại, không alias nào trùng nhau trỏ 2 nơi khác nhau).

---

## Thống kê lỗi / việc còn tồn (chốt ngày 2026-09-23)

Chạy `validate_admission_csv.py` lại toàn bộ 3 năm: **0 lỗi, 1 cảnh báo** (FL2/DGTD
2025→2026 lệch 18,32 điểm — đã đối chiếu ảnh gốc, xác nhận là điểm rớt thật, không phải
lỗi transcribe). Điểm chuẩn/chỉ tiêu/tổ hợp coi như sạch.

Các việc còn thiếu, xếp theo mức ưu tiên:

| # | Việc còn thiếu | Chi tiết | Mức độ |
|---|---|---|---|
| 1 | ~~Từ điển alias chưa xong~~ | **ĐÃ ĐÓNG 2026-09-23** — `entity_aliases.csv` 160 dòng + `validate_aliases.py` chạy sạch 0 lỗi | Xong |
| 2 | ~~5 ngành thiếu mô tả ngắn~~ | **ĐÃ ĐÓNG 2026-09-23** — crawl 68 trang giới thiệu ngành trên ts.hust.edu.vn (`crawl_program_pages.py`), mô tả đạt 68/68. Chỉ còn CH-E20, ED5, FL4 chưa có link CTĐT chi tiết (ngành mới, trang chưa đăng) | Xong |
| 3 | **`normalize_chunks.py` chưa viết** | Thống nhất schema chunk RAG theo đúng tên field PRD mục 11.3 (hiện các nguồn RAG dùng field name hơi khác nhau) | Trung bình — cần trước khi nạp vector DB |
| 4 | **`validate_tables.py` chưa viết** | Kiểm tra chéo các CSV bảng (tuition, fees, quotas...) như đã làm cho admission_scores | Trung bình |
| 5 | **`verification_status` chưa có bản nào = `manual_verified`** | Toàn bộ đang là `vision_extracted`; cần spot-check thủ công một mẫu trước khi coi là production-ready | Trung bình |
| 6 | **FAQ tiếng Việt lỗi HTTP 500** | `ts.hust.edu.vn/p/hoi-dap` phía HUST đang lỗi; tạm dùng bản `/en/p/faqs` thay thế | Thấp — lỗi phía nguồn, không sửa được, chỉ recheck định kỳ |
| 7 | **Chỉ tiêu 2024 theo từng ngành chưa có** | Phụ lục 1 không có trong file đã crawl | Đã chốt bỏ qua theo yêu cầu anh, không phải lỗi |

Không có lỗi nghiêm trọng (data corruption, mã ngành sai, trùng dòng) — các việc còn lại
đều là **hoàn thiện độ phủ**, không phải sửa lỗi dữ liệu sai.

# Bổ sung

### 1. Duyệt và chuẩn hóa Nhóm 1 (Tên tiếng Anh - Các ngành có dấu "?")

Dựa trên các tài liệu đào tạo chính thức và cách dịch thông dụng tại Bách khoa Hà Nội, tôi xin đề xuất chuẩn hóa các ngành chưa chắc chắn (dấu `?`) như sau:

| Mã | Tên tiếng Việt | Alias tiếng Anh đề xuất | Trạng thái đề xuất |
|---|---|---|---|
| **IT-EP** | CNTT (Việt - Pháp) | *Information Technology (Vietnam-France Program / PFIEV)* | Thêm "PFIEV" vì chương trình này thuộc hệ kỹ sư chất lượng cao Việt - Pháp. |
| **IT-E6** | CNTT (Việt - Nhật) | *Information Technology (Vietnam-Japan Program / HEDSPI)* | Giữ nguyên đề xuất của anh (HEDSPI là tên gọi rất phổ biến). |
| **ET-E9** | Hệ thống nhúng thông minh và IoT | *Smart Embedded Systems and IoT* | Xác nhận: Tên này chính xác. |
| **ET-E16** | Truyền thông số và Kỹ thuật đa phương tiện | *Digital Communications and Multimedia Engineering* | Xác nhận: Tên này chính xác. |
| **ET-LUH** | ĐT-VT hợp tác ĐH Leibniz Hannover | *Electronics and Telecommunications (Leibniz University Hannover Joint Program)* | Rút gọn nhẹ nhàng cho tự nhiên. |
| **EE-E18** | Hệ thống điện và năng lượng tái tạo | *Electric Power Systems and Renewable Energy* | Xác nhận: Tên này chính xác. |
| **EE-EP** | Tin học công nghiệp và Tự động hóa | *Industrial Informatics and Automation (Vietnam-France PFIEV)* | Xác nhận: Tên này chính xác. |
| **TE2** | Kỹ thuật Cơ khí động lực | *Power Mechanical Engineering* | Tên chính thức thường dùng của khoa cũ và ngành này. |
| **TE3** | Kỹ thuật Hàng không | *Aerospace Engineering* | Thường dùng "Aerospace Engineering" (rộng hơn Aeronautical). |
| **TE-EP** | Cơ khí hàng không (PFIEV) | *Aeronautical Engineering (Vietnam-France PFIEV)* | Hệ PFIEV ngành này thường dịch là "Aeronautical". |
| **HE1** | Kỹ thuật Nhiệt | *Thermal Engineering* | Tên "Thermal Engineering" phổ biến hơn tại HUST. |
| **ME-LUH** | Cơ điện tử hợp tác ĐH Leibniz Hannover | *Mechatronics (Leibniz University Hannover Joint Program)* | Chuẩn hóa hậu tố "Joint Program". |
| **ME-NUT** | Cơ điện tử hợp tác ĐH Nagaoka | *Mechatronics (Nagaoka University of Technology Joint Program)* | Chuẩn hóa hậu tố. |
| **ME-GU** | Cơ khí - Chế tạo máy hợp tác ĐH Griffith | *Mechanical Engineering - Manufacturing (Griffith University Joint Program)* | Chuẩn hóa hậu tố. |
| **CH-E11** | Kỹ thuật Hóa dược (CTTT) | *Pharmaceutical Engineering (Advanced Program)* | Rút gọn thành "Pharmaceutical Engineering" cho ngắn gọn, thực tế ngành này học hóa dược thiên về kỹ nghệ sinh dược. |
| **CH-E20** | Hoá học Mỹ phẩm (CTTT) | *Cosmetic Chemistry (Advanced Program)* | Xác nhận ngành mới 2026. |
| **EV2** | Quản lý Tài nguyên và Môi trường | *Environmental and Resource Management* | Xác nhận: Tên này chính xác. |
| **MS1** | Kỹ thuật Vật liệu | *Materials Engineering* | Phân biệt với MS-E3 (Science). |
| **MS-E3** | Khoa học và kỹ thuật vật liệu (CTTT) | *Materials Science and Engineering (Advanced Program)* | Xác nhận: Tên này chính xác. |
| **MS2** | Kỹ thuật Vi điện tử và Công nghệ nano | *Microelectronics and Nanotechnology Engineering* | Xác nhận: Tên này chính xác. |
| **MS3** | Công nghệ vật liệu Polyme và Compozit | *Polymer and Composite Materials Technology* | Xác nhận: Tên này chính xác. |
| **MS5** | Kỹ thuật in | *Printing Engineering* | Hoặc "Graphic Communication and Printing Technology" (tên hiện đại hơn), nhưng "Printing Engineering" vẫn là cốt lõi. |
| **TX1** | Công nghệ Dệt - May | *Textile and Garment Technology* | Xác nhận: Tên này chính xác. |
| **EM1** | Quản lý năng lượng | *Energy Management* | Xác nhận: Tên này chính xác. |
| **EM-E17** | Kế toán (CTTT) | *Accounting (Advanced Program)* | Xác nhận ngành mới 2026. |
| **MI1** | Toán - Tin | *Mathematics and Informatics* | Xác nhận: Tên này chính xác. |
| **MI-E22** | Khoa học tính toán cho các hệ thống thông minh | *Computational Science for Intelligent Systems* | Xác nhận ngành mới 2026. |
| **TROY-IT** | Khoa học máy tính - ĐH Troy | *Computer Science (Troy University Joint Program)* | Chuẩn hóa hậu tố. |
| **ED5** | Tâm lý học công nghiệp và tổ chức | *Industrial and Organizational Psychology* | Xác nhận ngành mới 2026. |
| **FL2** | Tiếng Anh chuyên nghiệp quốc tế | *Professional and International English* | Tên gốc của trường là "International Professional English" (IPE). Nên bổ sung cụm này. |

---

### 2. Xác nhận và bổ sung Nhóm 3 (Tên thông dụng / Viết tắt của sinh viên)

Các phán đoán của anh về cách gọi của sinh viên rất sát thực tế. Tôi xin xác nhận lại và bổ sung thêm một số từ khóa quan trọng để tăng độ phủ cho Bot:

| Cụm từ người dùng gõ (Alias) | Mã ngành tương ứng | Gợi ý xử lý / Giải thích |
|---|---|---|
| **Bách khoa CNTT / BK CNTT** | `IT1`, `IT2`, `IT-E10`, `IT-E15`, `IT-E7`, `IT-E6`, `IT-EP` | Trỏ về nhóm CNTT và hỏi lại (hoặc trỏ về Viện CNTT&TT - SoICT). |
| **Điện tự động / Tự động hóa** | `EE2`, `EE-E8`, `EE-EP` | Trùng giữa chuẩn, tiên tiến và Việt-Pháp. Cần hỏi rõ hệ. |
| **Cơ điện tử tiên tiến** | `ME-E1` | Đúng. |
| **Việt Nhật / HEDSPI** | `IT-E6` | Đúng (HEDSPI là thương hiệu rất mạnh của ngành này). |
| **Việt Pháp (CNTT)** | `IT-EP` | Đúng. |
| **PFIEV / kỹ sư chất lượng cao** | `EE-EP`, `TE-EP`, `IT-EP` | Nên cấu hình thành bộ lọc để bot liệt kê danh sách các ngành thuộc PFIEV Việt-Pháp. |
| **Troy** | `TROY-IT`, `TROY-BA` | Cần hỏi lại là CNTT hay Quản trị kinh doanh. |
| **Vi mạch / bán dẫn / chip** | `MS2`, `ET1`, `ET-E4`, `ET-E9` | Cực kỳ quan trọng. Hiện nay xu hướng tìm ngành Vi mạch bán dẫn rất cao. HUST đào tạo sâu mảng này ở `MS2` (Vi điện tử) và nhóm `ET` (Điện tử Viễn thông/Hệ thống nhúng). Nên định hướng người dùng vào các mã này. |
| **Đa phương tiện** | `ET-E16` | Đúng. |
| **Hóa dược** | `CH-E11` | Đúng. |
| **Logistics** | `EM-E14` | Đúng. |
| **BA / Phân tích kinh doanh** | `EM-E13` | Đúng. |
| **Liên kết quốc tế / Hợp tác quốc tế / SIE** | Nhóm mã `TROY-*`, `*-LUH`, `*-NUT`, `*-GU` | SIE là Viện Đào tạo Quốc tế quản lý các chương trình này. |
| **Elitech / CTTT / Chương trình tiên tiến** | Các ngành có hậu tố `-Ex` (như `IT-E10`, `EE-E8`,...) | "Elitech" là thương hiệu chung của HUST cho các chương trình chất lượng cao/tiên tiến. |

---

### 3. Quyết định câu hỏi Clarification (Nhóm 2)

Với các cặp ngành bị trùng tên giữa chương trình Chuẩn và chương trình Tiên tiến (Elitech), hướng xử lý đề xuất như sau:

*   **Kịch bản:** Khi người dùng nhập tên ngành chung chung (ví dụ: *"Điện tử viễn thông"*, *"Cơ điện tử"*), hệ thống nhận diện được cả 2 mã (ví dụ: `ET1` và `ET-E4`).
*   **Mẫu câu hỏi Clarification gợi ý:**
    > *"Ngành [Tên Ngành] tại Bách khoa Hà Nội có 2 chương trình đào tạo: **Chương trình chuẩn** (mã [Mã_Chuẩn]) và **Chương trình tiên tiến - ELITECH** học bằng tiếng Anh (mã [Mã_CTTT]). Bạn muốn tìm hiểu thông tin của chương trình nào?"*

---

### 4. Cấu trúc và phương án cập nhật dữ liệu

Tôi đồng ý với cấu trúc bảng `data/processed/entity_aliases.csv` mà anh đề xuất. Việc gộp chung các biến thể mã ngành vào một nơi sẽ giúp code logic gọn gàng hơn.
---

## Kết quả sinh file (2026-09-23)

`data/processed/entity_aliases.csv` — **160 dòng, 105 alias khác nhau, phủ 68/68 ngành 2026**
(en 85 · colloquial 63 · abbrev 8 · code_variant 4). Kiểm bằng `scripts/validate_aliases.py`:
**0 lỗi, 0 cảnh báo**. Validator đã được thử ngược với 6 lỗi cố ý (mã không tồn tại, trùng
dòng, một alias trỏ 2 mã mà vẫn đánh `unique`, alias trùng tên ngành sẵn có...) — bắt đủ cả 6.

### Có thêm một cột ngoài schema anh duyệt: `resolution`

Schema anh duyệt không phân biệt được alias trỏ 1 mã với alias trỏ nhiều mã, mà Nhóm 3
có rất nhiều alias trỏ nhiều mã (PFIEV, Troy, vi mạch...). Nếu không đánh dấu thì bot
không biết khi nào nên trả lời thẳng, khi nào phải hỏi lại. Cột này nhận 3 giá trị:

| Giá trị | Nghĩa | Bot làm gì |
|---|---|---|
| `unique` | alias chỉ ứng với 1 mã | Trả lời thẳng |
| `clarify` | alias ứng với nhiều mã | Hỏi lại theo mẫu câu ở mục 3 |
| `group` | trỏ tới cả một nhóm chương trình | Liệt kê danh sách ngành trong nhóm |

Với `resolution = group`, `entity_code` **không phải mã ngành** mà là đúng chuỗi trong cột
`program_group` của `quotas_2026.csv`, nên bot chỉ cần lọc thẳng, không phải giữ danh sách
26 mã ELITECH trong từ điển (mỗi năm mở/đóng ngành lại phải sửa tay).

### 4 điểm lệch so với bản anh duyệt — cần anh xác nhận lại

1. **PFIEV → IT-EP.** Anh xếp IT-EP cùng nhóm PFIEV với EE-EP và TE-EP. Nhưng đề án 2026
   xếp IT-EP vào **nhóm ELITECH**, chỉ EE-EP và TE-EP nằm trong "CHƯƠNG TRÌNH VIỆT - PHÁP
   (PFIEV)". Tên ngành IT-EP cũng chỉ ghi "(Việt - Pháp)" chứ không có chữ PFIEV. Tôi vẫn
   giữ IT-EP trong alias PFIEV (để học sinh gõ PFIEV vẫn tìm ra) nhưng đánh `clarify` và
   ghi chú rõ trong cột `note`, để bot không khẳng định sai rằng IT-EP là hệ PFIEV.
2. **"Liên kết quốc tế" / SIE.** Anh liệt kê gồm TROY-*, *-LUH, *-NUT, *-GU. Đề án 2026
   thì nhóm "LIÊN KẾT ĐÀO TẠO QUỐC TẾ" **chỉ có FL2 và TROY-IT**; ET-LUH, ME-LUH, ME-NUT,
   ME-GU bị xếp vào ELITECH. Tôi theo cách hiểu của sinh viên (6 mã, `clarify`) và ghi chú
   cách xếp chính thức, riêng alias `SIE` thì trỏ đúng nhóm chính thức.
3. **"Computer Science" phải hỏi lại.** Bản duyệt để `Computer Science → IT1`. Nhưng tên
   tiếng Việt của TROY-IT cũng là "Khoa học máy tính", nên để `unique` sẽ khiến bot trả lời
   IT1 cho cả người đang hỏi chương trình ĐH Troy. Đã đổi thành `clarify` (IT1 + TROY-IT),
   đúng như cách bản kế hoạch đã xử lý tên tiếng Việt ở mục "Đính chính".
4. **TROY-BA và EM4 không còn trong danh mục 2026.** Hai mã này chỉ tuyển đến 2025. Alias
   của chúng ("Troy", "Business Administration", "Accounting") vẫn giữ nhưng gắn `year=2025`
   để bot biết trả lời "ngành này không tuyển sinh năm 2026" thay vì báo không tìm thấy.

### Một alias tôi xác minh được từ dữ liệu vừa crawl

`MS5 = PRINTING ENGINEERING` — trước đây tôi để dấu "?", nay trang ngành chính thức trên
ts.hust.edu.vn ghi thẳng "Tiếng anh: PRINTING ENGINEERING". Đây là ngành **duy nhất trong
68 ngành** có ghi tên tiếng Anh trên trang; 67 tên còn lại vẫn là bản anh duyệt, chưa có
nguồn chính thức để đối chiếu.

---

## Rà soát lại file sau khi sinh (2026-09-23, lần 2)

Chạy lại validator thì sạch, nhưng validator lúc đó chưa kiểm được điều quan trọng nhất:
**gõ alias vào thì thực tế bot trả về mã nào**. Viết thêm phép mô phỏng tra cứu thì lòi ra
4 chỗ khớp thừa và 1 lỗi định dạng. Tất cả đã sửa.

### Bốn quy tắc khớp — tầng tra cứu BẮT BUỘC cài đúng thứ tự này

File alias chỉ đúng khi bot khớp theo đúng 4 quy tắc dưới. Dùng khớp chuỗi con thuần là
sai ngay:

1. **Lọc theo năm trước.** Bỏ các dòng có `year` khác năm đang hỏi, và bỏ mã không có
   trong `programs_<năm>.csv`. Nhờ vậy "Accounting" hỏi năm 2026 ra EM-E17 (CT tiên tiến)
   chứ không ra EM4 đã ngừng tuyển.
2. **Khớp chính xác trên chuỗi đã chuẩn hoá** (bỏ dấu, thường hoá, gộp khoảng trắng) →
   trả về ngay, không xét tiếp.
3. **Không khớp chính xác thì mới lùi về khớp chuỗi con.**
4. **`alias_type = abbrev` chỉ tham gia bước 2.** Viết tắt ngắn như `BA` nếu cho khớp
   chuỗi con sẽ dính 13 ngành (Bách khoa, bán dẫn, Nagaoka, Business Administration...).

Đã kiểm: 99/99 alias trả về đúng như khai báo dưới 4 quy tắc này. Phép mô phỏng nay nằm
trong `validate_aliases.py` nên lần sau sửa file sẽ tự phát hiện.

### Bốn chỗ khớp thừa phát hiện được

| Gõ vào | Khớp chuỗi con thuần sẽ ra | Xử lý |
|---|---|---|
| `BA` | 13 ngành | Quy tắc 4 — viết tắt chỉ khớp chính xác |
| `Accounting` | EM4 + EM-E17 | Quy tắc 1 — lọc năm, 2026 ra EM-E17 |
| `Chemistry` | CH2 + CH-E20 (Cosmetic Chemistry) | Quy tắc 2 — khớp chính xác ra CH2 |
| `Mechanical Engineering` | ME2 + ME-GU + TE2 | Quy tắc 2 — khớp chính xác ra ME2 |

### Lỗi ngược chiều: quy tắc khớp chính xác làm hỏng Nhóm 2

Đây là chỗ đáng chú ý nhất. Bản đầu tôi chỉ khai báo clarify cho **tên tiếng Anh**, còn
tên tiếng Việt thì tin là "khớp chuỗi con trên program_name đã đủ". Nhưng khi thêm quy tắc
khớp chính xác thì gõ "Kỹ thuật Ô tô" **dừng lại ở TE1** (vì trùng khít tên ngành hệ chuẩn)
và không bao giờ gợi ý TE-E2 — tức là **bước hỏi lại của Nhóm 2 bị vô hiệu hóa hoàn toàn**.

Đã thêm **14 dòng tiếng Việt** khai báo tường minh cho cả 7 cặp. Giờ gõ "Kỹ thuật Ô tô"
ra `TE1 + TE-E2` đúng như thiết kế.

Kéo theo một chỉnh sửa trong validator: cảnh báo "alias trùng y hệt tên ngành → thừa" chỉ
còn áp dụng cho dòng `unique`. Với dòng `clarify` thì trùng tên ngành là **bắt buộc**, không
phải thừa.

### Lỗi định dạng

14 dòng vừa thêm có dấu phẩy giữa câu trong cột `note` nên tràn sang cột thứ 8. Đọc bằng
`csv.DictReader` theo tên cột vẫn thấy bình thường, không lộ ra. Đã sửa câu ghi chú và thêm
phép đếm cột vào validator.

**File chốt: 174 dòng, 112 alias, phủ 68/68 ngành, 0 lỗi 0 cảnh báo.** Validator đã thử
ngược với 9 loại lỗi cố ý (gồm 3 loại mới ở lần rà này) — bắt đủ.
