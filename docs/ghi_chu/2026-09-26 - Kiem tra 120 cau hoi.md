# Kiểm tra bộ 120 câu hỏi với dữ liệu thực tế (2026-09-26)

File kiểm tra: `backend/tests/eval/120_question_check_data.md` (bản lưu 2026-09-26 22:20). Mỗi câu được tra trực tiếp trong chunk RAG (`data/rag/raw_chunks/`) và CSV (`data/processed/`), không suy đoán.

## Tổng hợp

| Kết quả | Ý nghĩa | Số câu |
| --- | --- | --: |
| ✅ Khớp | Dữ liệu đủ, đáp án mong đợi đúng | 18 |
| 🔵 Điền số | Đáp án đang là placeholder "[Đọc từ …csv]" — dữ liệu có, đã điền số thật bên dưới | 10 |
| 🟡 Sửa đáp án | Dữ liệu đủ nhưng **đáp án mong đợi sai/lệch** với nguồn | 39 |
| 🟠 Một phần | Dữ liệu trả lời được phần chính, thiếu chi tiết | 26 |
| ⛔ Không có | Nguồn đã thu thập không có thông tin | 21 |
| | **Tổng** | **114** |

Thiếu Q99–Q104 (file có 114 câu). Mọi tên file và URL ở cột nguồn đều tồn tại trong bộ dữ liệu.

## Chi tiết từng câu

| ID | Nhóm | Kết quả | Theo dữ liệu thực tế |
| --- | --- | --- | --- |
| Q1 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Đúng 3 phương thức (đề án 2026). Tỷ lệ % chỉ tiêu từng phương thức (15–20/30–40/40–50%) **không có nguồn** → bỏ. |
| Q2 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Diện 1.1/1.2/1.3 đúng; 1.2 gồm SAT, ACT, A-Level, AP, IB. Cổng đăng ký XTTN 2026 mở **18/5–31/5/2026** (tshn.hust.edu.vn), không phải "tháng 3–5". |
| Q3 | Phương thức tuyển sinh | ✅ Khớp | Giải Ba tỉnh → diện 1.3 (20 điểm thành tích), kèm điều kiện TBC từng năm lớp 10–12 ≥ 8,00. |
| Q4 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Đáp án đang dùng bảng **2025**. Bảng 2026: IELTS 5.0→8.0; 5.5→8.5; 6.0→9.0; 6.5→9.5; 7.0+→10 (cert_bonus_conversion.csv, year=2026). Nên ghi rõ năm trong câu hỏi. |
| Q5 | Phương thức tuyển sinh | 🟡 Sửa đáp án | IELTS là **điểm thưởng** ở cả 1.2 (6.5 → +64 trên thang SAT/+4 thang 100, Bảng 4 QĐ XTTN) và 1.3 (6.5 → 4 điểm thưởng, Bảng 7). Diện 1.2 bắt buộc có SAT/ACT/A-Level/AP/IB. |
| Q6 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Kết quả TSA **có giá trị 02 năm**; xét tuyển 2026 dùng điểm TSA 2025 hoặc 2026. Đề án 2026: 3 đợt thi (24–25/01, 14–15/03, 16–17/05/2026). |
| Q7 | Phương thức tuyển sinh | ✅ Khớp | 150 phút, 100 câu: Toán 60′, Đọc hiểu 30′, Khoa học/GQVĐ 60′. |
| Q8 | Phương thức tuyển sinh | 🟠 Một phần | Đăng ký tại **tsa.hust.edu.vn**; thi tại 11 tỉnh/thành (không có Nam Định). **Lệ phí: `admission_fees.csv` có mức 2024 = 450.000đ/đợt**; mức 2026 (500.000đ) chưa có nguồn — lần kiểm trước ghi nhầm là không có vì chỉ tìm trong chunk RAG. |
| Q9 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Điểm TSA các ngành CNTT 2025/2026 đều ≥ 67 trừ TROY-IT (54,07 / 59,19). IT-E6, IT-EP: 72,81/71,83 (2025), 67,83/67,87 (2026) → 60 điểm không đủ. |
| Q10 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Có (bảng `subject_combinations_2026`, cột `main_subject`, nguồn bên thứ ba): **Toán** là môn chính ở A00/A01/B00/D07 của các ngành kỹ thuật và ở **D01** của 7 ngành Trường Kinh tế (EM*). Ngành Ngôn ngữ (FL1–FL4) và Giáo dục (ED*) **không có môn chính** — "FL nhân hệ số tiếng Anh" là sai. |
| Q11 | Phương thức tuyển sinh | ✅ Khớp | Công thức [(M1+M2+M3+Môn chính)×3/4] + ưu tiên (môn chính là Toán) và K01, nguyên văn trong `scoring_formulas_2026.csv`; biết được ngành nào áp dụng qua cột `main_subject`. |
| Q12 | Phương thức tuyển sinh | 🟡 Sửa đáp án | ĐX ĐGTD **giữ thang 100**: ĐX = điểm TSA + điểm ưu tiên (quy về thang 100) + điểm thưởng chứng chỉ NN. Không quy về thang 30. |
| Q13 | Phương thức tuyển sinh | ⛔ Không có | Không có ngưỡng SAT/ACT tối thiểu (1270/25 không có nguồn). Chỉ có công thức quy đổi và điều kiện TBC ≥ 8,00. |
| Q14 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Phỏng vấn **"không kiểm tra kiến thức học tập"**: hiểu biết về ĐHBK, CTĐT, kế hoạch học tập, khả năng trình bày; tối đa 15 phút; tối đa 20 điểm, đạt ≥ 10; HSNL ≥ 55 mới được phỏng vấn. |
| Q15 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Không đạt giải → không thuộc 1.1, cũng không thuộc điều kiện (a) của 1.3 (yêu cầu **đạt giải**). Chỉ nộp 1.3 nếu thuộc (b) KHKT, (c) Olympia, (d) hệ chuyên 3 năm. |
| Q16 | Phương thức tuyển sinh | 🟡 Sửa đáp án | XTTN diện 1.1: tối đa **03** nguyện vọng (không phải 2). Quy định nguyện vọng THPT/ĐGTD trên hệ thống Bộ: không có. |
| Q17 | Phương thức tuyển sinh | ⛔ Không có | Quy chế chung của Bộ GD&ĐT — không có trong dữ liệu. |
| Q18 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Không có ngưỡng học bạ 7,0. XTTN 1.2/1.3 yêu cầu TBC **từng năm** lớp 10–12 ≥ 8,00; THPT: ngưỡng sàn thông báo sau. |
| Q19 | Phương thức tuyển sinh | ✅ Khớp | Hệ chuyên cả 3 năm → diện 1.3, 20 điểm thành tích. |
| Q20 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Giống Q12: điểm ưu tiên quy về **thang 100**, cộng vào điểm TSA. |
| Q21 | Phương thức tuyển sinh | ⛔ Không có | Quy trình xác nhận nhập học — không có. |
| Q22 | Phương thức tuyển sinh | ⛔ Không có | Không có quy định đăng ký đồng thời nhiều phương thức. |
| Q23 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Nộp trực tuyến tại tshn.hust.edu.vn; 1.2: 01 thư động lực tiếng Anh; 1.3: thư động lực + **02 thư giới thiệu** của thầy/cô THPT; minh chứng thành tích; hậu kiểm sau khi nhập học. |
| Q24 | Phương thức tuyển sinh | 🟠 Một phần | Có: thí sinh phải **tốt nghiệp THPT cùng năm xét tuyển**. Phần "không công nhận nếu trượt tốt nghiệp" là suy luận. |
| Q25 | Phương thức tuyển sinh | 🟡 Sửa đáp án | Đúng là không xét học bạ độc lập (3 phương thức). Bỏ phần "≥ 7,0"; điều kiện TBC ≥ 8,00 là của XTTN. |
| Q26 | Điểm chuẩn & Chỉ tiêu | 🟡 Sửa đáp án | IT1 THPT: **2024 = 28,53; 2025 = 29,19** (29,39 là của IT-E10 năm 2025). 2026 = 29,27. |
| Q27 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | TSA 2026 cao nhất: IT-E10 82,12; IT1 79,26; IT-E15 76,79; EE2 76,50; IT2 75,84 (2025: IT-E10 86,97; IT1 83,39; IT2 79,86; IT-E15 78,49; IT-E7 78,19). |
| Q28 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | Có đủ 65 ngành, method_code = DGTD, year = 2025. |
| Q29 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | EM-E14 2025 XTTN 1.3 = **59,16** (1.2 = 61,42). |
| Q30 | Điểm chuẩn & Chỉ tiêu | 🟡 Sửa đáp án | IT1/IT2 THPT: 2024 28,53/28,48; 2025 29,19/28,83; 2026 29,27/28,91 → chênh **0,05–0,36**, không phải 0,5–1. |
| Q31 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | Đều tăng 2024→2026: EE1 26,81→27,55→28,24; EE2 28,16→28,48→28,98; ET1 27,41→28,07→28,57; ET2 25,80→26,32→27,15. |
| Q32 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | THPT 2025 thấp nhất: TROY-BA 19,00; BF-E19 20,00; BF-E12 21,00 (không phải EV1/MS5/TX1). |
| Q33 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | Nhóm MS, THPT 2024–2026: 23,70 (MS-E3 2025) đến 28,64 (MS2 2026); MS1 24,90→25,39→26,63. |
| Q34 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | IT-E10 THPT 28,22 / 29,39 / 29,54; TSA 81,60 / 86,97 / 82,12 (2024/2025/2026). |
| Q35 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Lý do không có nguồn (suy luận). Có thể dẫn học phí: Elitech 35–50 tr/năm vs chuẩn 28–40 tr/năm (2026). |
| Q36 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Chỉ có chỉ tiêu **tổng theo ngành** (IT2 2026), không chia theo phương thức. |
| Q37 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | Tổng chỉ tiêu 9.680 (2025) → **9.880** (2026), +200; 65 → 68 chương trình. |
| Q38 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Số hồ sơ đăng ký / tỷ lệ chọi — không có. |
| Q39 | Điểm chuẩn & Chỉ tiêu | 🟡 Sửa đáp án | FL2 **không có môn chính** (D01 tính tổng 3 môn), thang 30; không có nguồn cho "thang 40". FL2 2026 THPT 21,25 (nhóm KT) / 20,75; FL2 yêu cầu IELTS 5.5. |
| Q40 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Tỷ lệ chọi — không có. |
| Q41 | Điểm chuẩn & Chỉ tiêu | 🟡 Sửa đáp án | **CÓ**: ĐGTD được cộng điểm thưởng chứng chỉ NN (2026: IELTS 5.0 +1 … 7.0+ +5, thang 100). |
| Q42 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Tỷ lệ % chỉ tiêu theo phương thức — không có. |
| Q43 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | Không có: cả 68 ngành năm 2026 đều xét đủ 3 phương thức (program_methods_2026.csv). |
| Q44 | Điểm chuẩn & Chỉ tiêu | ⛔ Không có | Phổ điểm TSA — không có (chỉ có nhắc phổ điểm THPT khi nói độ lệch tổ hợp). |
| Q45 | Điểm chuẩn & Chỉ tiêu | 🔵 Điền số | TROY-IT: 2024 THPT 21,00 / TSA 50,29; 2025 THPT 21,80 (KT) / 21,30, TSA 54,07, XTTN 55; 2026 THPT 24,94 / 24,44, TSA 59,19. |
| Q46 | Học phí & Học bổng | 🟡 Sửa đáp án | Chuẩn 2026: **28–40 tr/năm** (ED5 22–28, FL4 28–35). Đơn giá/tín chỉ chỉ có năm **2024–2025** (480 / 525 / 550 nghìn) → câu hỏi "2026 bao nhiêu/tín chỉ" chỉ trả lời được bằng số 2024–2025 kèm ghi chú. |
| Q47 | Học phí & Học bổng | 🟡 Sửa đáp án | Elitech 2026 phổ biến **35–50 tr/năm**; IT-E10 ~68; EM-E14 65; CH-E20 40–45; EM-E17, MI-E22 35–45. |
| Q48 | Học phí & Học bổng | ✅ Khớp | Tối đa 10%/năm (QĐ học phí 2024–2025). |
| Q49 | Học phí & Học bổng | 🟡 Sửa đáp án | ME-LUH, ME-NUT, ME-GU, ET-LUH 24–30 tr/**học kỳ**; TROY-IT 33 tr/học kỳ (3 học kỳ/năm); FL2 55 tr/năm. Học phí giai đoạn ở nước ngoài: không có. |
| Q50 | Học phí & Học bổng | 🟡 Sửa đáp án | Xét theo **GPA học kỳ** (không phải CPA): A ≥ 3,6 & ĐRL ≥ 90 (1,5× loại C); B ≥ 3,2 & ĐRL ≥ 80 (1,2×); C ≥ 2,5 & ĐRL ≥ 65 (= học phí các học phần tính GPA). |
| Q51 | Học phí & Học bổng | ✅ Khớp | Hoàn cảnh đặc biệt khó khăn, học tập rèn luyện tốt; 2 mức 50% / 100% học phí học kỳ. |
| Q52 | Học phí & Học bổng | 🟠 Một phần | Có mục Học bổng tài trợ doanh nghiệp (Sổ tay tr. 31); tên nhà tài trợ (Honda, Sumitomo, Samsung, Toyota, Microsoft, Kova) trong đề án 2024. "Học bổng cựu sinh viên cho tân SV": không có. |
| Q53 | Học phí & Học bổng | ⛔ Không có | Học bổng thủ khoa — không có. |
| Q54 | Học phí & Học bổng | ✅ Khớp | Thu theo số tín chỉ đăng ký × đơn giá (QĐ học phí). |
| Q55 | Học phí & Học bổng | ⛔ Không có | Không có quy định thu riêng GDQP/GDTC (chỉ có đơn giá tín chỉ LLCT-GDTC-GDQP cho vài CT Elitech 2024). |
| Q56 | Học phí & Học bổng | 🟡 Sửa đáp án | Vay NHCSXH (QĐ 157/QĐ-TTg) 4 tr/tháng; vay STEM (QĐ 29/2025/QĐ-TTg) học phí + sinh hoạt ≤ 5 tr/tháng. "Không lãi suất / trường bảo lãnh": không có nguồn. |
| Q57 | Học phí & Học bổng | 🟡 Sửa đáp án | Theo NĐ 238/2025/NĐ-CP; nộp Hồ sơ CĐCS cho **Ban** CTSV; mức theo bảng đối tượng (Sổ tay tr. 26); nhận giấy tại P.102 C1. |
| Q58 | Học phí & Học bổng | 🟡 Sửa đáp án | IT-E6, IT-EP 2026: **40–50 tr/năm** (không phải 35–38). |
| Q59 | Học phí & Học bổng | ⛔ Không có | Chi phí sinh hoạt — không có (chỉ có định mức vay 4–5 tr/tháng). |
| Q60 | Học phí & Học bổng | 🟡 Sửa đáp án | Học lại/cải thiện = đơn giá thường, **nhưng học kỳ hè × 1,5**. |
| Q61 | Chương trình đào tạo | 🟠 Một phần | Có ngôn ngữ đào tạo, học phí, khối kiến thức từng CT Elitech. Sĩ số lớp, giảng viên: không có. |
| Q62 | Chương trình đào tạo | 🟠 Một phần | Không có lộ trình tiếng Anh theo năm. Có điều kiện đầu vào CT dạy bằng tiếng Anh: IELTS 5.0 / VSTEP B1 / điểm THPT tiếng Anh ≥ 6,5. |
| Q63 | Chương trình đào tạo | 🟠 Một phần | IT-E7: cử nhân 4 năm, hoàn toàn tiếng Anh, có trao đổi/chuyển tiếp với đối tác. "2+2, 3+1 tại Nhật/Pháp/Đức" không có trong trang ngành. |
| Q64 | Chương trình đào tạo | 🟠 Một phần | EE-EP (Tin học CN & Tự động hóa), TE-EP (Cơ khí hàng không): bằng Kỹ sư – Thạc sĩ, 5,5 năm; hợp tác Chính phủ Pháp–VN (nghị định thư 1997). |
| Q65 | Chương trình đào tạo | 🟠 Một phần | IT-E6: tiếng Nhật tăng cường, cử nhân–thạc sĩ tích hợp. Lộ trình N5→N2 và "không yêu cầu tiếng Nhật đầu vào": không có. |
| Q66 | Chương trình đào tạo | 🟡 Sửa đáp án | TROY-IT: **3,5 năm (10 học kỳ)**, bằng do ĐH Troy cấp; đầu khóa yêu cầu VSTEP B2 hoặc tương đương. |
| Q67 | Chương trình đào tạo | 🟡 Sửa đáp án | ET-LUH: tiếng Việt tăng cường tiếng Đức; chuyển tiếp giai đoạn 2 cần CPA > 2,6 + **tiếng Đức B1** (không phải B2). |
| Q68 | Chương trình đào tạo | 🟡 Sửa đáp án | QCDT Điều 17: học hết năm 1; đáp ứng điều kiện trúng tuyển CT muốn chuyển; **CPA ≥ 2,5**; không bị cảnh báo; không bị kỷ luật. |
| Q69 | Chương trình đào tạo | 🟡 Sửa đáp án | Cử nhân 4 năm; kỹ sư = 4 + **1,5 năm (5,5 năm)**, ≥ 180 TC, bậc 7 (Sổ tay tr. 12–13) — không phải 5 năm / 150–160 TC. |
| Q70 | Chương trình đào tạo | 🟠 Một phần | 4 năm cử nhân + 1,5 năm thạc sĩ = 5,5 năm (đúng). "Đăng ký từ năm 3": không có nguồn. |
| Q71 | Chương trình đào tạo | ⛔ Không có | Ưu tiên phòng học/giảng viên cho Elitech — không có. |
| Q72 | Chương trình đào tạo | 🟠 Một phần | PFIEV là hợp tác Chính phủ Pháp–VN; tài trợ học phí/học bổng: không có. |
| Q73 | Chương trình đào tạo | 🟠 Một phần | Có trang ngành CH-E20, EM-E17 (đều là ngành mới 2026). **Nguồn nên sửa** thành `nganh_dao_tao` / `program_overview_2026.csv`. |
| Q74 | Chương trình đào tạo | 🟠 Một phần | Có ví dụ: CNTT 3+1 với ĐH Aizu…; ET-LUH/ME-LUH 2 giai đoạn. Không có mô tả chung. |
| Q75 | Chương trình đào tạo | ✅ Khớp | IT-EP: tiếng Việt + tiếng Pháp tăng cường; chuẩn đầu ra tiếng Pháp (DELF). |
| Q76 | Chương trình đào tạo | 🟠 Một phần | Khoa Ngoại ngữ có 4 ngành FL1–FL4 (đáp án chỉ nêu FL1). |
| Q77 | Chương trình đào tạo | ⛔ Không có | "Hệ SIE" không còn trong dữ liệu 2026 (liên kết: TROY-IT, FL2 + CT hợp tác quốc tế ME-/ET-). |
| Q78 | Chương trình đào tạo | ✅ Khớp | ME1 dạy tiếng Việt, ME-E1 tiếng Anh (+ điều kiện IELTS 5.0/B1 đầu vào). |
| Q79 | Chương trình đào tạo | ⛔ Không có | SIE không còn; TROY-IT, FL2 yêu cầu IELTS 5.5; không có quy định phỏng vấn. |
| Q80 | Chương trình đào tạo | ✅ Khớp | Có khối kiến thức và việc làm của IT1, IT2. |
| Q81 | Quy chế & Học vụ | ✅ Khớp | 2 học kỳ chính + 1 học kỳ hè (số tuần không có). |
| Q82 | Quy chế & Học vụ | 🟡 Sửa đáp án | Cảnh báo tính theo **số TC không đạt**, không theo CPA: >8 TC → +1 mức; >16 TC hoặc bỏ học → +2 mức; nợ đọng >24 TC → mức 3 (QCDT Điều 19). |
| Q83 | Quy chế & Học vụ | 🟡 Sửa đáp án | Buộc thôi học: (a) cảnh báo mức 3 **lần thứ hai liên tiếp**; (b) quá thời gian học cho phép / không còn khả năng tốt nghiệp (Điều 19 khoản 3). "Tự ý bỏ 1 học kỳ" → nâng 2 mức cảnh báo, không trực tiếp buộc thôi học. |
| Q84 | Quy chế & Học vụ | 🟡 Sửa đáp án | CT chuẩn (K71): **Bậc 3** — IELTS 4.0–5.0 hoặc TOEIC **4 kỹ năng** (Nghe/Đọc ≥ 275, Nói/Viết ≥ 120), không phải "TOEIC 500". K70 trở về trước theo QĐ 10728. |
| Q85 | Quy chế & Học vụ | 🟠 Một phần | Phân loại đầu vào → xếp lớp NNCB; không đạt thì học từ học phần NNCB đầu tiên; từ HK3 tự đăng ký song hành. "Hạn chế đăng ký môn chuyên ngành": không có. |
| Q86 | Quy chế & Học vụ | 🟠 Một phần | Thang 4, trọng số tín chỉ (QCDT Điều 5, 7); bảng quy đổi có thêm các mức A+, B+, C+, D+ — đáp án chỉ nêu A/B/C/D/F. |
| Q87 | Quy chế & Học vụ | ✅ Khớp | Được học lại học phần đã đạt để cải thiện; điểm cao nhất là điểm chính thức. |
| Q88 | Quy chế & Học vụ | 🟠 Một phần | Được tốt nghiệp sớm; tối đa 24 TC/học kỳ chính, 8 TC/học kỳ hè (không phân biệt học lực Khá/Giỏi). |
| Q89 | Quy chế & Học vụ | 🟠 Một phần | Có quy định mở lớp khi ít SV (5–19 SV, hệ số học phí). Tên hệ thống SIS và thủ tục "phiếu mở thêm chỗ": không có. |
| Q90 | Quy chế & Học vụ | ⛔ Không có | Trọng số giữa kỳ/cuối kỳ, hình thức thi — không có quy định chung. |
| Q91 | Quy chế & Học vụ | 🟡 Sửa đáp án | Sớm nhất khi được xếp **trình độ năm thứ 2**; CPA từ trung bình trở lên; **đáp ứng điều kiện trúng tuyển** CT thứ hai trong năm tuyển sinh. |
| Q92 | Quy chế & Học vụ | 🟡 Sửa đáp án | Chậm tiến độ tối đa **5 học kỳ chính** (cử nhân), **2 học kỳ chính** (kỹ sư/thạc sĩ). "Gấp 2 lần" chỉ áp dụng cho diện ưu tiên. |
| Q93 | Quy chế & Học vụ | 🟡 Sửa đáp án | ĐRL theo 5 tiêu chí TC1–TC5 (khung ĐRL 2026–2027, Sổ tay tr. 20–21). Ngưỡng học bổng KKHT: ĐRL ≥ 65 (C) / 80 (B) / 90 (A) — không phải "dưới 70". |
| Q94 | Quy chế & Học vụ | 🟠 Một phần | QCDT Điều 16 có điều kiện nghỉ học tạm thời; danh mục giấy tờ (lệnh nhập ngũ, bệnh án) không có. |
| Q95 | Quy chế & Học vụ | 🟡 Sửa đáp án | Giống Q68: QCDT Điều 17 (hết năm 1, CPA ≥ 2,5, đáp ứng điều kiện trúng tuyển, không cảnh báo, không kỷ luật). |
| Q96 | So sánh & Hướng nghiệp | ✅ Khớp | Có mô tả và việc làm TE1, ME2. |
| Q97 | So sánh & Hướng nghiệp | ✅ Khớp | MI1: môn cốt lõi (CSDL, kỹ thuật lập trình, tối ưu…) và việc làm. |
| Q98 | So sánh & Hướng nghiệp | 🟠 Một phần | Có khối kiến thức IT-E10 (Toán, XSTK, Học máy…) và IT1; "nặng hơn" là suy luận. |
| Q105 | So sánh & Hướng nghiệp | ✅ Khớp | Có mô tả và việc làm EM1. |
| Q106 | So sánh & Hướng nghiệp | 🟠 Một phần | Có việc làm từng ngành MS*/TX1; tên công ty (Samsung, Foxconn, Hòa Phát) không có nguồn. |
| Q107 | So sánh & Hướng nghiệp | ✅ Khớp | HE1: nhiệt điện, dầu khí, hoá chất…; tỷ lệ việc làm đúng ngành thuộc top 5. |
| Q108 | So sánh & Hướng nghiệp | ✅ Khớp | ED2: e-Learning, lớp học thông minh…; việc làm BA, chuyên viên quản trị hệ thống… |
| Q109 | So sánh & Hướng nghiệp | ⛔ Không có | Công nhận bằng tại Nhật/Mỹ — không có. |
| Q110 | So sánh & Hướng nghiệp | ✅ Khớp | PH2: có mục Cơ hội việc làm. |
| Q111 | Đời sống & Ngoại khóa | ⛔ Không có | Số chỗ, giá phòng KTX — không có (chỉ có hệ thống CSAM-HUST, liên hệ). |
| Q112 | Đời sống & Ngoại khóa | ⛔ Không có | Đối tượng ưu tiên KTX — không có. |
| Q113 | Đời sống & Ngoại khóa | 🟠 Một phần | Có danh sách phòng và chức năng thư viện; giờ mở cửa không có. |
| Q114 | Đời sống & Ngoại khóa | 🟡 Sửa đáp án | Có danh sách ~62 CLB/Tổ/Đội (Sổ tay tr. 23); các tên trong đáp án (BK Music, BK Zoom…) **không có** trong danh sách. |
| Q115 | Đời sống & Ngoại khóa | 🟠 Một phần | Có NCKH thường niên, CLB NCKH, cuộc thi sáng tạo (Sổ tay tr. 24); quy đổi điểm đồ án: không có. |
| Q116 | Đời sống & Ngoại khóa | 🟠 Một phần | Gửi xe bằng thẻ sinh viên, nên đăng ký vé tháng (Sổ tay tr. 75); giá vé không có. |
| Q117 | Đời sống & Ngoại khóa | ⛔ Không có | Không có. |
| Q118 | Đời sống & Ngoại khóa | 🟠 Một phần | Sinh hoạt công dân được tính trong ĐRL (mục 1.1.2, 6 điểm); mức "bắt buộc / xử lý vắng" không có. |
| Q119 | Đời sống & Ngoại khóa | 🟠 Một phần | Trung tâm Y tế Bách khoa: số 5 Tạ Quang Bửu, 024 38692400; chính sách BHYT chỉ có tiêu đề link. |
| Q120 | Đời sống & Ngoại khóa | 🟠 Một phần | Đoàn TN (Sổ tay tr. 52); ĐRL: Mùa hè xanh 6 điểm, hiến máu 6 điểm; số liệu quy mô không có. |

