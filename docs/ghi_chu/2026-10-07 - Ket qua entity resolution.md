# Kết quả Entity Resolution trên bộ 120 câu — 2026-10-07

Sinh bởi `scripts/eval_entity_scan.py`: `scan()` tìm cụm từ trong câu, `resolve()` đổi ra mã (năm lấy theo năm ghi trong câu, không có thì năm mới nhất). **Chưa phải số đo AC2/AC8** — chưa có bộ ca có nhãn; bảng này để đọc bằng mắt, tìm alias thiếu và chỉnh ngưỡng fuzzy.

- 114 câu, 62 câu tìm được ít nhất một cụm
- Kết quả theo cụm: clarify = 8, group = 19, unique = 85

| ID | Câu hỏi | Cụm → kết quả | Năm |
|---|---|---|---|
| Q1 | Năm 2026 trường có những phương thức tuyển sinh chính thức nào? | — | 2026 |
| Q2 | Xét tuyển tài năng (XTTN) gồm những diện nào? Khi nào trường bắt đầu mở cổng đăng ký? | `Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`XTTN` → method: **unique** XTTN (exact) |  |
| Q3 | Em được giải Ba học sinh giỏi cấp tỉnh môn Toán thì có thuộc diện xét tuyển thẳng không? | `tuyển thẳng` → method: **unique** XTTN_1.1 (exact) |  |
| Q4 | Chứng chỉ IELTS từ bao nhiêu thì được quy đổi điểm tiếng Anh? Cách quy đổi cụ thể thế nào? | `IELTS` → certificate: **unique** IELTS_ACADEMIC (exact) |  |
| Q5 | Có chứng chỉ IELTS 6.5 thì nộp hồ sơ Xét tuyển tài năng diện 1.2 hay 1.3 sẽ có lợi thế hơn | `IELTS` → certificate: **unique** IELTS_ACADEMIC (exact)<br>`Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`diện 1.2` → method: **unique** XTTN_1.2 (exact) |  |
| Q6 | Kỳ thi Đánh giá tư duy (TSA) thường tổ chức mấy đợt một năm và kết quả thi được bảo lưu tr | `Đánh giá tư duy` → method: **unique** DGTD (exact)<br>`TSA` → method: **unique** DGTD (exact) |  |
| Q7 | Cấu trúc bài thi Đánh giá tư duy (TSA) gồm những phần nào? Thời gian làm bài là bao lâu? | `Đánh giá tư duy` → method: **unique** DGTD (exact)<br>`TSA` → method: **unique** DGTD (exact) |  |
| Q8 | Đăng ký thi ĐGTD ở đâu, lệ phí thi là bao nhiêu và thi ở những tỉnh thành nào? | — |  |
| Q9 | Em thi ĐGTD đạt khoảng 60 điểm thì có cơ hội đỗ vào các ngành công nghệ thông tin của trườ | — |  |
| Q10 | Trường có tính hệ số 2 đối với môn chính (ví dụ Toán hoặc Tiếng Anh) khi xét tuyển theo đi | `điểm thi THPT` → method: **unique** THPT (exact) |  |
| Q11 | Công thức tính điểm xét tuyển (ĐXT) theo điểm thi THPT của Bách khoa được quy định thế nào | `điểm thi THPT` → method: **unique** THPT (exact) |  |
| Q12 | Công thức tính điểm xét tuyển theo kỳ thi ĐGTD (TSA) có cộng điểm ưu tiên đối tượng và khu | `TSA` → method: **unique** DGTD (exact) |  |
| Q13 | Chứng chỉ SAT hoặc ACT tối thiểu bao nhiêu điểm thì đủ điều kiện nộp hồ sơ Xét tuyển tài n | `Xét tuyển tài năng` → method: **unique** XTTN (exact) |  |
| Q14 | Phỏng vấn Xét tuyển tài năng diện 1.3 thường hỏi những gì? Làm sao để chuẩn bị tốt? | `Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`diện 1.3` → method: **unique** XTTN_1.3 (exact) |  |
| Q15 | Em thi học sinh giỏi quốc gia nhưng không đạt giải thì có được ưu tiên cộng điểm hay xét t | — |  |
| Q16 | Trường có giới hạn số lượng nguyện vọng đăng ký xét tuyển của mỗi thí sinh không? | — |  |
| Q17 | Sau khi biết điểm thi THPT hoặc điểm thi ĐGTD, em có được thay đổi thứ tự nguyện vọng khôn | `điểm thi THPT` → method: **unique** THPT (exact) |  |
| Q18 | Điều kiện học bạ tối thiểu để nộp hồ sơ vào HUST là gì? Có yêu cầu điểm trung bình các môn | — |  |
| Q19 | Học sinh các trường THPT chuyên có được ưu tiên cộng điểm hay có phương thức xét tuyển riê | `THPT` → method: **unique** THPT (exact) |  |
| Q20 | Điểm ưu tiên khu vực và đối tượng được tính như thế nào trong phương thức xét điểm thi ĐGT | — |  |
| Q21 | Quy trình xác nhận nhập học trực tuyến trên hệ thống của Bộ GD&ĐT và hệ thống riêng của HU | — |  |
| Q22 | Em có thể đăng ký đồng thời cả phương thức Xét tuyển tài năng và xét điểm thi ĐGTD được kh | `Xét tuyển tài năng` → method: **unique** XTTN (exact) |  |
| Q23 | Hồ sơ Xét tuyển tài năng cần chuẩn bị những giấy tờ gì? Có cần phải nộp bản cứng về trường | `Xét tuyển tài năng` → method: **unique** XTTN (exact) |  |
| Q24 | Nếu đã trúng tuyển diện Xét tuyển tài năng thì em có cần thi tốt nghiệp THPT để lấy điểm x | `Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`thi tốt nghiệp THPT` → method: **unique** THPT (exact) |  |
| Q25 | Bách khoa Hà Nội có xét tuyển hoàn toàn bằng học bạ THPT (không kèm điều kiện chứng chỉ) k | `THPT` → method: **unique** THPT (exact) |  |
| Q26 | Điểm chuẩn ngành Khoa học máy tính (IT1) theo điểm thi THPT của các năm 2024 và 2025 là ba | `IT1` → program: **unique** IT1 (exact)<br>`điểm thi THPT` → method: **unique** THPT (exact) | 2024, 2025 |
| Q27 | Những ngành nào có điểm chuẩn Đánh giá tư duy (TSA) cao nhất trường trong mùa tuyển sinh v | `Đánh giá tư duy` → method: **unique** DGTD (exact)<br>`TSA` → method: **unique** DGTD (exact) |  |
| Q28 | Cho xin bảng điểm chuẩn phương thức ĐGTD của tất cả các ngành năm 2025? | — | 2025 |
| Q29 | Điểm chuẩn Xét tuyển tài năng diện 1.3 của ngành Logistics và Quản lý chuỗi cung ứng (EM-E | `Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`diện 1.3` → method: **unique** XTTN_1.3 (exact)<br>`Logistics và Quản lý chuỗi cung ứng` → program: **unique** EM-E14 (exact)<br>`EM-E14` → program: **unique** EM-E14 (exact) | 2025 |
| Q30 | So sánh điểm chuẩn ngành IT1 và IT2 theo phương thức THPT qua các năm gần đây? | `IT1` → program: **unique** IT1 (exact)<br>`IT2` → program: **unique** IT2 (exact)<br>`THPT` → method: **unique** THPT (exact) |  |
| Q31 | Điểm chuẩn các ngành thuộc khối ngành Điện - Điện tử có xu hướng tăng hay giảm qua các năm | — |  |
| Q32 | Ngành nào có điểm chuẩn thấp nhất của Bách khoa trong năm ngoái? | — |  |
| Q33 | Nhóm ngành Vật liệu (MS) điểm chuẩn thường dao động trong khoảng nào đối với phương thức t | `thi THPT` → method: **unique** THPT (exact) |  |
| Q34 | Ngành Khoa học dữ liệu và Trí tuệ nhân tạo (IT-E10) lấy điểm chuẩn THPT và TSA bao nhiêu? | `Khoa học dữ liệu và Trí tuệ nhân tạo` → program: **unique** IT-E10 (exact)<br>`IT-E10` → program: **unique** IT-E10 (exact)<br>`THPT` → method: **unique** THPT (exact)<br>`TSA` → method: **unique** DGTD (exact) |  |
| Q35 | Tại sao điểm chuẩn của các chương trình Elitech đôi khi lại thấp hơn chương trình chuẩn cù | `Elitech` → program: **group** elitech (exact)<br>`chương trình chuẩn` → program: **group** chuan (exact) |  |
| Q36 | Có bao nhiêu chỉ tiêu dành riêng cho phương thức Xét tuyển tài năng của ngành Kỹ thuật máy | `Xét tuyển tài năng` → method: **unique** XTTN (exact)<br>`IT2` → program: **unique** IT2 (exact) |  |
| Q37 | Tổng chỉ tiêu tuyển sinh của HUST năm 2026 thay đổi thế nào so với năm 2025? | — | 2025, 2026 |
| Q38 | Thống kê số lượng hồ sơ nộp vào ngành Global ICT (IT-E7) qua các năm để tham khảo tỷ lệ ch | `Global ICT` → program: **unique** IT-E7 (exact)<br>`IT-E7` → program: **unique** IT-E7 (exact) |  |
| Q39 | Điểm chuẩn ngành Tiếng Anh chuyên nghiệp quốc tế (FL2) được tính theo thang điểm 30 hay 40 | `Tiếng Anh chuyên nghiệp quốc tế` → program: **unique** FL2 (exact)<br>`FL2` → program: **unique** FL2 (exact) |  |
| Q40 | Ngành nào có tỷ lệ chọi (số lượng đăng ký/chỉ tiêu) cao nhất trong kỳ tuyển sinh vừa qua? | — |  |
| Q41 | Điểm chuẩn phương thức xét điểm ĐGTD có được cộng điểm quy đổi từ chứng chỉ IELTS không? | `IELTS` → certificate: **unique** IELTS_ACADEMIC (exact) |  |
| Q42 | Tỷ lệ chỉ tiêu phân bổ giữa phương thức thi THPT và thi ĐGTD là bao nhiêu phần trăm? | `thi THPT` → method: **unique** THPT (exact) |  |
| Q43 | Có ngành nào của trường năm nay không dành chỉ tiêu cho phương thức xét điểm thi THPT khôn | `điểm thi THPT` → method: **unique** THPT (exact) |  |
| Q44 | Phổ điểm thi Đánh giá tư duy (TSA) năm gần nhất dao động tập trung ở mức bao nhiêu điểm? | `Đánh giá tư duy` → method: **unique** DGTD (exact)<br>`TSA` → method: **unique** DGTD (exact) |  |
| Q45 | Điểm chuẩn ngành CNTT hợp tác với Đại học Troy (Mỹ) lấy bao nhiêu điểm? | `Troy` → program: **unique** TROY-IT (exact) |  |
| Q46 | Học phí chương trình chuẩn của trường năm học 2026-2027 là bao nhiêu tiền một tín chỉ? | `chương trình chuẩn` → program: **group** chuan (exact) | 2026, 2027 |
| Q47 | Học phí các chương trình Elitech (Tiên tiến) dao động trong khoảng bao nhiêu một năm học? | `Elitech` → program: **group** elitech (exact) |  |
| Q48 | Lộ trình tăng học phí của Bách khoa được quy định thế nào? Có cam kết không tăng quá mức q | — |  |
| Q49 | Học phí các chương trình đào tạo quốc tế liên kết (SIE, Troy, Leibniz) được tính như thế n | `SIE` → program: **group** lien_ket (exact)<br>`Troy` → program: **unique** TROY-IT (exact) |  |
| Q50 | Học bổng Khuyến khích học tập (KKHT) của trường gồm những mức nào? Điều kiện CPA và điểm r | — |  |
| Q51 | Học bổng Trần Đại Nghĩa dành cho những đối tượng nào và mức hỗ trợ học phí là bao nhiêu? | — |  |
| Q52 | HUST có những chương trình học bổng doanh nghiệp hay học bổng cựu sinh viên nào dành cho t | — |  |
| Q53 | Tân sinh viên đạt thủ khoa đầu vào các phương thức xét tuyển có được học bổng đặc biệt khô | — |  |
| Q54 | Cách đóng học phí theo kỳ của trường ra sao? Có tính dựa trên số tín chỉ thực tế đăng ký h | — |  |
| Q55 | Sinh viên có phải đóng thêm tiền học phí cho các học phần Giáo dục quốc phòng và Thể chất  | — |  |
| Q56 | HUST có chính sách hỗ trợ vay vốn học tập lãi suất thấp hoặc không lãi suất cho sinh viên  | — |  |
| Q57 | Đối tượng chính sách (hộ nghèo, con thương binh...) được miễn giảm học phí tại trường theo | — |  |
| Q58 | Học phí ngành Việt - Nhật (IT-E6) và Việt - Pháp (IT-EP) có cao hơn nhiều so với hệ chuẩn  | `Việt - Nhật` → program: **unique** IT-E6 (exact)<br>`IT-E6` → program: **unique** IT-E6 (exact)<br>`Việt - Pháp` → program: **clarify** EE-EP, IT-EP, TE-EP (exact)<br>`IT-EP` → program: **unique** IT-EP (exact)<br>`hệ chuẩn` → program: **group** chuan (exact) |  |
| Q59 | Chi phí sinh hoạt, ăn ở trung bình khi học tập tại khu vực quanh Bách khoa Hà Nội khoảng b | — |  |
| Q60 | Học phí khi đăng ký học lại hoặc học cải thiện điểm có bị nhân hệ số cao hơn học lần đầu k | — |  |
| Q61 | Chương trình chất lượng cao Elitech khác chương trình đào tạo Chuẩn ở những điểm cơ bản nà | `Chương trình chất lượng cao Elitech` → program: **group** elitech (exact) |  |
| Q62 | Học chương trình Elitech có bắt buộc phải học và thi bằng tiếng Anh hoàn toàn ngay từ năm  | `Elitech` → program: **group** elitech (exact) |  |
| Q63 | Chương trình Global ICT (IT-E7) học những gì và cơ hội chuyển tiếp học tập nước ngoài ra s | `Global ICT` → program: **unique** IT-E7 (exact)<br>`IT-E7` → program: **unique** IT-E7 (exact) |  |
| Q64 | Chương trình đào tạo kỹ sư Việt - Pháp (PFIEV) có những ngành nào? Bằng kỹ sư PFIEV có giá | `Việt - Pháp` → program: **clarify** EE-EP, IT-EP, TE-EP (exact)<br>`PFIEV` → program: **clarify** EE-EP, IT-EP, TE-EP (exact)<br>`PFIEV` → program: **clarify** EE-EP, IT-EP, TE-EP (exact) |  |
| Q65 | Học hệ Việt - Nhật (IT-E6) có yêu cầu học sinh phải có chứng chỉ tiếng Nhật từ trước khi n | `Việt - Nhật` → program: **unique** IT-E6 (exact)<br>`IT-E6` → program: **unique** IT-E6 (exact) |  |
| Q66 | Chương trình hợp tác với Đại học Troy (Mỹ) học hoàn toàn tại Việt Nam hay phải chuyển tiếp | `Troy` → program: **unique** TROY-IT (exact) |  |
| Q67 | Chương trình liên kết đào tạo với Đức (Leibniz Hannover) yêu cầu trình độ ngoại ngữ (tiếng | — |  |
| Q68 | Sinh viên đang học chương trình chuẩn có thể thi hoặc nộp đơn chuyển sang hệ Elitech được  | `chương trình chuẩn` → program: **group** chuan (exact)<br>`Elitech` → program: **group** elitech (exact) |  |
| Q69 | Bằng Kỹ sư (chương trình chuyên sâu nghề nghiệp) và bằng Cử nhân của Bách khoa khác nhau t | — |  |
| Q70 | Chương trình tích hợp Cử nhân - Thạc sĩ hoạt động thế nào? Học trong bao lâu thì lấy được  | — |  |
| Q71 | Sinh viên chương trình Elitech có được ưu tiên về phòng học điều hòa, giảng viên hay quy m | `Elitech` → program: **group** elitech (exact) |  |
| Q72 | Các chương trình thuộc hệ PFIEV (Việt-Pháp) có được chính phủ Pháp hỗ trợ gì về học phí ha | `PFIEV` → program: **clarify** EE-EP, IT-EP, TE-EP (exact)<br>`Việt-Pháp` → program: **clarify** EE-EP, IT-EP, TE-EP (exact) |  |
| Q73 | Những ngành mới mở năm 2026 như Hoá học Mỹ phẩm (CH-E20), Kế toán (EM-E17) có gì đặc biệt  | `Hoá học Mỹ phẩm` → program: **unique** CH-E20 (exact)<br>`CH-E20` → program: **unique** CH-E20 (exact)<br>`Kế toán` → program: **unique** EM-E17 (substring)<br>`EM-E17` → program: **unique** EM-E17 (exact) | 2026 |
| Q74 | Chương trình liên kết đào tạo quốc tế dạng 2+2 hoặc 3+1 hoạt động như thế nào? | `Chương trình liên kết đào tạo quốc tế` → program: **group** lien_ket (exact) |  |
| Q75 | Tại HUST có ngành nào học hoàn toàn bằng tiếng Pháp ngoài các ngành PFIEV không? | `PFIEV` → program: **clarify** EE-EP, IT-EP, TE-EP (exact) |  |
| Q76 | Các chuyên ngành của Khoa Ngoại ngữ đào tạo những gì? Tiếng Anh khoa học kỹ thuật khác gì  | `Khoa Ngoại ngữ` → faculty: **unique** SOFL (exact) |  |
| Q77 | Đăng ký học chương trình liên kết đào tạo quốc tế (hệ SIE) có bắt buộc phải đi du học ở gi | `chương trình liên kết đào tạo quốc tế` → program: **group** lien_ket (exact)<br>`SIE` → program: **group** lien_ket (exact) |  |
| Q78 | Em muốn đăng ký ngành Cơ điện tử nhưng tiếng Anh chưa tốt thì nên chọn chương trình chuẩn  | `chương trình chuẩn` → program: **group** chuan (exact)<br>`Elitech` → program: **group** elitech (exact) |  |
| Q79 | Các chương trình đào tạo quốc tế của Viện Đào tạo Quốc tế (SIE) có yêu cầu phỏng vấn đầu v | `SIE` → program: **group** lien_ket (exact) |  |
| Q80 | Phân biệt sự khác nhau về nội dung đào tạo và chuẩn đầu ra giữa ngành Khoa học máy tính (I | `IT1` → program: **unique** IT1 (exact)<br>`IT2` → program: **unique** IT2 (exact) |  |
| Q81 | Trường áp dụng quy chế đào tạo theo tín chỉ như thế nào? Một năm học có tối đa bao nhiêu h | — |  |
| Q82 | Điều kiện về điểm CPA tối thiểu để sinh viên không bị rơi vào các mức cảnh cáo học tập (mứ | — |  |
| Q83 | Sinh viên Bách khoa bị buộc thôi học trong những trường hợp vi phạm quy chế học tập nào? | — |  |
| Q84 | Chuẩn đầu ra tiếng Anh (TOEIC/IELTS) để được nhận đồ án tốt nghiệp và xét tốt nghiệp của c | `TOEIC` → certificate: **group** TOEIC_LISTENING, TOEIC_READING, TOEIC_SPEAKING, TOEIC_WRITING (exact)<br>`IELTS` → certificate: **unique** IELTS_ACADEMIC (exact)<br>`chương trình chuẩn` → program: **group** chuan (exact) |  |
| Q85 | Nếu chưa đạt chuẩn tiếng Anh đầu vào (qua bài thi phân loại của trường) thì có được học cá | — |  |
| Q86 | Cách tính điểm trung bình học kỳ (GPA) và điểm trung bình tích lũy (CPA) theo thang điểm 4 | — |  |
| Q87 | Quy định về học cải thiện điểm và học bù, học lại như thế nào? Điểm thi lần sau có thay th | — |  |
| Q88 | Sinh viên có thể đăng ký học vượt để hoàn thành chương trình và tốt nghiệp sớm hơn thời gi | — |  |
| Q89 | Quy trình đăng ký lớp học phần (đăng ký tín chỉ) diễn ra thế nào? Có giải pháp nào khi lớp | — |  |
| Q90 | Hình thức và quy chế tổ chức thi giữa kỳ, cuối kỳ tại HUST có gì khác biệt so với các trườ | — |  |
| Q91 | Điều kiện để sinh viên được phép đăng ký học song bằng (bằng đại học thứ hai) là gì? Yêu c | — |  |
| Q92 | Thời gian tối đa được phép kéo dài khóa học đối với chương trình Cử nhân và Kỹ sư là bao n | — |  |
| Q93 | Điểm rèn luyện của sinh viên được đánh giá dựa trên những tiêu chí nào và ảnh hưởng thế nà | — |  |
| Q94 | Thủ tục xin bảo lưu kết quả học tập để đi nghĩa vụ quân sự hoặc điều trị bệnh cần những gi | — |  |
| Q95 | Sinh viên năm thứ nhất có được phép xin chuyển ngành học nếu thấy không phù hợp không? Điề | — |  |
| Q96 | Em phân vân giữa Kỹ thuật Ô tô (TE1) và Kỹ thuật Cơ khí (ME2), hai ngành này khác nhau thế | `Kỹ thuật Ô tô` → program: **clarify** TE-E2, TE1 (exact)<br>`TE1` → program: **unique** TE1 (exact)<br>`Kỹ thuật Cơ khí` → program: **unique** ME2 (exact)<br>`ME2` → program: **unique** ME2 (exact) |  |
| Q97 | Học ngành Toán - Tin (MI1) ra trường có làm được lập trình viên công nghệ thông tin không? | `Toán - Tin` → program: **unique** MI1 (exact)<br>`MI1` → program: **unique** MI1 (exact) |  |
| Q98 | Khung chương trình của Khoa học dữ liệu & AI (IT-E10) học có nặng hơn ngành Khoa học máy t | `IT-E10` → program: **unique** IT-E10 (exact)<br>`IT1` → program: **unique** IT1 (exact) |  |
| Q105 | Ngành Quản lý năng lượng (EM1) đào tạo những nội dung gì và sau này có thể làm việc ở nhữn | `Quản lý năng lượng` → program: **unique** EM1 (exact)<br>`EM1` → program: **unique** EM1 (exact) |  |
| Q106 | Sinh viên tốt nghiệp các ngành thuộc Trường Vật liệu thường đầu quân cho các doanh nghiệp, | `Trường Vật liệu` → faculty: **unique** SMSE (exact) |  |
| Q107 | Ngành Kỹ thuật nhiệt (HE1) có phải chỉ học về sửa chữa điện lạnh, điều hòa hay rộng hơn th | `Kỹ thuật nhiệt` → program: **unique** HE1 (exact)<br>`HE1` → program: **unique** HE1 (exact) |  |
| Q108 | Ngành Công nghệ giáo dục (ED2) đào tạo ra làm giáo viên hay làm lập trình viên xây dựng hệ | `Công nghệ giáo dục` → program: **unique** ED2 (exact)<br>`ED2` → program: **unique** ED2 (exact) |  |
| Q109 | Bằng Cử nhân/Kỹ sư Công nghệ thông tin của HUST có được các nước phát triển như Nhật Bản,  | — |  |
| Q110 | Ngành Kỹ thuật hạt nhân (PH2) ra trường sẽ làm việc ở đâu trong bối cảnh Việt Nam chưa tri | `Kỹ thuật hạt nhân` → program: **unique** PH2 (exact)<br>`PH2` → program: **unique** PH2 (exact) |  |
| Q111 | Ký túc xá của Bách khoa Hà Nội có bao nhiêu chỗ ở cho tân sinh viên khóa mới? Chi phí phòn | — |  |
| Q112 | Đối tượng sinh viên nào được ưu tiên duyệt hồ sơ ở Ký túc xá HUST? Tân sinh viên tỉnh xa c | — |  |
| Q113 | Thư viện Tạ Quang Bửu phục vụ sinh viên tự học vào những khung giờ nào? Cần điều kiện gì đ | — |  |
| Q114 | Bách khoa Hà Nội có những câu lạc bộ (CLB) học thuật, kỹ năng hay văn nghệ nào nổi bật dàn | — |  |
| Q115 | Hoạt động Nghiên cứu khoa học (NCKH) trong sinh viên được tổ chức thế nào? Có được cộng đi | — |  |
| Q116 | Sinh viên năm thứ nhất có được đăng ký gửi xe máy trong khuôn viên trường không? Giá vé gử | — |  |
| Q117 | Khuôn viên trường rất rộng, làm thế nào để di chuyển giữa các tòa nhà (như tòa D, tòa B, t | — |  |
| Q118 | Tân sinh viên có bắt buộc phải tham gia đầy đủ Tuần sinh hoạt công dân đầu khóa học không? | — |  |
| Q119 | Trường có trạm y tế riêng không và chính sách đăng ký, sử dụng Bảo hiểm y tế bắt buộc cho  | — |  |
| Q120 | Hoạt động tình nguyện (Mùa hè xanh, Tiếp sức mùa thi) của Đoàn thanh niên - Hội sinh viên  | — |  |

## Nhận xét khi đọc bảng (2026-10-07)

**Đúng như thiết kế:**
- "giải Ba" (Q3), "ba năm" không bị nhận là ngành BA: viết tắt chỉ khớp chữ hoa (E8).
- Troy (Q45, Q66) → TROY-IT vì năm mới nhất TROY-BA đã dừng tuyển (E3). PFIEV / Việt - Pháp → hỏi lại 3 ngành như anh đã chốt.
- Tên kèm mã trong ngoặc (Q34, Q39, Q105...) ra cùng một mã ở cả hai cụm.

**Ghi cho Router (Tuần 4):**
- Q96 "Kỹ thuật Ô tô (TE1)": cụm tên ra `clarify` {TE1, TE-E2} nhưng mã ngay sau trong ngoặc đã chỉ rõ TE1. Router nên ưu tiên mã khi mã nằm trong tập ứng viên của cụm tên đứng sát nó.
- Q19 "trường THPT chuyên", Q25 "học bạ THPT": "THPT" bị nhận là phương thức (đã biết trước ở plan mục 2.4). Router bỏ qua khi câu không hỏi điểm/phương thức.
- Q46 "năm học 2026-2027" cho ra 2 năm: Router phải hiểu đây là một năm học.

**Alias có thể còn thiếu — CHƯA thêm, chờ anh quyết (sửa dữ liệu nguồn):**

| Câu | Cụm người dùng gõ | Hiện tại | Gợi ý |
|---|---|---|---|
| Q9 | "các ngành công nghệ thông tin" | không tìm thấy | alias "công nghệ thông tin" → clarify 7 ngành CNTT như "BK CNTT" |
| Q31 | "khối ngành Điện - Điện tử" | không tìm thấy | alias Trường "Điện - Điện tử" → faculty SEEE |
| Q33 | "Nhóm ngành Vật liệu (MS)" | không tìm thấy | "MS" là tiền tố mã ngành Vật liệu; alias "ngành Vật liệu" → faculty SMSE |
| Q49 | "Leibniz" | không tìm thấy | alias "Leibniz" → clarify ET-LUH, ME-LUH |
