# Kết quả retrieval T7 — 2026-10-11

Sinh bởi `scripts/eval_retrieval.py`. Mức **tài liệu**, top-5, cùng một vector câu hỏi cho cả hai cách. Cột tham chiếu đã sửa 2026-10-11 (Q10, Q12, Q20 thêm `trang_tuyen_sinh`; Q18 thêm `qui-dinh-ve-xttn-nam-2026-ky`). Câu chưa gắn ngành/Trường (Router chưa có) nên T7 chạy nhánh chung.

| Cách | Toàn bộ 77 câu | Bỏ câu đã biết thiếu dữ liệu (59) |
|---|--:|--:|
| Cũ — dense thuần | 62/77 (81%) | 50/59 (85%) |
| **Mới — retriever T7** | 64/77 (83%) | **52/59 (88%)** |

- Câu chuyển sang trúng: Q10, Q18
- Câu chuyển sang trượt: —

## Phân bố `top_dense_score` (cosine top-1) — căn cứ ngưỡng R6

- Câu có tham chiếu RAG, trúng: min 0.460 · trung vị 0.567 · max 0.706
- Câu có tham chiếu RAG, trượt: min 0.494 · trung vị 0.562 · max 0.681
- Câu ngoài phạm vi (tự đặt): min 0.279 · trung vị 0.380 · max 0.645
- Câu có tham chiếu RAG dưới ngưỡng 0.4: không có

| Câu ngoài phạm vi | top_dense_score | Dưới ngưỡng? |
|---|--:|---|
| Hôm nay thời tiết Hà Nội thế nào? | 0.380 | có |
| Công thức nấu phở bò ngon? | 0.336 | có |
| Giá vàng hôm nay bao nhiêu? | 0.279 | có |
| Điểm chuẩn Đại học Quốc gia Hà Nội năm 2025 là bao nhiêu? | 0.645 | **không** — Router phải chặn |
| Học phí Đại học Kinh tế Quốc dân? | 0.524 | **không** — Router phải chặn |

## Câu vẫn trượt (không tính câu đã biết thiếu dữ liệu)

| ID | Câu hỏi | Nguồn kỳ vọng | Top-1 mới | Cụm từ dùng |
|---|---|---|---|---|
| Q24 | Nếu đã trúng tuyển diện Xét tuyển tài năng thì em có cần thi tốt nghiệp THPT để lấy điểm x | de_an_tuyen_sinh_2026 | qui-dinh-ve-xttn-nam-2026-ky | — |
| Q39 | Điểm chuẩn ngành Tiếng Anh chuyên nghiệp quốc tế (FL2) được tính theo thang điểm 30 hay 40 | de_an_tuyen_sinh_2026 | nganh_dao_tao | — |
| Q41 | Điểm chuẩn phương thức xét điểm ĐGTD có được cộng điểm quy đổi từ chứng chỉ IELTS không? | de_an_tuyen_sinh_2026 | qui-dinh-ve-xttn-nam-2026-ky | — |
| Q61 | Chương trình chất lượng cao Elitech khác chương trình đào tạo Chuẩn ở những điểm cơ bản nà | de_an_tuyen_sinh_2026 | QCDT_2025_5445_QD-DHBK | — |
| Q73 | Những ngành mới mở năm 2026 như Hoá học Mỹ phẩm (CH-E20), Kế toán (EM-E17) có gì đặc biệt  | gioi_thieu_truong_khoa | nganh_dao_tao | — |
| Q74 | Chương trình liên kết đào tạo quốc tế dạng 2+2 hoặc 3+1 hoạt động như thế nào? | gioi_thieu_truong_khoa | QCDT_2025_5445_QD-DHBK | — |
| Q106 | Sinh viên tốt nghiệp các ngành thuộc Trường Vật liệu thường đầu quân cho các doanh nghiệp, | gioi_thieu_truong_khoa | nganh_dao_tao | — |
