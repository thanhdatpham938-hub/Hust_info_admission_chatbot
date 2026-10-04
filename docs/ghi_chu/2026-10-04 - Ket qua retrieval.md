# Kết quả retrieval — 2026-10-04 (dense, text-embedding-3-large, top-5)

Đo mức tài liệu (chưa có `chunk_id` mong đợi trong bộ 120 câu — xem PLAN - Embedding (v1) mục 7).
Đáp án mong đợi trong bộ 120 câu KHÔNG dùng để chấm — chỉ so cột "Tài liệu tham chiếu".

| | Số câu | Hit@5 |
|---|--:|--:|
| Toàn bộ 77 câu có tham chiếu RAG | 77 | 60 (78%) |
| Bỏ câu đã biết thiếu dữ liệu nguồn (⛔) | 59 | 48 (81%) |

## Câu trượt (không phải do thiếu dữ liệu đã biết)

| ID | Câu hỏi | Nguồn kỳ vọng | Top-1 trả về |
|---|---|---|---|
| Q10 | Trường có tính hệ số 2 đối với môn chính (ví dụ Toán hoặc Tiếng Anh) khi xét tuyển theo điểm thi THPT không? | de_an_tuyen_sinh_2026 | qui-dinh-ve-xttn-nam-2026-ky |
| Q12 | Công thức tính điểm xét tuyển theo kỳ thi ĐGTD (TSA) có cộng điểm ưu tiên đối tượng và khu vực không? | de_an_tuyen_sinh_2026 | de_an_tuyen_sinh_2025 |
| Q18 | Điều kiện học bạ tối thiểu để nộp hồ sơ vào HUST là gì? Có yêu cầu điểm trung bình các môn học không? | de_an_tuyen_sinh_2026 | de_an_tuyen_sinh_2024 |
| Q20 | Điểm ưu tiên khu vực và đối tượng được tính như thế nào trong phương thức xét điểm thi ĐGTD? | de_an_tuyen_sinh_2026 | trang_tuyen_sinh |
| Q24 | Nếu đã trúng tuyển diện Xét tuyển tài năng thì em có cần thi tốt nghiệp THPT để lấy điểm xét tuyển nữa không? | de_an_tuyen_sinh_2026 | qui-dinh-ve-xttn-nam-2026-ky |
| Q39 | Điểm chuẩn ngành Tiếng Anh chuyên nghiệp quốc tế (FL2) được tính theo thang điểm 30 hay 40? | de_an_tuyen_sinh_2026 | nganh_dao_tao |
| Q41 | Điểm chuẩn phương thức xét điểm ĐGTD có được cộng điểm quy đổi từ chứng chỉ IELTS không? | de_an_tuyen_sinh_2026 | qui-dinh-ve-xttn-nam-2026-ky |
| Q61 | Chương trình chất lượng cao Elitech khác chương trình đào tạo Chuẩn ở những điểm cơ bản nào? | de_an_tuyen_sinh_2026 | QCDT_2025_5445_QD-DHBK |
| Q73 | Những ngành mới mở năm 2026 như Hoá học Mỹ phẩm (CH-E20), Kế toán (EM-E17) có gì đặc biệt để thu hút thí sinh? | gioi_thieu_truong_khoa | nganh_dao_tao |
| Q74 | Chương trình liên kết đào tạo quốc tế dạng 2+2 hoặc 3+1 hoạt động như thế nào? | gioi_thieu_truong_khoa | QCDT_2025_5445_QD-DHBK |
| Q106 | Sinh viên tốt nghiệp các ngành thuộc Trường Vật liệu thường đầu quân cho các doanh nghiệp, nhà máy thuộc lĩnh vực nào? | gioi_thieu_truong_khoa | nganh_dao_tao |
