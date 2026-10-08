# Tổng hợp link nguồn dữ liệu — HUST Info & Admission Assistant

Cập nhật 2026-09-26 · `dataset_version = 2026.1`. Sinh tự động từ trường `source_url` của mọi chunk RAG (`data/rag/raw_chunks/`), mọi CSV (`data/processed/`), `data/programs/*.json` và `data/faculty/*/info.json`, nên chỉ liệt kê link **đang thực sự được dùng** (trừ mục 5). Cột "Dùng ở" ghi tên file và số chunk/bản ghi trong ngoặc.

## 1. Trang tuyển sinh (ts.hust.edu.vn)

| # | Nguồn | Link | Dùng ở |
| --: | --- | --- | --- |
| 1 | Phương án tuyển sinh 2025 | https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025 | RAG de_an_tuyen_sinh_2025 (9); cert_bonus_conversion.csv (7); cert_cefr_equivalence.csv (47); program_methods_2025.csv (195); quotas_2025.csv (65); subject_combinations_ref.csv (12) |
| 2 | Thông tin tuyển sinh 2026 | https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026 | RAG de_an_tuyen_sinh_2026 (10); cert_bonus_conversion.csv (105); program_methods_2026.csv (204); programs_2026.csv (68); quotas_2026.csv (68) |
| 3 | Điểm chuẩn 2024 | https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53 | RAG trang_tuyen_sinh (4); admission_scores_2024.csv (128); programs_2024.csv (64) |
| 4 | Điểm chuẩn 2025 | https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa | RAG trang_tuyen_sinh (5); admission_scores_2025.csv (272); programs_2025.csv (65) |
| 5 | Điểm chuẩn 2026 | https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026 | RAG trang_tuyen_sinh (4); admission_scores_2026.csv (287); scoring_formulas_2026.csv (5) |
| 6 | Quy định xét tuyển tài năng 2026 | https://ts.hust.edu.vn/tin-tuc/quy-dinh-ve-phuong-thuc-xet-tuyen-tai-nang-nam-2026 | RAG qui-dinh-ve-xttn-nam-2026-ky (15) |
| 7 | Giới thiệu kỳ thi ĐGTD (TSA) | https://ts.hust.edu.vn/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa | RAG trang_tuyen_sinh (8) |
| 8 | Giới thiệu kỳ thi ĐGTD (TSA) — đường dẫn /en | https://ts.hust.edu.vn/index.php/en/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa | RAG trang_tuyen_sinh (4) |
| 9 | Cẩm nang thi ĐGTD 2026 | https://ts.hust.edu.vn/tin-tuc/cam-nang-thi-danh-gia-tu-duy-tsa-2026-xuat-ban-lan-thu-2 | RAG trang_tuyen_sinh (2) |
| 10 | Danh mục 68 ngành (trang index) | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc | — |

> Các bài điểm chuẩn / đề án trên cũng là nguồn của những bảng đọc từ **ảnh** trong bài: `programs_2024.csv`, `programs_2025.csv`, `cert_cefr_equivalence.csv`, `cert_bonus_conversion.csv` (cột `source` ghi tên ảnh, ví dụ `bka1/bka2`, `image_2b.png`, `quydoi-cccnn-2026.png`).

## 2. Văn bản quy chế, quy định, sổ tay

| # | Nguồn | Link | Dùng ở |
| --: | --- | --- | --- |
| 1 | Quy chế đào tạo 2025 (5445/QĐ-ĐHBK) | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf | RAG QCDT_2025_5445_QD-DHBK (76) |
| 2 | Quy chế thi ĐGTD (10461/QĐ-ĐHBK, 23/10/2024) — Google Drive dẫn từ trang TSA | https://drive.google.com/file/d/1SJ1VnlXIXQHshZvqmu6KC6iN66l_RCxA/view | RAG tsa_quyche (35) |
| 3 | Quy định chuẩn ngoại ngữ K71 (10828/QĐ-ĐHBK, 07/9/2026) | https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=51634 | RAG Quy_dinh_ngoai_ngu_K71_2026 (7); cert_equivalence_output_2026.csv (153); language_exit_requirement_2026.csv (14) |
| 4 | Quy định chuẩn ngoại ngữ K70 (10728/QĐ-ĐHBK, 26/9/2025) | https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=44574 | RAG Quy_dinh_ngoai_ngu_K70 (7) |
| 5 | Sổ tay sinh viên 2026 (bản web) | https://ctsv.hust.edu.vn/so-tay-sv | RAG So_tay_sinh_vien_2026 (206) |
| 6 | Đề án tuyển sinh 2024 (trang đăng; PDF nhúng Google Drive trùng từng byte với file trong máy) | https://ts.hust.edu.vn/tin-tuc/de-an-tuyen-sinh-dai-hoc-nam-2024 | RAG de_an_tuyen_sinh_2024 (38); admission_fees.csv (6); cert_bonus_conversion.csv (18); tuition_by_year.csv (11) |
| 7 | Quyết định học phí 2024–2025 | https://ctt.hust.edu.vn/Upload/Nguyen%20Quoc%20Dat/files/DTDH_QDQC/Hocphi/2024-2025/2024_2_%20Q%C4%90%20h%E1%BB%8Dc%20ph%C3%AD%20-%202024-2025.pdf | RAG tuition (1); tuition_credit.csv (30) |
| 8 | Quyết định học phí 2025–2026 (10232/QĐ-ĐHBK, 12/9/2025) | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2025-2026/QD%20HOC%20PHI%20-%202025-2026-final.pdf | tuition_credit.csv (29) |
| 9 | Quyết định học phí 2026–2027 (12006/QĐ-ĐHBK, 05/10/2026) | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2026-2027/12006_Q%C4%90-%C4%90HBK.pdf | tuition_credit.csv (31) |
| 10 | Quy định học bổng KKHT 2022 | https://ctt.hust.edu.vn/Upload/Nguyen%20Viet%20Tien/files/Quy%20%C4%91%E1%BB%8Bnh%20HB%20KKHT%20n%C4%83m%202022.pdf | RAG kkht_2022 (7) |

Các file `Quy_dinh_ngoai_ngu_K71_2026.pdf`, `Quy_dinh_ngoai_ngu_K70.pdf`, `QCDT_2025_5445_QD-DHBK.pdf`, `10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf`, `qui-dinh-ve-xttn-nam-2026-ky.pdf`, `So tay sinh vien_2026.pdf` là bản tải về của các link ở bảng trên.

## 3. Trường / Khoa (10 đơn vị)

Trang giới thiệu là nguồn của `RAG gioi_thieu_truong_khoa` (số chunk trong ngoặc); các trang còn lại là nguồn của `data/faculty/<mã>/info.json`.

| Mã | Tên | Website chính thức | Giới thiệu | Cán bộ | Danh sách ngành |
| --- | --- | --- | --- | --- | --- |
| FAMI | Khoa toán tin | https://fami.hust.edu.vn/ | https://fami.hust.edu.vn/gioi-thieu-chung-2/ (2) | https://fami.hust.edu.vn/danh-sach-giang-vien/bo-mon-toan-tin/<br>https://fami.hust.edu.vn/danh-sach-giang-vien/n-3/<br>https://fami.hust.edu.vn/danh-sach-giang-vien/bo-mon-toan-ung-dung/ | https://fami.hust.edu.vn/dao-tao/dao-tao-dai-hoc/ |
| FED | Khoa khoa học và công nghệ giáo dục | https://fed.hust.edu.vn/ | https://fed.hust.edu.vn/vi/about/gioi-thieu-chung.html (6) | https://fed.hust.edu.vn/vi/about/can-bo-va-giang-vien.html | https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/ |
| SCLS | Trường hóa và khoa học sự sống | https://scls.hust.edu.vn/vi/ | https://scls.hust.edu.vn/vi/about/gioi-thieu-chung.html (3) | https://scls.hust.edu.vn/vi/organs/ | https://scls.hust.edu.vn/vi/dao-tao/ |
| SEEE | Trường Điện - Điện tử | https://seee.hust.edu.vn/vi/ | https://seee.hust.edu.vn/vi/gioi-thieu/ (1) | https://seee.hust.edu.vn/vi/con-nguoi/can-bo/ | https://seee.hust.edu.vn/vi/dao-tao/chuong-trinh/ |
| SEM | Trường kinh tế | https://sem.hust.edu.vn/ | https://sem.hust.edu.vn/thu-ngo (2) | https://sem.hust.edu.vn/ban-giam-hieu | https://sem.hust.edu.vn/dao-tao-dai-hoc |
| SEP | Khoa vật lý kỹ thuật | https://sep.hust.edu.vn/ | https://sep.hust.edu.vn/gioi-thieu (4) | https://sep.hust.edu.vn/can-bo | https://sep.hust.edu.vn/dao-tao/he-dai-hoc |
| SME | Trường cơ khí | https://sme.hust.edu.vn/vi/ | https://sme.hust.edu.vn/vi/about/thong-tin-chung-ve-truong-co-khi.html (2) | https://sme.hust.edu.vn/vi/organs/viewsearch/?q=&p=&oid=0 | https://sme.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/gioi-thieu-dao-tao-dai-hoc-19.html |
| SMSE | trường vật liệu | https://smse.hust.edu.vn/ | https://smse.hust.edu.vn/vi/about/thong-tin-chung-ve-truong-vat-lieu.html (2) | https://smse.hust.edu.vn/vi/organs/ | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/ |
| SOFL | Khoa ngoại ngữ | https://sofl.hust.edu.vn/ | https://sofl.hust.edu.vn/thu-ngo (4) | https://sofl.hust.edu.vn/danh-muc-can-bo8<br>https://sofl.hust.edu.vn/danh-muc-can-bo7<br>https://sofl.hust.edu.vn/danh-muc-can-bo6<br>https://sofl.hust.edu.vn/danh-muc-can-bo5 | https://sofl.hust.edu.vn/web/vien-ngoai-ngu/dao-tao |
| SOICT | Trường CNTT và TT | https://soict.hust.edu.vn/ | https://soict.hust.edu.vn/category/gioi-thieu (12) | https://soict.hust.edu.vn/can-bo | https://soict.hust.edu.vn/category/dao-tao/he-dai-hoc |

## 4. 68 ngành đào tạo 2026

Cột **Trang giới thiệu** là nguồn của `RAG nganh_dao_tao` (151 chunk), `program_overview_2026.csv`, `tuition_2026.csv` và `data/programs/<mã>.json`. Cột **CTĐT** là link chương trình đào tạo trên web Trường/Khoa (`curriculum_url`).

| # | Mã | Tên ngành | Trường/Khoa | Trang giới thiệu (ts.hust.edu.vn) | CTĐT |
| --: | --- | --- | --- | --- | --- |
| 1 | ED2 | Công nghệ giáo dục | Khoa KH&CN Giáo dục | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-giao-duc | https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/chuong-trinh-dt-cong-nghe-giao-duc-178281.html |
| 2 | ED3 | Quản lý giáo dục | Khoa KH&CN Giáo dục | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/quan-ly-giao-duc | https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/chuong-trinh-dao-tao-cu-nhan-quan-ly-giao-duc-214985.html |
| 3 | ED5 | Tâm lý học công nghiệp và tổ chức (mới) | Khoa KH&CN Giáo dục | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tam-ly-hoc-cong-nghiep-va-to-chuc | https://fed.hust.edu.vn/vi/dao-tao/dai-hoc/chuong-trinh-dao-tao-tam-ly-hoc-cong-nghiep-va-to-chuc-214989.html |
| 4 | FL1 | Tiếng Anh KHKT và Công nghệ | Khoa Ngoại ngữ | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tieng-anh-khoa-hoc-ky-thuat-va-cong-nghe | https://sofl.hust.edu.vn/nganh-fl1 |
| 5 | FL2 | Tiếng Anh chuyên nghiệp quốc tế | Khoa Ngoại ngữ | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tieng-anh-chuyen-nghiep-quoc-te | https://sofl.hust.edu.vn/nganh-fl2 |
| 6 | FL3 | Tiếng Trung Khoa học và Công nghệ | Khoa Ngoại ngữ | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tieng-trung-khoa-hoc-va-cong-nghe | https://sofl.hust.edu.vn/nganh-fl3 |
| 7 | FL4 | Tiếng Hàn Khoa học và Công nghệ (mới) | Khoa Ngoại ngữ | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tieng-han-khoa-hoc-va-cong-nghe | https://sofl.hust.edu.vn/nganh-fl4 |
| 8 | MI-E22 | Khoa học tính toán cho các hệ thống thông minh (CT tiên tiến) (mới) | Khoa Toán - Tin | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/khoa-hoc-tinh-toan-cho-cac-he-thong-thong-minh-cttt | https://fami.hust.edu.vn/dao-tao/dao-tao-dai-hoc/ctdt-khoa-hoc-tinh-toan-cho-cac-he-thong-thong-minh/ |
| 9 | MI1 | Toán - Tin | Khoa Toán - Tin | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/toan-tin | https://fami.hust.edu.vn/dao-tao/dao-tao-dai-hoc/chuong-trinh-dao-tao-toan-tin/ |
| 10 | MI2 | Hệ thống thông tin quản lý | Khoa Toán - Tin | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/he-thong-thong-tin-quan-ly | https://fami.hust.edu.vn/dao-tao/dao-tao-dai-hoc/chuong-trinh-he-thong-thong-tin-quan-ly/ |
| 11 | TROY-IT | Khoa học máy tính - hợp tác với ĐH Troy (Hoa Kỳ) | Khoa Toán - Tin | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/khoa-hoc-may-tinh-dh-troy-hoa-ky | https://fami.hust.edu.vn/dao-tao/dao-tao-dai-hoc/chuong-trinh-dao-tao-khoa-hoc-may-tinh-dh-troy/ |
| 12 | PH1 | Vật lý kỹ thuật | Khoa Vật lý Kỹ thuật | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/vat-ly-ky-thuat | https://sep.hust.edu.vn/dao-tao/he-dai-hoc/chuong-trinh-vat-ly-ky-thuat-ma-tuyen-sinh-ph1.html |
| 13 | PH2 | Kỹ thuật hạt nhân | Khoa Vật lý Kỹ thuật | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-hat-nhan | https://sep.hust.edu.vn/dao-tao/he-dai-hoc/chuong-trinh-dao-tao-ky-thuat-hat-nhan-ph2.html |
| 14 | PH3 | Vật lý Y khoa | Khoa Vật lý Kỹ thuật | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/vat-ly-y-khoa | https://sep.hust.edu.vn/dao-tao/he-dai-hoc/chuong-trinh-dao-tao-dai-hoc-vat-ly-y-khoa-ph3.html |
| 15 | IT-E10 | Khoa học dữ liệu và Trí tuệ nhân tạo (CT tiên tiến) | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/khoa-hoc-du-lieu-va-tri-tue-nhan-tao | https://soict.hust.edu.vn/chuong-trinh-cu-nhan-khoa-hoc-du-lieu-va-tri-tue-nhan-tao-dsai-it-e10.html |
| 16 | IT-E15 | An toàn không gian số - Cyber Security (CT Tiên tiến) | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/an-toan-khong-gian-so-chuong-trinh-tien-tien | https://soict.hust.edu.vn/chuong-trinh-elitech-an-toan-khong-gian-so-cyber-security-it-e15.html |
| 17 | IT-E6 | Công nghệ thông tin (Việt - Nhật) | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-thong-tin-viet-nhat-chuong-trinh-tien-tien | https://soict.hust.edu.vn/chuong-trinh-ky-su-cong-nghe-thong-tin-viet-nam-nhat-ban-hedspi.html |
| 18 | IT-E7 | Công nghệ thông tin (Global ICT) | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-thong-tin-global-ict | https://soict.hust.edu.vn/chuong-trinh-ky-su-cong-nghe-thong-tin-toan-cau-global-ict.html |
| 19 | IT-EP | Công nghệ thông tin (Việt - Pháp) | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-thong-tin-viet-phap-chuong-trinh-tien-tien | https://soict.hust.edu.vn/chuong-trinh-elitech-cong-nghe-thong-tin-viet-phap.html |
| 20 | IT1 | CNTT: Khoa học Máy tính | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cntt-khoa-hoc-may-tinh | https://soict.hust.edu.vn/chuong-trinh-khoa-hoc-may-tinh-ma-tuyen-sinh-it1.html |
| 21 | IT2 | CNTT: Kỹ thuật Máy tính | Trường CNTT&TT | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cntt-ky-thuat-may-tinh | https://soict.hust.edu.vn/chuong-trinh-dao-tao-cong-nghe-thong-tin-ky-thuat-may-tinh-it2.html |
| 22 | HE1 | Kỹ thuật Nhiệt | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-nhiet | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-ky-thuat-nhiet-20.html |
| 23 | ME-E1 | Kỹ thuật Cơ điện tử (CT tiên tiến) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-co-dien-tu-chuong-trinh-tien-tien- | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-elitech/elitech-chuong-trinh-tien-tien-co-dien-tu-5.html |
| 24 | ME-GU | Cơ khí - Chế tạo máy - hợp tác với ĐH Griffith (Úc) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/co-khi-che-tao-may-dh-griffith-uc | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-quoc-te/chuong-trinh-hop-tac-dao-tao-quoc-te-co-khi-ctm-voi-dh-griffith-uc-3.html |
| 25 | ME-LUH | Cơ điện tử - hợp tác với ĐH Leibniz Hannover (Đức) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/co-dien-tu-dh-leibniz-hannover-duc | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-quoc-te/chuong-trinh-hop-tac-dao-tao-quoc-te-co-dien-tu-voi-dh-leibniz-hannover-duc-26.html |
| 26 | ME-NUT | Cơ điện tử - hợp tác với ĐH Công nghệ Nagaoka (Nhật Bản) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/co-dien-tu-dh-nagaoka-nhat-ban | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-quoc-te/chuong-trinh-hop-tac-dao-tao-quoc-te-co-dien-tu-voi-dh-nagaoka-nhat-ban-25.html |
| 27 | ME1 | Kỹ thuật Cơ điện tử | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-co-dien-tu | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-ky-thuat-co-dien-tu-4.html |
| 28 | ME2 | Kỹ thuật Cơ khí | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-co-khi | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-dao-tao-ky-thuat-co-khi-2.html |
| 29 | TE-E2 | Kỹ thuật Ô tô (CT tiên tiến) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-o-to-chuong-trinh-tien-tien | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-elitech/elitech-chuong-trinh-tien-tien-ky-thuat-o-to-22.html |
| 30 | TE-EP | Cơ khí hàng không (Chương trình Việt - Pháp PFIEV) | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/co-khi-hang-khong-chuong-trinh-viet-phap-pfiev | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-elitech/elitech-chuong-trinh-co-khi-hang-khong-chuong-trinh-viet-phap-pfiev-23.html |
| 31 | TE1 | Kỹ thuật Ô tô | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-o-to | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-ky-thuat-o-to-7.html |
| 32 | TE2 | Kỹ thuật Cơ khí động lực | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-co-khi-dong-luc | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-ky-thuat-co-khi-dong-luc-6.html |
| 33 | TE3 | Kỹ thuật Hàng không | Trường Cơ khí | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-hang-khong | https://sme.hust.edu.vn/vi/dao-tao/chuong-trinh-chuan/chuong-trinh-ky-thuat-hang-khong-24.html |
| 34 | BF-E12 | Kỹ thuật Thực phẩm (CT tiên tiến) | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-thuc-pham-chuong-trinh-tien-tien | https://scls.hust.edu.vn/vi/tuyen-sinh/bf-e12-ky-thuat-thuc-pham-elitech/ |
| 35 | BF-E19 | Kỹ thuật sinh học (CT tiên tiến) | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-sinh-hoc-chuong-trinh-tien-tien | https://scls.hust.edu.vn/vi/tuyen-sinh/bf-e19-ky-thuat-sinh-hoc-elitech/ |
| 36 | BF1 | Kỹ thuật Sinh học | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-sinh-hoc | https://scls.hust.edu.vn/vi/tuyen-sinh/bf1-ky-thuat-sinh-hoc/ |
| 37 | BF2 | Kỹ thuật Thực phẩm | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-thuc-pham | https://scls.hust.edu.vn/vi/tuyen-sinh/bf2-ky-thuat-thuc-pham/ |
| 38 | CH-E11 | Kỹ thuật Hóa dược (CT tiên tiến) | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-hoa-duoc-chuong-trinh-tien-tien | https://scls.hust.edu.vn/vi/tuyen-sinh/ch-e11-ky-thuat-hoa-duoc-elitech/ |
| 39 | CH-E20 | Hoá học Mỹ phẩm (CT tiên tiến) (mới) | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/hoa-hoc-my-pham-chuong-trinh-tien-tien | https://scls.hust.edu.vn/vi/tuyen-sinh/ch-e20-hoa-hoc-my-pham-elitech/ |
| 40 | CH1 | Kỹ thuật Hoá học | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-hoa-hoc | https://scls.hust.edu.vn/vi/tuyen-sinh/ch1-ky-thuat-hoa-hoc/ |
| 41 | CH2 | Hoá học | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/hoa-hoc | https://scls.hust.edu.vn/vi/tuyen-sinh/ch2-hoa-hoc/ |
| 42 | EV1 | Kỹ thuật Môi trường | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-moi-truong | https://scls.hust.edu.vn/vi/dao-tao/ky-thuat-moi-truong/ |
| 43 | EV2 | Quản lý Tài nguyên và Môi trường | Trường Hóa & KHSS | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/quan-ly-tai-nguyen-va-moi-truong | https://scls.hust.edu.vn/vi/dao-tao/quan-ly-tai-nguyen-va-moi-truong/ |
| 44 | EM-E13 | Phân tích kinh doanh (CT tiên tiến) | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/phan-tich-kinh-doanh-chuong-trinh-tien-tien | https://sem.hust.edu.vn/chuong-trinh-tien-tien-phan-tich-kinh-doanh |
| 45 | EM-E14 | Logistics và Quản lý chuỗi cung ứng (CT tiên tiến) | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/logistics-va-quan-ly-chuoi-cung-ung-chuong-trinh-tien-tien | https://sem.hust.edu.vn/chuong-trinh-tien-tien-logistics-va-quan-ly-chuoi-cung-ung |
| 46 | EM-E17 | Kế toán (CT tiên tiến) (mới) | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ke-toan-chuong-trinh-tien-tien | https://sem.hust.edu.vn/chuong-trinh-tien-tien-ke-toan |
| 47 | EM1 | Quản lý năng lượng | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/quan-ly-nang-luong | https://sem.hust.edu.vn/chuong-trinh-cu-nhan-quan-ly-nang-luong |
| 48 | EM2 | Quản lý công nghiệp | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/quan-ly-cong-nghiep | https://sem.hust.edu.vn/chuong-trinh-tich-hop-quan-ly-cong-nghiep |
| 49 | EM3 | Quản trị kinh doanh | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/quan-tri-kinh-doanh | https://sem.hust.edu.vn/chuong-trinh-tich-hop-quan-tri-kinh-doanh |
| 50 | EM5 | Tài chính - Ngân hàng | Trường Kinh tế | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tai-chinh-ngan-hang | https://sem.hust.edu.vn/chuong-trinh-cu-nhan-tai-chinh-ngan-hang |
| 51 | MS-E3 | Khoa học và kỹ thuật vật liệu (CT tiên tiến) | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/khoa-hoc-va-ky-thuat-vat-lieu-chuong-trinh-tien-tien | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-khoa-hoc-va-ky-thuat-vat-lieu-cttt-5.html |
| 52 | MS1 | Kỹ thuật Vật liệu | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-vat-lieu | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-ky-thuat-vat-lieu-4.html |
| 53 | MS2 | Kỹ thuật Vi điện tử và Công nghệ nano | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/chuong-trinh-ky-thuat-vi-dien-tu-va-cong-nghe-nano | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-ky-thuat-vi-dien-tu-va-cong-nghe-nano-7.html |
| 54 | MS3 | Công nghệ vật liệu Polyme và Compozit | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-vat-lieu-polyme-va-compozit | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-dao-tao-cong-nghe-vat-lieu-polyme-va-compozit-3.html |
| 55 | MS5 | Kỹ thuật in | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-in | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-ky-thuat-in-6.html |
| 56 | TX1 | Công nghệ Dệt - May | Trường Vật liệu | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/cong-nghe-det-may | https://smse.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/chuong-trinh-dao-tao-cong-nghe-det-may-2.html |
| 57 | EE-E18 | Hệ thống điện và năng lượng tái tạo (CT tiên tiến) | Trường Điện - Điện tử | http://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/he-thong-dien-va-nang-luong-tai-tao-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/ee-e18/ |
| 58 | EE-E8 | Kỹ thuật Điều khiển - Tự động hoá (CT tiên tiến) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-dieu-khien-tu-dong-hoa-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/ee-e8/ |
| 59 | EE-EP | Tin học công nghiệp và Tự động hóa (Chương trình Việt - Pháp PFIEV) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/tin-hoc-cong-nghiep-va-tu-dong-hoa-chuong-trinh-viet-phap-pfiev | https://seee.hust.edu.vn/vi/dao-tao/ee-ep/ |
| 60 | EE1 | Kỹ thuật Điện | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-dien | https://seee.hust.edu.vn/vi/dao-tao/ee1/ |
| 61 | EE2 | Kỹ thuật Điều khiển - Tự động hoá | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-dieu-khien-tu-dong-hoa | https://seee.hust.edu.vn/vi/dao-tao/ee2/ |
| 62 | ET-E16 | Truyền thông số và Kỹ thuật đa phương tiện (CT tiên tiến) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/truyen-thong-so-va-ky-thuat-da-phuong-tien-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/et-e16/ |
| 63 | ET-E4 | Kỹ thuật Điện tử - Viễn thông (CT tiên tiến) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-dien-tu-vien-thong-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/et-e4/ |
| 64 | ET-E5 | Kỹ thuật Y sinh (CT tiên tiến) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-y-sinh-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/et-e5-ky-thuat-y-sinh-cttt-287934.html |
| 65 | ET-E9 | Hệ thống nhúng thông minh và IoT (CT tiên tiến) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/he-thong-nhung-thong-minh-va-iot-chuong-trinh-tien-tien | https://seee.hust.edu.vn/vi/dao-tao/et-e9/ |
| 66 | ET-LUH | Điện tử - Viễn thông - hợp tác với ĐH Leibniz Hannover (Đức) | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/dien-tu-vien-thong-dh-leibniz-hannover-duc | https://seee.hust.edu.vn/vi/dao-tao/et-luh/ |
| 67 | ET1 | Kỹ thuật Điện tử - Viễn thông | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/dien-tu-va-vien-thong | https://seee.hust.edu.vn/vi/dao-tao/et1/ |
| 68 | ET2 | Kỹ thuật Y sinh | Trường Điện - Điện tử | https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc/ky-thuat-y-sinh | https://seee.hust.edu.vn/vi/dao-tao/dao-tao-dai-hoc/et2-ky-thuat-y-sinh-287932.html |

Đủ link CTĐT cho cả 68 ngành. Riêng ED5: trang ts.hust.edu.vn trỏ tới một bài báo nên dùng trang CTĐT trên web Khoa (fed.hust.edu.vn).

## 5. Link đã ghi trong `data/link.md` nhưng chưa dùng làm nguồn

| Link | Lý do |
| --- | --- |
| https://ts.hust.edu.vn/en/p/faqs | FAQ tuyển sinh — chưa crawl |
| https://ts.hust.edu.vn/tin-tuc/hoc-phi-dai-hoc-chinh-quy | Trang học phí — đã tải (`data/raw/tuition/hoc_phi_page.html`) để đối chiếu; học phí 2026 lấy từ 68 trang ngành |
| `03102023-quy-che-thi-tu-duy-dhbkhn.pdf` (818/QĐ-ĐHBK, 2023) | Quy chế thi ĐGTD cũ, đã thay bằng 10461/QĐ-ĐHBK |

## Kiểm tra

- Số link đang được dữ liệu dùng nhưng chưa có trong file này: **0**
