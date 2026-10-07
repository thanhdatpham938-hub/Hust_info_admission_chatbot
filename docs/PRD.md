# TÀI LIỆU YÊU CẦU SẢN PHẨM (PRD)

## HUST Info & Admission Assistant

**Phiên bản:** MVP v1.2 (đồng bộ với dataset đã thu thập) · 2026-09-23 · `dataset_version = 2026.1`

> **Vì sao có v1.2.** v1.1 được viết trước khi thu thập dữ liệu. Sau khi thu thập xong (20 bảng CSV + 573 chunk RAG), đối chiếu lại thì có 8 chỗ PRD mô tả không khớp thực tế — trong đó 3 chỗ nếu không sửa sẽ dẫn tới xây sai: 47% corpus RAG bị chính PRD khai là out-of-scope, AC4 đặt ra điều kiện không thể đạt với nguồn web, và Entity Resolution thiếu quy tắc khớp khiến 7 cặp ngành trùng tên bị bỏ qua bước hỏi lại. v1.2 sửa PRD theo dữ liệu thật, không sửa dữ liệu theo PRD.
>
> | Mục | Thay đổi |
> | --- | --- |
> | 3.1.A | Thêm bảng độ phủ thật theo từng năm — nêu rõ ô nào trống (chỉ tiêu 2024, tổ hợp 2024–2025); thêm học phí/thời gian đào tạo/bằng tốt nghiệp; thêm quy tắc bắt buộc về đơn vị học phí |
> | 3.C | Mở rộng danh sách đóng từ 5 lên 12 tài liệu, chia 2 nhóm; thêm nguyên tắc tách bảng số / văn xuôi |
> | 3.D | Bỏ mâu thuẫn "không thuộc RAG"; phân định rõ trường nào ở structured, phần nào ở RAG |
> | 4.7 | Nới mức chi tiết tối đa (thêm khối kiến thức đặc trưng, cơ hội việc làm…); ghi ngoại lệ 3 ngành mới chưa có link CTĐT |
> | 10.3 | Thêm 4 quy tắc khớp bắt buộc theo thứ tự; sửa ví dụ "Khoa học máy tính → IT1" thành ca phải hỏi lại |
> | 11.3 | Thay schema metadata bằng schema thật; thêm `dataset_version`, `collection_date` |
> | 12 + AC4 | Citation theo loại nguồn (PDF có số trang, web dùng `source_url`) |
> | 13.2 | Thêm fallback "thiếu dữ liệu theo năm" |
> | 15.1 | Thêm 10 bảng đã có dữ liệu; thêm cột `resolution` cho `entity_aliases`; ràng buộc tách bảng `programs` theo năm |
> | 20 | Ghi trạng thái thật của Tuần 1; chuyển việc soạn bộ test từ Tuần 6 lên Tuần 2 |
> | 26 | Chốt `dataset_version = 2026.1`; ghi rõ chưa có bản ghi nào `manual_verified` |

## 1. Tổng quan dự án (Executive Summary)

### 1.1. Bối cảnh

Đại học Bách khoa Hà Nội (HUST) có hệ thống thông tin tuyển sinh, đào tạo và quy chế học vụ với lượng thông tin lớn, phân bố trên nhiều loại tài liệu và nguồn khác nhau.

Đối với học sinh và phụ huynh, việc tra cứu thông tin tuyển sinh gặp khó khăn do: nhiều phương thức xét tuyển với thang điểm khác nhau; tên ngành có mã chính thức nhưng người dùng thường dùng tên viết tắt hoặc tên gọi thông dụng; dữ liệu điểm chuẩn thay đổi theo từng năm; thông tin về ngành, khoa/viện và chương trình học bị phân tán.

Đối với sinh viên HUST, các quy định về học vụ, học phí, học bổng, cảnh báo học tập và thủ tục hành chính thường nằm trong các văn bản dài, khiến việc tìm kiếm mất nhiều thời gian.

### 1.2. Vấn đề cần giải quyết

Hệ thống cần cung cấp một giao diện hội thoại thống nhất để người dùng có thể: tra cứu dữ liệu tuyển sinh có cấu trúc (kể cả so sánh nhiều ngành/năm/phương thức); hỏi đáp quy chế từ tài liệu chính thức có trích dẫn; tra cứu thông tin Khoa/Viện; dùng tên viết tắt/tên thông dụng thay mã chính thức; hỏi liên tiếp không cần lặp lại ngữ cảnh; và biết nên tìm thông báo mới nhất ở đâu khi hệ thống chưa hỗ trợ trực tiếp.

### 1.3. Giải pháp

Xây dựng **HUST Info & Admission Assistant**, một AI chatbot dùng kiến trúc **LangGraph-based Agentic Workflow**, kết hợp:

- **Structured Retrieval:** PostgreSQL cho dữ liệu tuyển sinh và thông tin Khoa/Viện.
- **Unstructured Retrieval / RAG:** Qdrant hoặc Pinecone cho tài liệu quy chế.

Một Router xác định loại yêu cầu rồi chuyển tới tool/workflow phù hợp; các tool giao tiếp trực tiếp qua function calling nội bộ (xem mục 7 — không dùng MCP cho MVP).

```text
                         USER
                           │
                           ▼
                    ┌──────────────┐
                    │   Router     │
                    │    Agent     │
                    └──────┬───────┘
                           │
         ┌───────────┬─────┼─────┬───────────┐
         │           │     │     │           │
         ▼           ▼     ▼     ▼           ▼
    Admission   University  RAG  Clarification Announcement
       Tool      Info Tool  Tool     Node        (link-only)
         │           │       │
         ▼           ▼       ▼
     PostgreSQL  PostgreSQL Vector DB
         │           │       │
         └───────────┼───────┘
                      ▼
               ┌──────────────┐
               │ Synthesizer  │
               └──────┬───────┘
                       ▼
                     USER
```

## 2. Mục tiêu sản phẩm (Product Goals)

### 2.1. Mục tiêu chính

Xây dựng một chatbot cung cấp thông tin HUST chính xác, có nguồn kiểm chứng, hỗ trợ hội thoại nhiều lượt.

### 2.2. Mục tiêu cụ thể

**Mục tiêu 1 — Tra cứu tuyển sinh.** Hỗ trợ tra cứu dữ liệu tuyển sinh 2024–2026 (điểm chuẩn, chỉ tiêu, tổ hợp môn, mã ngành, tên ngành, phương thức xét tuyển) qua 3 nhóm phương thức: Xét tuyển tài năng (thang 100), Đánh giá tư duy (thang 100), Điểm thi tốt nghiệp THPT (thang 30). **Hỗ trợ truy vấn nhiều thực thể trong một câu hỏi** (ví dụ so sánh 2–3 ngành/năm/phương thức cùng lúc), giới hạn tối đa 3 thực thể mỗi chiều để đảm bảo độ chính xác.

**Mục tiêu 2 — Entity Resolution.** Cho phép dùng mã ngành, tên ngành, tên viết tắt, tên gọi thông dụng, một số biến thể chính tả/kiểu chữ (VD: "IT1", "CNTT", "Khoa học máy tính", "Computer Science" → cùng một thực thể). Khi có nhiều khả năng ánh xạ gần nhau về độ tin cậy, hệ thống **không tự chọn** mà hỏi lại người dùng để xác nhận trước khi truy vấn dữ liệu.

**Mục tiêu 3 — RAG quy chế.** Cho phép hỏi đáp về cảnh báo học tập, học phí, học bổng, chuẩn đầu ra tiếng Anh, bảo lưu, thôi học, thủ tục học vụ, quy định sinh viên — dựa trên một danh sách tài liệu chính thức đã xác định trước (xem mục 3.C).

**Mục tiêu 4 — Thông tin Khoa/Viện.** Cung cấp tên, địa chỉ, bộ môn trực thuộc, ngành đào tạo, mô tả ngắn chương trình liên quan, thông tin liên hệ — dưới dạng dữ liệu có cấu trúc (không qua RAG). Với thông báo/sự kiện mới nhất của từng Khoa/Viện (nội dung thay đổi liên tục), MVP chỉ cung cấp link kênh thông tin chính thức, không cố trả lời nội dung cụ thể.

**Mục tiêu 5 — Citation.** Câu trả lời dùng dữ liệu từ RAG phải kèm nguồn tối thiểu: tên tài liệu, điều/mục liên quan, số trang; kèm URL nguồn chính thức nếu có.

**Mục tiêu 6 — Multi-turn Context.** Hệ thống duy trì thông tin quan trọng từ các lượt trước (VD: hỏi tiếp "Thế còn năm 2025?" sau khi đã hỏi điểm chuẩn IT1). Context chỉ được giữ lại khi câu hỏi mới có tham chiếu ngầm định (đại từ, "ngành này", "năm đó"...); nếu không, state cũ không được mang sang câu hỏi tiếp theo (chi tiết quy tắc reset ở mục 14).

**Mục tiêu 7 — Safety & Fallback.** Hệ thống không tự tạo dữ liệu khi thiếu bằng chứng đáng tin cậy. Khi không tìm thấy dữ liệu, dữ liệu ngoài phạm vi, retriever không đủ tin cậy, hoặc query yêu cầu thông tin cá nhân/nằm ngoài danh sách tài liệu đã định — hệ thống thực hiện fallback phù hợp, không suy đoán.

## 3. Phạm vi sản phẩm (Scope)

### 3.1. In-Scope

**A. Admission Information**

- Truy vấn nhiều thực thể (so sánh) trong một câu hỏi, tối đa 3 chương trình / 3 năm / 3 phương thức mỗi truy vấn.
- Độ phủ thực tế của dataset (chốt 2026-09-23) — bot **chỉ được trả lời trong phạm vi này**, ô trống phải rơi vào fallback "không có dữ liệu" ở mục 13.2, không được suy đoán:

| Loại dữ liệu | 2024 | 2025 | 2026 | Ghi chú |
| --- | --- | --- | --- | --- |
| Điểm chuẩn (4 phương thức, thang 30 & 100) | ✔ 64 ngành | ✔ 65 ngành | ✔ 68 ngành | 660 dòng long-format |
| Mã ngành / tên ngành | ✔ | ✔ | ✔ | Tách bảng theo năm vì danh mục ngành đổi hằng năm |
| Chỉ tiêu tuyển sinh | ✖ | ✔ | ✔ | Phụ lục 1 đề án 2024 không công bố dạng bóc được — đã chốt bỏ |
| Phương thức xét tuyển theo ngành | ✖ | ✔ | ✔ | |
| Tổ hợp môn chi tiết theo ngành | ✖ | ✖ | ✔ | 2024–2025 chỉ có tổ hợp đại diện đi kèm từng dòng điểm chuẩn |
| Học phí theo ngành | — | — | ✔ 68/68 | Đơn vị **không đồng nhất**: 63 ngành tính /năm, 5 ngành quốc tế tính /học kỳ |
| Thời gian đào tạo, bằng tốt nghiệp, ngôn ngữ đào tạo | — | — | ✔ 68/68 | |

- Ngoài ra dataset có các bảng dùng chung không gắn theo năm: học phí theo tín chỉ, lệ phí xét tuyển/thi ĐGTD, quy đổi điểm chứng chỉ quốc tế, quy đổi CEFR.
- **Quy tắc bắt buộc về học phí:** mọi câu trả lời về học phí phải kèm đơn vị (/năm hay /học kỳ) và năm áp dụng. Các chương trình hợp tác quốc tế tính theo học kỳ, riêng TROY có 3 học kỳ/năm — gộp nhầm đơn vị sẽ sai số tiền tới 3 lần.

**B. Entity Resolution**

- Alias ngành, alias Khoa/Viện, tên viết tắt, tên thông dụng.
- Chuẩn hóa chữ hoa/thường, chuẩn hóa dấu tiếng Việt, fuzzy matching ở mức phù hợp.
- Alias tiếng Anh cho tên ngành/khoa phổ biến (chỉ ở tầng ánh xạ thực thể — xem giới hạn ngôn ngữ ở mục 4.6).
- Bước xử lý mơ hồ (ambiguity): khi nhiều candidate có độ tin cậy gần nhau, trả về câu hỏi làm rõ thay vì tự chọn.

**C. RAG — danh sách tài liệu MVP (đóng, không mở rộng trong phạm vi MVP)**

Danh sách dưới đây là **corpus thực tế đã thu thập và chunk xong** (622 chunk gốc, ~595.000 ký tự, 100% chunk có `source_url`; sau chuẩn hoá metadata 2026-09-27 còn **637 chunk** trong `data/rag/normalized/` do tách 11 chunk dài — xem `PLAN - Metadata Design (v2).md`). Bản v1.1 trước đây chỉ liệt kê 5 tài liệu nhóm 1; trong quá trình thu thập đã bổ sung nhóm 2 theo yêu cầu phạm vi thực tế (kỳ thi ĐGTD, xét tuyển tài năng, thông tin ngành) — nay đưa vào PRD cho khớp.

*Nhóm 1 — Văn bản quy chế, quy định (341 chunk):*

| # | Tài liệu | Chunk | Cách chunk |
| --: | --- | --: | --- |
| 1 | Quy chế đào tạo đại học chính quy (QCDT 2025, 5445/QĐ-ĐHBK) | 76 | Theo Điều → khoản |
| 2 | Sổ tay sinh viên 2026 | 206 | Theo tiêu đề trang › tiêu đề mục; `page_no` = số trang **in** (không phải trang PDF). Trích lại 2026-09-26 bằng `scripts/sotay_to_rag.py` (bản in dàn 2 trang/1 trang PDF, nhiều cột); 22 trang infographic/bảng không kẻ ô chép tay ở `data/raw/sotay_overrides/` |
| 3 | Đề án tuyển sinh 2024 / 2025 / 2026 | 37 / 7 / 8 | Theo mục đánh số |
| 4 | Quy định xét cấp học bổng khuyến khích học tập (KKHT) | 7 | Theo Điều |
| 5 | Quy định cảnh báo học tập, buộc thôi học | — | Nằm trong QCDT (Điều 19, Điều 25), không phải file rời |

*Nhóm 2 — Tài liệu tuyển sinh & thông tin ngành (281 chunk):*

| # | Tài liệu | Chunk | Lý do thuộc scope |
| --: | --- | --: | --- |
| 6 | Trang giới thiệu 68 ngành đào tạo (ts.hust.edu.vn) | 151 | Nguồn duy nhất có mô tả ngành, đối tượng phù hợp, cơ hội việc làm, liên hệ tư vấn — phục vụ mục tiêu 4 |
| 7 | Quy chế thi Đánh giá tư duy (10461/QĐ-ĐHBK, 2024) | 35 | ĐGTD là 1 trong 3 phương thức xét tuyển chính, không thể trả lời phương thức mà thiếu quy chế thi |
| 8 | Giới thiệu 10 Trường/Khoa | 38 | Phần văn xuôi; dữ liệu tra cứu được vẫn nằm ở bảng `faculties` (xem D) |
| 9 | Các bài công bố trên trang tuyển sinh (điểm chuẩn, giới thiệu TSA, cẩm nang TSA) | 27 | Phần **văn bản** giải thích cách tính điểm, điểm ưu tiên, nhận xét phổ điểm — bảng số đã tách sang PostgreSQL |
| 10 | Quy định xét tuyển tài năng (XTTN) 2026 | 15 | XTTN chiếm 2/4 phương thức trong bảng điểm chuẩn |
| 11 | Quyết định học phí theo tín chỉ | 1 | Quy tắc đặc biệt (học kỳ hè ×1,5; trần tăng 10%/năm) |
| 12 | **Quy định về chuẩn ngoại ngữ: bản K71 (10828/QĐ-ĐHBK, 07/9/2026) và bản K70 (10728/QĐ-ĐHBK, 26/9/2025)** | 14 | Bổ sung 2026-09-24. QCDT chỉ ghi "đạt chuẩn ngoại ngữ đầu ra" **không kèm con số**; con số nằm ở văn bản này. Không có nó thì mọi câu hỏi về TOEIC/IELTS để tốt nghiệp đều không trả lời được |

Hai bản K70/K71 được giữ **cả hai**: bản K71 chỉ áp dụng từ khóa 71, còn K70 trở về trước — tức phần lớn sinh viên đang học — vẫn theo bản cũ. Hỏi về chuẩn đầu ra mà chưa rõ khóa thì phải hỏi lại, không được chọn bừa một bản.

Tài liệu ngoài 12 mục trên → out-of-scope cho MVP, ghi nhận vào backlog v2.

**Cách tài liệu 12 được phát hiện — nên lặp lại định kỳ.** Nó không lộ ra từ việc rà
danh sách tài liệu, mà từ việc **truy các tham chiếu treo**: văn bản trong corpus dẫn
tới văn bản khác mà mình không có. `scripts/check_dangling_refs.py` tự động hoá phép
kiểm này. Phép đo độ phủ theo từ khoá KHÔNG bắt được loại thiếu này — gõ "TOEIC" vẫn ra
19 chunk, nhưng 17 trong số đó là bảng điểm thưởng IELTS **khi xét tuyển**, không phải
chuẩn tốt nghiệp. Đếm số lần xuất hiện không thay được việc đọc nghĩa.

**Nguyên tắc phân tách bảng số / văn xuôi (áp dụng cho mọi nguồn):** khi một tài liệu vừa có bảng vừa có văn xuôi, **bảng số đi vào PostgreSQL, văn xuôi đi vào RAG, không để trùng ở cả hai nơi** — nếu trùng, bot sẽ trả lời cùng một câu hỏi theo hai cách khác nhau. Ngược lại, khi bóc bảng thì **phần văn xuôi xung quanh bảng vẫn phải được giữ lại**, không được lấy bảng rồi bỏ phần diễn giải.

**D. University Info**

Dữ liệu **tra cứu được** (tên, mã, địa chỉ, liên hệ, link, mô tả ngắn) nằm ở tầng structured; phần **văn xuôi dài** (lịch sử, thế mạnh, định hướng của Trường/Khoa) nằm ở RAG mục C.9. Bản v1.1 ghi "không thuộc RAG" là chưa chuẩn — hai tầng này bổ sung cho nhau chứ không loại trừ:

| Trường dữ liệu | Tầng | Nguồn |
| --- | --- | --- |
| Tên Khoa/Viện, bộ môn trực thuộc, danh sách ngành | structured — bảng `faculties` | `data/faculty/<mã>/info.json` |
| Địa chỉ, hotline, email, website | structured — bảng `faculties` | Mục "Đơn vị quản lý" trên 68 trang ngành |
| `official_channel_url` (phục vụ ANNOUNCEMENT_QUERY) | structured — bảng `faculties` | Đã có đủ 10/10 Trường/Khoa |
| Mô tả ngắn ngành + link CTĐT | structured — bảng `programs` | 68/68 có mô tả; 65/68 có link CTĐT |
| Giới thiệu dài về Trường/Khoa | RAG | mục C.9 |

**Router phải ưu tiên tầng structured trước.** Chỉ khi câu hỏi mang tính mô tả/kể chuyện (vd "Trường CNTT&TT có thế mạnh gì?") mới chuyển sang RAG. Hỏi địa chỉ, số điện thoại, link mà đi qua RAG là sai tầng, vì kết quả sẽ không ổn định.

**E. Conversation**

- Multi-turn context, session-based conversation, thread ID, context persistence có quy tắc reset (mục 14).

**F. Citation**

- Document title, article/section, page number, source URL nếu có.

**G. Guardrails**

- Out-of-domain detection, tách 2 nhóm: dữ liệu trường khác (OTHER\_UNIVERSITY) và câu hỏi ngoài chủ đề chung (GENERAL\_OFF\_TOPIC).
- Low-retrieval-score fallback, missing-data fallback.
- Clarification khi entity mơ hồ (không tự suy đoán dữ liệu tuyển sinh).

## 4. Ngoài phạm vi (Out-of-Scope)

MVP **không triển khai** các chức năng sau:

### 4.1. Cá nhân hóa

Không yêu cầu đăng nhập SSO, tra cứu CPA cá nhân, thời khóa biểu cá nhân, học phí cá nhân, điểm cá nhân, hồ sơ sinh viên.

### 4.2. Tư vấn quyết định

Hệ thống không phán đoán đỗ/trượt, không đánh giá khả năng đỗ, không đưa lời khuyên chọn ngành, không xếp hạng ngành theo mức độ phù hợp cá nhân, không quyết định thay người dùng. Ví dụ không hỗ trợ: "24 điểm thì chắc chắn đỗ ngành nào?", "Em nên chọn ngành nào?". Hệ thống chỉ cung cấp thông tin khách quan đã công bố (điểm chuẩn, phương thức, chỉ tiêu, đặc điểm chương trình).

### 4.3. Real-time Scraping

Không triển khai crawler thời gian thực. Dataset được thu thập → kiểm tra → chuẩn hóa → version hóa → nạp vào hệ thống. Thông tin mới chỉ cập nhật sau khi dữ liệu được xác minh và ingest lại.

### 4.4. Dữ liệu ngoài HUST

Không hỗ trợ dữ liệu tuyển sinh chi tiết của trường khác. Ví dụ: "Điểm chuẩn UET năm 2025?" → out-of-domain (nhóm OTHER\_UNIVERSITY).

### 4.5. Thông báo / tin tức thời gian thực của Khoa/Viện

MVP không tra cứu nội dung thông báo, sự kiện, lịch cập nhật thường xuyên của các Khoa/Viện — bản chất dữ liệu thay đổi liên tục không phù hợp với pipeline ingestion theo batch (mục 4.3). Thay vào đó, hệ thống cung cấp link kênh thông tin chính thức (website/fanpage) của từng Khoa/Viện để người dùng tự tra cứu (intent ANNOUNCEMENT\_QUERY, xem mục 10.1). Việc crawl định kỳ để hiển thị tiêu đề thông báo mới nhất là backlog v2, cần đánh giá tính khả thi crawl ổn định theo từng nguồn trước khi triển khai.

### 4.6. Phạm vi ngôn ngữ

Ngôn ngữ hội thoại chính: tiếng Việt. Alias tiếng Anh chỉ được hỗ trợ ở tầng Entity Resolution (tên ngành/khoa phổ biến ánh xạ về entity), không hỗ trợ toàn bộ hội thoại bằng tiếng Anh trong MVP. Câu hỏi thuần tiếng Anh → fallback gợi ý hỏi lại bằng tiếng Việt.

### 4.7. Chương trình đào tạo chi tiết

MVP **không** cung cấp khung chương trình, danh sách môn học, tín chỉ từng học kỳ.

Mức chi tiết tối đa mà MVP trả lời (đã có đủ cho 68/68 ngành): mô tả ngành, đối tượng phù hợp, **khối kiến thức đặc trưng**, cơ hội việc làm, thời gian đào tạo, bằng tốt nghiệp, học phí. Đây rộng hơn mức "1-2 câu" ghi ở bản v1.1, vì nguồn trang ngành chính thức cung cấp sẵn các mục này.

Khi người dùng hỏi sâu hơn (môn học cụ thể, số tín chỉ từng kỳ), hệ thống trả về link CTĐT chính thức theo nguyên tắc link-only như mục 4.5. **Ngoại lệ:** 3 ngành mới mở 2026 (CH-E20, ED5, FL4) chưa có link CTĐT công bố — với 3 ngành này phải trả lời rõ là chưa có, kèm link trang ngành và kênh liên hệ của Trường quản lý, không được trỏ sang link của ngành khác.

## 5. Người dùng mục tiêu (User Personas)

### 5.1. Học sinh lớp 12

**Nhu cầu:** tìm điểm chuẩn, so sánh các phương thức xét tuyển, tìm mã ngành, tra cứu chỉ tiêu, tìm hiểu ngành đào tạo. **Pain points:** nhầm thang điểm 30 và 100; không nhớ mã ngành; khó tìm thông tin trong nhiều tài liệu.

### 5.2. Phụ huynh

**Nhu cầu:** tra cứu phương thức tuyển sinh, tìm điểm chuẩn, tìm thông tin ngành, tìm thông tin Khoa/Viện. **Pain points:** thông tin tuyển sinh có nhiều thuật ngữ; khó xác định nguồn thông tin chính thức.

### 5.3. Sinh viên HUST

**Nhu cầu:** tra cứu quy chế, học bổng, cảnh báo học tập, học phí, bảo lưu, thông tin Khoa/Viện, thủ tục học vụ. **Pain points:** văn bản dài; khó xác định điều khoản liên quan; không biết thông tin nằm ở tài liệu nào.

## 6. User Stories

**US1 — Tra cứu điểm chuẩn.** Học sinh hỏi "Điểm chuẩn Đánh giá tư duy ngành IT1 năm 2025 là bao nhiêu?" → nhận điểm chuẩn chính xác trên thang 100, kèm ngành, mã ngành, năm, phương thức, thang điểm, nguồn.

**US2 — Alias Mapping.** "Điểm ngành Toán Tin năm ngoái?" → Entity Resolution ánh xạ "Toán Tin" → MI1, sau đó truy vấn dữ liệu năm trước đó trong phạm vi dataset.

**US3 — Multi-turn.** "Điểm IT1 năm 2024?" rồi "Thế còn 2025?" → hệ thống hiểu `program=IT1, year=2025, query_type=admission_score` mà không cần nhập lại IT1.

**US4 — Citation.** "Điều kiện nhận học bổng loại A?" → trả lời kèm nguồn (VD: Sổ tay Sinh viên 2025–2026, Điều 15, Trang 42).

**US5 — Out-of-domain.** "Điểm chuẩn UET năm 2025?" → hệ thống trả lời phạm vi hỗ trợ hiện tại là HUST, không tự cung cấp dữ liệu trường khác.

**US6 — Không tìm thấy dữ liệu.** "Điểm chuẩn IT1 năm 2020?" (ngoài phạm vi dataset) → "Không tìm thấy dữ liệu năm 2020 trong phạm vi dữ liệu hiện tại." Hệ thống không tự suy đoán hoặc nội suy điểm chuẩn.

**US7 — So sánh nhiều ngành (mới).** "Điểm chuẩn IT1 và IT2 năm 2025 chênh nhau bao nhiêu?" → Admission Tool nhận input dạng danh sách, trả về kết quả từng ngành và phần chênh lệch được Synthesizer tính lại từ số liệu đã truy xuất (không phải LLM tự ước lượng).

**US8 — Hỏi thông báo Khoa/Viện (mới).** "Viện CNTT có thông báo gì mới không?" → hệ thống không cố trả lời nội dung, mà trả về link kênh thông tin chính thức của Viện CNTT kèm ghi chú lý do (nội dung cập nhật thường xuyên, MVP chưa hỗ trợ tra cứu trực tiếp).

## 7. Kiến trúc kỹ thuật (Technical Architecture)

### 7.1. Tổng quan

Kiến trúc: **LLM Router + Tool Calling + Hybrid Retrieval + Stateful Conversation**.

```text
┌───────────────────────────────────────────┐
│                 Next.js UI                │
│       Chat / Markdown / Citation          │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│               FastAPI Backend              │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│             LangGraph Workflow             │
│       ┌──────────────┐                      │
│       │ Router Agent │                      │
│       └──────┬───────┘                      │
│   ┌────────┬─┴─┬────────┬──────────┐        │
│   ▼        ▼   ▼        ▼          ▼        │
│Admission University RAG Clarification Announcement│
│  Tool     Tool     Tool    Node      (link) │
└─────┼────────┼──────┼───────────────────────┘
      ▼        ▼      ▼
 PostgreSQL PostgreSQL Qdrant
      │        │       │
      └────┬───┴───┬───┘
           ▼
    Synthesizer Node
           ▼
        Response
```

### 7.2. Quyết định kiến trúc: không dùng MCP

MVP dùng **function calling nội bộ** (LangChain/LangGraph tool binding + Pydantic schema) thay vì MCP (Model Context Protocol). MCP có giá trị khi cần chuẩn hóa giao thức cho nhiều client khác nhau cùng dùng chung tool, hoặc khi tận dụng MCP server có sẵn của bên thứ ba. Hệ thống này là kiến trúc khép kín (một backend, một workflow, gọi tool của chính nó) nên MCP chỉ thêm một lớp giao thức trung gian không cần thiết — tăng độ trễ (ảnh hưởng P95 TTFT ở mục 21) và bề mặt vận hành mà không giải quyết vấn đề gì đang tồn tại. MCP được để ngỏ cho v2 nếu phát sinh nhu cầu chia sẻ tool cho nhiều ứng dụng khác ngoài chatbot này.

## 8. Frontend

**Technology:** Next.js, App Router, TailwindCSS, React, react-markdown.

**Chức năng:** chat interface, streaming response, markdown, table rendering, citation display, loading state, error state, fallback message, clarification prompt (hiển thị các lựa chọn khi entity mơ hồ).

## 9. Backend

**Technology:** Python 3.11+, FastAPI, Pydantic, LangChain, LangGraph.

Backend chịu trách nhiệm: API; session ở mức session ID; agent workflow; tool execution; RAG pipeline; database access; streaming response; error handling.

## 10. Agent Workflow

### 10.1. Router Agent

Router xác định intent, không trực tiếp trả lời nội dung — chỉ quyết định workflow tiếp theo.

```text
ADMISSION_QUERY
REGULATION_QUERY
UNIVERSITY_INFO_QUERY
ANNOUNCEMENT_QUERY        (mới — thông báo Khoa/Viện, trả link)
CLARIFICATION_NEEDED      (mới — entity/intent mơ hồ)
OUT_OF_DOMAIN
  ├── OTHER_UNIVERSITY    (mới — dữ liệu trường khác)
  └── GENERAL_OFF_TOPIC   (mới — không liên quan HUST)
UNKNOWN
```

Ví dụ: "Điểm IT1 năm 2025?" → ADMISSION\_QUERY; "Điều kiện cảnh báo học tập?" → REGULATION\_QUERY; "Viện CNTT ở đâu?" → UNIVERSITY\_INFO\_QUERY; "Viện CNTT có thông báo gì mới?" → ANNOUNCEMENT\_QUERY; "Điểm chuẩn UET năm 2025?" → OTHER\_UNIVERSITY; "Hôm nay thời tiết thế nào?" → GENERAL\_OFF\_TOPIC.

### 10.2. Admission Tool

Xử lý truy vấn có cấu trúc, hỗ trợ nhiều thực thể (so sánh) trong một lượt.

Input:

```text
program: List[str]   (tối đa 3)
year: List[int]      (tối đa 3)
method: List[str]    (tối đa 3)
```

Output (mỗi tổ hợp hợp lệ trả về 1 record):

```json
{
  "program_code": "IT1",
  "program_name": "...",
  "year": 2025,
  "method": "TSA",
  "score": 82.10,
  "scale": 100
}
```

Nếu vượt quá 3 thực thể mỗi chiều → fallback: "Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác." Dữ liệu lấy trực tiếp từ PostgreSQL; mọi phép so sánh/tính chênh lệch được thực hiện trên số liệu đã truy xuất, không để LLM tự ước lượng.

### 10.3. Entity Resolution Module

```text
User Query
    ↓
Text Normalization (bỏ dấu, thường hoá, gộp khoảng trắng)
    ↓
[B1] Lọc theo NĂM đang hỏi  — bỏ alias/mã không tồn tại ở năm đó
    ↓
[B2] Exact Alias Lookup     — khớp đúng chuỗi đã chuẩn hoá → dừng, KHÔNG xét tiếp
    ↓
[B3] Substring / Fuzzy      — chỉ chạy khi B2 không ra kết quả
    ↓
Candidate Entity
    ↓
Đọc cột `resolution` của alias:
  unique  → Validated Entity, trả lời thẳng
  clarify → KHÔNG tự chọn, trả tối đa 3 candidate,
            Router chuyển CLARIFICATION_NEEDED
  group   → liệt kê các ngành thuộc nhóm (lọc `program_group`)
```

**Bốn quy tắc khớp bắt buộc cài đúng thứ tự trên.** Đây không phải gợi ý tối ưu mà là điều kiện đúng/sai — đã kiểm chứng trên toàn bộ 112 alias:

1. **Lọc năm trước tiên.** "Accounting" hỏi năm 2026 phải ra EM-E17; nếu không lọc năm sẽ ra EM4 (ngành đã ngừng tuyển sau 2025).
2. **Khớp chính xác thắng tuyệt đối.** Không có quy tắc này thì "Chemistry" bị "Cosmetic Chemistry" nuốt, "Mechanical Engineering" kéo theo cả ME-GU và TE2.
3. **Chỉ lùi về khớp chuỗi con khi B2 trượt.**
4. **Alias loại `abbrev` chỉ tham gia B2.** Viết tắt ngắn như `BA` nếu cho khớp chuỗi con sẽ dính 13 ngành (Bách khoa, bán dẫn, Nagaoka, Business Administration…).

Nguồn dữ liệu: `data/processed/entity_aliases.csv` — 174 dòng, 112 alias, phủ 68/68 ngành, gồm alias tiếng Anh, tên thông dụng, viết tắt, biến thể mã. Có script `validate_aliases.py` kiểm tính nhất quán và **mô phỏng lại đúng 4 quy tắc trên** để bắt lỗi khớp thừa/thiếu mỗi khi sửa file.

**Lưu ý ngược đời nhưng bắt buộc:** 7 cặp ngành trùng tên giữa hệ chuẩn và hệ tiên tiến (Kỹ thuật Ô tô TE1/TE-E2, Kỹ thuật Y sinh ET2/ET-E5, …) **phải khai báo tường minh trong bảng alias** dù tên đã có sẵn trong bảng `programs`. Lý do: quy tắc khớp chính xác sẽ dừng ngay ở mã hệ chuẩn và bỏ qua bước hỏi lại, khiến người hỏi về hệ tiên tiến nhận nhầm dữ liệu hệ chuẩn.

Ví dụ: "Toán Tin" → MI1 (unique); "Khoa học máy tính" → **IT1 + TROY-IT → hỏi lại** (không phải IT1 như bản v1.1 ghi, vì TROY-IT cũng tên là Khoa học máy tính). Entity Resolution ưu tiên dữ liệu deterministic trước khi dùng LLM fallback.

## 11. RAG Pipeline

### 11.1. Data Ingestion

Nguồn tài liệu: đúng danh sách đóng 11 mục ở mục 3.C — nhóm 1 là văn bản quy chế/quy định, nhóm 2 là tài liệu tuyển sinh và thông tin ngành. Không ingest tài liệu ngoài danh sách này trong phạm vi MVP.

Nguồn ở dạng scan không có lớp text (vd quy chế thi ĐGTD) được đọc bằng mô hình thị giác rồi chép lại thành Markdown, không dùng OCR riêng. Mọi chunk từ nguồn scan phải gắn `verification_status = vision_extracted` để về sau biết chỗ nào cần soát tay.

```text
PDF / Document
      ↓
Text Extraction
      ↓
Cleaning
      ↓
Metadata Extraction
      ↓
Header-based Chunking
      ↓
Embedding
      ↓
Vector Database
```

### 11.2. Chunking

Chunking ưu tiên theo cấu trúc H1 → H2 → H3, giữ trọn vẹn ngữ nghĩa từng quy định/điều khoản. Không chia nhỏ một điều khoản thành nhiều chunk khiến mất ngữ cảnh.

### 11.3. Metadata

Schema chunk thực tế (giữ tên trường tiếng Việt cho văn bản pháp quy vì `chương / điều / khoản` là 3 cấp khác nhau, gộp vào `article_no`/`section` như bản v1.1 sẽ mất một cấp):

```json
{
  "document_title": "Quy chế đào tạo 2025",
  "document_no":    "5445/QĐ-ĐHBK",
  "document_type":  "quy_che_dao_tao",
  "year":           2025,
  "chuong":         "III",
  "dieu_no":        "19",
  "khoan_no":       "2",
  "heading":        "Điều 19. Cảnh báo học tập",
  "page_no":        42,
  "source_url":     "https://...",
  "dataset_version":  "2026.1",
  "collection_date":  "2026-09-23",
  "verification_status": "vision_extracted"
}
```

Trường riêng cho từng loại nguồn: chunk giới thiệu ngành có thêm `program_code` + `program_name`; chunk giới thiệu Trường/Khoa có thêm `faculty_code`. Hai trường này cho phép lọc trước khi retrieval thay vì tìm theo ngữ nghĩa — hỏi về một ngành cụ thể thì lọc `program_code` luôn chính xác hơn.

**Bắt buộc:**

- `source_url` — 100% chunk phải có (hiện đã đạt 573/573).
- `page_no` — bắt buộc với chunk bóc từ PDF/scan; để trống với chunk từ trang web (trang web không có khái niệm số trang, đã có `source_url` thay thế).
- `dataset_version` + `collection_date` — bắt buộc trên **mọi** chunk, theo mục 26. Không có 2 trường này thì không xác định được bot đang chạy trên bộ dữ liệu nào khi điều tra lỗi.

Metadata phục vụ filtering, retrieval, citation, debugging.

## 12. Citation System

Đối với RAG response, hệ thống giữ lại thông tin nguồn từ retrieved chunks. LLM không được tự tạo citation — citation phải lấy từ metadata của document/chunk.

Citation hợp lệ = **Tên tài liệu + Vị trí + Đường dẫn về nguồn**. "Vị trí" và "đường dẫn" lấy theo loại nguồn, vì không phải nguồn nào cũng có số trang:

| Loại nguồn | Vị trí | Đường dẫn |
| --- | --- | --- |
| Văn bản pháp quy (PDF/scan) | Điều / khoản + số trang | `source_url` nếu có bản công bố |
| Sổ tay sinh viên | Tên mục + số trang | `source_url` |
| Trang web (ngành, tin tuyển sinh, giới thiệu Trường) | Tên mục trên trang | `source_url` — **bắt buộc** |

```text
Theo quy định hiện hành, ...

[Nguồn]
Quy định xét cấp học bổng KKHT
Điều 3. Tiêu chuẩn xét cấp học bổng — Trang 2
https://...
```

## 13. Confidence & Fallback

### 13.1. Nguyên tắc

Không dùng trực tiếp cosine similarity như xác suất confidence. Retrieval score chỉ là tín hiệu đánh giá chất lượng evidence; threshold được xác định qua tập validation.

### 13.2. Fallback Conditions

Fallback khi: không có kết quả retrieval phù hợp; retrieval score dưới threshold; không xác định được entity (và không đủ điều kiện để hỏi làm rõ); không có dữ liệu trong database; query ngoài phạm vi (OTHER\_UNIVERSITY / GENERAL\_OFF\_TOPIC); query thuộc ANNOUNCEMENT\_QUERY hoặc hỏi chương trình đào tạo chi tiết vượt quá mô tả ngắn (mục 4.7) — cả hai đều trả link chính thức thay vì nội dung.

Ví dụ:

```text
Không tìm thấy thông tin đủ tin cậy trong
nguồn dữ liệu hiện tại để trả lời câu hỏi này.
Bạn có thể kiểm tra thông tin tại nguồn chính thức
của Đại học Bách khoa Hà Nội.
```

**Fallback "thiếu dữ liệu theo năm" (bắt buộc, theo bảng độ phủ ở mục 3.1.A).** Dataset không phủ đều mọi năm, nên có những câu hỏi hợp lệ mà vẫn không có dữ liệu. Các trường hợp phải rơi vào fallback này thay vì suy đoán hoặc lấy tạm số của năm khác:

| Câu hỏi | Xử lý đúng |
| --- | --- |
| "Chỉ tiêu ngành IT1 năm 2024?" | Báo chưa có dữ liệu chỉ tiêu 2024, **chủ động đề xuất 2025/2026** là năm có dữ liệu |
| "Ngành TE1 năm 2024 xét những tổ hợp nào?" | Chỉ nêu tổ hợp đại diện kèm theo dòng điểm chuẩn, nói rõ chưa có danh sách tổ hợp đầy đủ cho 2024 |
| "Điểm chuẩn IT1 năm 2020?" | Ngoài phạm vi dataset 2024–2026, không nội suy |

Nguyên tắc chung: **nói rõ thiếu cái gì và có sẵn cái gì**, không trả lời cụt "không có dữ liệu" rồi dừng.

## 14. Multi-turn Context

LangGraph Checkpointer lưu state theo `thread_id`. State có thể chứa: `current_program, current_year, current_method, previous_intent, conversation_summary`.

Ví dụ:

```text
User: Điểm IT1 năm 2024?
State: program=IT1, year=2024

User: Thế còn 2025?
Router + Context: program=IT1, year=2025
```

### Quy tắc reset context (mới)

- Nếu Router xác định intent mới **không** tham chiếu đại từ ngầm định ("ngành này", "năm đó", "thế còn...") → không mang state cũ sang câu hỏi mới.
- Nếu câu hỏi có tham chiếu ngầm định nhưng state cũ thuộc nhóm intent khác (VD: state cũ là ADMISSION\_QUERY, câu hỏi mới là REGULATION\_QUERY có nhắc "ngành này") → chỉ mang entity (program), không mang method/year, và Router phải tự xác nhận entity đó còn hợp lệ trong ngữ cảnh mới (VD học bổng có áp dụng riêng theo ngành hay không) trước khi dùng.
- Khi entity đang ở trạng thái CLARIFICATION\_NEEDED (mục 10.3), state không được coi là "đã xác nhận" cho tới khi người dùng chọn 1 candidate cụ thể.

## 15. Database Design

### 15.1. PostgreSQL — bảng chính

**`programs`**: program\_id, program\_code, program\_name, faculty\_id, short\_description, curriculum\_url (link CTDT chính thức, phục vụ fallback ở mục 4.7).

**`admission_methods`**: method\_id, method\_code, method\_name, scale.

**`admission_scores`**: id, program\_id, year, method\_id, score, quota, subject\_combination.

**`entity_aliases`**: id, alias, normalized\_alias, entity\_type (`program` | `program_group`), entity\_code, alias\_type (`en` | `colloquial` | `abbrev` | `code_variant`), **resolution** (`unique` | `clarify` | `group`), year (rỗng = mọi năm), note.

> Cột `resolution` là bổ sung so với bản v1.1. Không có nó thì tầng tra cứu không phân biệt được alias trỏ 1 mã (trả lời thẳng) với alias trỏ nhiều mã (phải hỏi lại) — tức không cài được AC8. Với `resolution = group`, `entity_code` **không phải mã ngành** mà là chuỗi trong cột `program_group` của bảng `quotas`, để lọc thẳng thay vì phải chép danh sách 26 mã ELITECH vào từ điển rồi sửa tay mỗi năm.

**`faculties`** (mới — chuyển từ RAG sang structured): faculty\_id, faculty\_name, address, departments (list), programs (list, liên kết programs.program\_id), contact\_info, **official\_channel\_url** (link fanpage/website chính thức, phục vụ ANNOUNCEMENT\_QUERY).

**`faculty_announcements`** (mới — backlog v2, không triển khai trong MVP): title, url, published\_date, faculty\_id, fetched\_at. Chỉ dùng khi có batch job crawl định kỳ đã được đánh giá khả thi theo từng nguồn (xem mục 4.5).

**Các bảng bổ sung (đã có dữ liệu, chưa liệt kê ở bản v1.1):**

| Bảng | Nội dung | Dòng |
| --- | --- | --: |
| `quotas` | Chỉ tiêu theo ngành + `program_group` (CHUẨN / ELITECH / PFIEV / LIÊN KẾT QUỐC TẾ) | 133 (2025–2026) |
| `program_methods` | Ngành nào xét theo phương thức nào | 399 (2025–2026) |
| `subject_combinations` | Tổ hợp xét tuyển theo ngành — tra được **cả hai chiều**: ngành → tổ hợp, và tổ hợp → các ngành nhận. Có cột `main_subject` (môn chính, "Toán" hoặc rỗng) và `formula_type` để nối sang bảng công thức. Môn chính lấy từ nguồn **bên thứ ba** (`main_subject_status = third_party`, đã đối chiếu tổ hợp khớp 67/68 ngành) vì HUST không công bố danh sách này trong các nguồn chính thức đã thu thập; TROY-IT/D01 để `chua_ro` | 293 (2026) |
| `subject_combinations_ref` | Giải nghĩa mã tổ hợp (A00 = Toán, Lý, Hoá…) | 13 |
| `scoring_formulas_2026` | Công thức tính điểm xét theo `formula_type` (không môn chính / môn chính Toán / K01 / ĐGTD / XTTN), nguyên văn bài điểm chuẩn 2026. Câu "ngành X tính điểm thế nào" = join `subject_combinations` → `scoring_formulas` | 6 |
| `program_overview` | Học phí, thời gian đào tạo, bằng tốt nghiệp, ngôn ngữ đào tạo theo ngành | 68 (2026) |
| `tuition_by_year` | Học phí theo nhóm chương trình, **có cột `unit` riêng** vì lẫn /năm và /học kỳ | 11 |
| `tuition_credit` | Học phí theo tín chỉ | 30 |
| `admission_fees` | Lệ phí xét tuyển, lệ phí thi ĐGTD (450.000đ), phí xác minh chứng chỉ | 6 |
| `cert_bonus_conversion` | Quy đổi điểm thưởng chứng chỉ quốc tế | 122 |
| `cert_cefr_equivalence` | Quy đổi chứng chỉ ngoại ngữ theo khung CEFR | 47 |
| `cert_equivalence_output_2026` | Quy đổi chứng chỉ tiếng Anh để xét **chuẩn đầu ra** (9 bậc × 18 loại chứng chỉ) | 153 |
| `language_exit_requirement_2026` | Chuẩn ngoại ngữ đầu ra theo từng nhóm CTĐT | 14 |
| `tuition_2026` | Học phí 2026 theo từng ngành, tách số và đơn vị | 68 |

> **Hai bảng chứng chỉ KHÔNG được dùng lẫn nhau.** `cert_bonus_conversion` là điểm thưởng
> **khi xét tuyển** (thí sinh lớp 12); `cert_equivalence_output_2026` là quy đổi bậc năng lực
> để xét **chuẩn đầu ra khi tốt nghiệp**. Cùng là IELTS nhưng khác mục đích và khác giá trị.


**Ràng buộc bắt buộc khi thiết kế schema:** bảng `programs` phải **tách theo năm** (hoặc có cột `year` trong khoá), không dùng một master list dùng chung. Danh mục ngành đổi hằng năm — 2026 mở thêm 5 ngành (CH-E20, EM-E17, MI-E22, ED5, FL4) và bỏ 2 ngành (TROY-BA, EM4). Dùng master list sẽ khiến bot trả lời rằng ngành đã ngừng tuyển vẫn đang tuyển.

## 16. Vector Database

Sử dụng Qdrant hoặc Pinecone. Embedding: `text-embedding-3-large` (3072 chiều; đổi từ `-small` ngày 2026-10-04, xem `PLAN - Embedding (v1).md` mục 6.3). Vector record chứa: embedding, chunk\_text, metadata (phục vụ citation và filtering).

## 17. LLM

MVP dùng `OpenAI gpt-4o-mini`.

- Temperature = 0.0 cho các tác vụ cần tính deterministic cao: structured extraction, query generation, classification (bao gồm Router và Entity Resolution).
- Temperature ≈ 0.2 cho RAG answer generation, để giảm tính ngẫu nhiên nhưng vẫn tạo câu trả lời tự nhiên.

## 18. Observability

Sử dụng Langfuse để theo dõi: request, router decision, tool call, SQL latency, retrieval latency, retrieval score, LLM latency, token usage, estimated cost, error rate, end-to-end latency. Mục tiêu là truy ngược được toàn bộ đường đi User Query → Router → Tool → Database → LLM → Final Answer khi xảy ra lỗi.

## 19. API Design

**POST `/api/chat`** — nhận `{"thread_id": "...", "message": "..."}`, trả về `{"answer": "...", "citations": [], "metadata": {"intent": "ADMISSION_QUERY"}}`. `metadata.intent` bao gồm cả các intent mới: ANNOUNCEMENT\_QUERY, CLARIFICATION\_NEEDED, OTHER\_UNIVERSITY, GENERAL\_OFF\_TOPIC.

**POST `/api/chat/stream`** — streaming response qua SSE.

**GET `/api/health`** — health check cho backend.

## 20. Lộ trình triển khai 6 tuần

*(Giữ nguyên theo bản gốc — không điều chỉnh trong lần cập nhật scope này.)*

**Tuần 1 — Data Foundation:** thiết kế PostgreSQL schema (`programs`, `admission_methods`, `admission_scores`, `entity_aliases`, `faculties`, cùng các bảng bổ sung ở mục 15.1); thu thập & chuẩn hóa dữ liệu tuyển sinh 2024–2026; thu thập PDF, chuyển sang Markdown, gán metadata; chuẩn bị tài liệu Khoa/Viện. Deliverable: PostgreSQL database + cleaned Markdown documents.

*Trạng thái 2026-10-05 — Tuần 1 xong (thay bảng ngày 2026-09-23; bảng cũ còn trong lịch sử git):*

| Hạng mục | Trạng thái |
| --- | --- |
| Thu thập & chuẩn hoá dữ liệu tuyển sinh | ✔ 24 bảng CSV, có script validate tự động |
| PDF → Markdown + gán metadata | ✔ 641 chunk / 14 tài liệu, đủ `dataset_version`, `collection_date`, `page_no` (xem `PLAN - Metadata Design (v2).md`) |
| Từ điển alias | ✔ 253 dòng: ngành (68/68), nhóm ngành, Trường/Khoa, chứng chỉ |
| Thiết kế schema + nạp DB | ✔ 23 bảng trong **SQLite** `data/db/hust.sqlite`, dựng lại từ CSV bằng `build_db.py`; 0 trùng khoá, 0 khoá ngoại mồ côi (xem `PLAN - Data Linking (v1).md`). Lệch "chưa phải PostgreSQL" **đã khép 2026-10-06**: `build_db.py --postgres` nạp cùng dữ liệu vào PostgreSQL (schema `hust`), SQLite giữ làm bước kiểm tra trước khi nạp (xem `PLAN - Backend PostgreSQL (v1).md`) |
| `faculties`: `address`, `contact_info`, `departments`, `official_channel_url` | ✔ 10/10 Trường/Khoa có số điện thoại, email, địa chỉ (từ mục "Đơn vị quản lý" trên trang ngành + `data/link.md`; chỗ lệch do người dùng chốt). `departments` thành bảng `faculty_units` (34 đơn vị chuyên môn); SEM, SOFL chưa có trong dữ liệu thu thập |
| Chuẩn hoá schema chunk theo mục 11.3 | ✔ xong trước khi embed (2026-09-27) |
| Bổ sung `page_no` cho chunk nguồn PDF/scan | ✔ 404/404 chunk PDF có trang |
| Gắn `manual_verified` cho bảng điểm chuẩn + học phí (mục 26) | ✔ 2026-10-05 người dùng soát tay: điểm chuẩn 2024–2026 (660 dòng; 27 dòng tính theo luật lệch 0,5 điểm giữ `rule_derived`), học phí 2026 (68), học phí 2024–2025 (41), liên hệ 10 Trường/Khoa |

**Bộ test đánh giá (mục 25) chuyển từ Tuần 6 lên Tuần 2, làm song song với RAG pipeline.** Lý do: cả 9 tiêu chí AC1–AC9 đều đo trên test set, nên nếu viết ở Tuần 6 thì suốt 4 tuần trước đó không có cách nào biết hệ thống đang đúng hay sai. Viết sớm khi còn nắm rõ dữ liệu có gì/thiếu gì thì bộ test còn có tác dụng phát hiện lỗ hổng lúc kịp vá; viết ở Tuần 6 thì chỉ còn tác dụng chấm điểm. Tuần 6 giữ nguyên phần **chạy đánh giá và viết báo cáo**.

**Tuần 2 — RAG Pipeline:** document loader, header-based chunking, metadata extraction, embedding, Qdrant/Pinecone, retriever, citation metadata, retrieval evaluation. Deliverable: Document → Chunk → Embedding → Vector DB → Retriever.

**Tuần 3 — Tools & Entity Resolution:** Admission SQL Tool (input dạng list), Entity Resolution (kèm bước clarification), Alias lookup, Fuzzy matching, RAG Tool, University Info Tool, Pydantic schemas, function calling. Deliverable: các tool hoạt động độc lập và có test.

**Tuần 4 — LangGraph:** Router (đầy đủ intent mới), StateGraph, Tool execution, Synthesizer, Checkpointer, Multi-turn context (kèm quy tắc reset), Fallback, Guardrails, Langfuse. Deliverable: backend end-to-end User → Router → Tool → Database → Synthesizer → Response.

**Tuần 5 — Frontend:** Next.js, Chat UI, Streaming, Markdown, Table, Citation component, Clarification prompt, Error state, Loading state, Fallback UI. Deliverable: Full-stack MVP.

**Tuần 6 — Evaluation & Demo:** chạy bộ test đã soạn từ Tuần 2 (50 Admission queries, 50 RAG queries, 20 Edge cases); kiểm thử Accuracy, Entity resolution, Router, Citation, Hallucination, Multi-turn, Latency, Cost; Deployment (Backend: Railway/Render, Frontend: Vercel). Deliverable: production-like demo, evaluation report, technical documentation, presentation.

## 21. Acceptance Criteria

**AC1 — Admission Accuracy (đã tách 2 chỉ số).**

- Tool accuracy: 100% trên test set — Admission Tool trả đúng dữ liệu theo ngành + năm + phương thức + thang điểm (đây là SQL query trực tiếp, có thể đạt tuyệt đối).
- Synthesis accuracy: ≥ 98% trên test set — câu trả lời cuối cùng của LLM phản ánh đúng dữ liệu mà tool đã trả về (đo riêng vì lỗi có thể phát sinh ở bước LLM diễn giải, không chỉ ở dữ liệu). 100% ở tool accuracy chỉ áp dụng cho test set định trước, không phải tuyên bố hệ thống luôn đúng tuyệt đối trên mọi câu hỏi thực tế.

**AC2 — Entity Resolution.** ≥ 95% trên test set alias được gán nhãn, gồm: mã ngành, tên đầy đủ, tên viết tắt, tên thông dụng, khác biệt chữ hoa/thường, biến thể tiếng Việt, alias tiếng Anh cho tên ngành/khoa.

**AC3 — Router.** ≥ 95% accuracy trên bộ test intent đã gán nhãn, bao gồm cả các intent mới (ANNOUNCEMENT\_QUERY, CLARIFICATION\_NEEDED, OTHER\_UNIVERSITY, GENERAL\_OFF\_TOPIC).

**AC4 — Citation.** 100% các câu trả lời RAG trong test set phải có citation hợp lệ theo bảng ở mục 12: Tên tài liệu + Vị trí + Đường dẫn. Yêu cầu "có số trang" chỉ áp dụng cho nguồn PDF/scan — nguồn web không có số trang nên tính hợp lệ bằng `source_url`. Bản v1.1 ghi cứng "Document + Article/Section + Page" là không thể đạt với 267 chunk nguồn web.

**AC5 — No Hallucination.** Với câu hỏi không có trong dataset: không tự tạo số liệu, không tự tạo điều khoản, không tự tạo citation, không tự suy đoán điểm chuẩn hay chênh lệch giữa các ngành.

**AC6 — Multi-turn.** Xử lý đúng các câu hỏi phụ thuộc context trong bộ test multi-turn, bao gồm cả trường hợp reset context khi đổi chủ đề (mục 14).

**AC7 — Out-of-domain.** Với câu hỏi ngoài phạm vi HUST hoặc ngoài dữ liệu MVP (cả OTHER\_UNIVERSITY và GENERAL\_OFF\_TOPIC): trả về fallback thay vì cố sinh câu trả lời.

**AC8 — Clarification (mới).** Khi entity resolution phát hiện ambiguity (top-1/top-2 score gần nhau), hệ thống phải hỏi làm rõ thay vì tự chọn, trên ≥ 95% trường hợp trong test set ambiguity đã gán nhãn.

**AC9 — Announcement fallback (mới).** 100% câu hỏi thuộc ANNOUNCEMENT\_QUERY trả về đúng link kênh thông tin chính thức của Khoa/Viện tương ứng, không tự bịa nội dung thông báo.

## 22. Performance Requirements

### 22.1. Time to First Token

P50 TTFT < 2 giây; P95 TTFT < 4 giây. Đo trong môi trường deployment thử nghiệm, dùng streaming response, loại trừ cold-start bất thường. Lưu ý: các bước clarification/multi-entity có thể thêm 1 vòng LLM call — cần đo riêng TTFT cho các luồng này khi eval.

### 22.2. Database Query

P95 PostgreSQL query < 500 ms trong môi trường benchmark MVP.

## 23. Security Requirements

### API Keys

Không lưu API key trong frontend. Dùng Environment Variables: `OPENAI_API_KEY`, `DATABASE_URL`, `QDRANT_URL`, `LANGFUSE_SECRET_KEY`.

### Rate Limiting (mới)

Vì MVP không yêu cầu đăng nhập (mục 4.1), hệ thống công khai cho mọi người gọi — cần rate limit cơ bản theo IP/session (VD: giới hạn số request/phút) để tránh bị lạm dụng gây phát sinh chi phí LLM ngoài kiểm soát.

### Data Privacy

MVP không yêu cầu dữ liệu cá nhân. Không lưu: CPA, điểm cá nhân, hồ sơ sinh viên, thông tin tài chính cá nhân.

## 24. Error Handling

Hệ thống phải phân biệt ít nhất:

```text
INVALID_REQUEST
ENTITY_NOT_FOUND
ENTITY_AMBIGUOUS        (mới — kích hoạt CLARIFICATION_NEEDED)
DATA_NOT_FOUND
LOW_RETRIEVAL_CONFIDENCE
OUT_OF_DOMAIN
DATABASE_ERROR
LLM_ERROR
INTERNAL_ERROR
```

Mỗi loại lỗi có fallback message phù hợp.

## 25. Evaluation Framework

| Nhóm | Số lượng | Mục tiêu |
| --- | --: | --- |
| Admission | 50 | Data accuracy (đơn + đa thực thể) |
| RAG | 50 | Retrieval + answer + citation |
| Edge cases | 20 | Safety + fallback |
| Multi-turn | Bổ sung | Context + reset rules |
| Entity | Bổ sung | Alias resolution + ambiguity/clarification |
| Announcement | Bổ sung (mới) | Đúng link, không bịa nội dung |

Các metric chính: Admission Accuracy (tool + synthesis), Router Accuracy, Entity Resolution Accuracy, Clarification Accuracy, Citation Validity, Retrieval Hit Rate, Hallucination Rate, P50/P95 TTFT, Token Cost, Error Rate.

## 26. Data Versioning

Do MVP không dùng real-time scraping, dữ liệu phải có version. **Phiên bản hiện tại: `dataset_version = 2026.1`**, `admission_data: [2024, 2025, 2026]`, `collection_date` từ 2026-09-20 đến 2026-09-23.

Khi cập nhật dữ liệu phải xác định: `source, collection_date, verification_status, version`.

Giá trị `verification_status` đang dùng, xếp theo độ tin tăng dần:

| Giá trị | Nghĩa |
|---|---|
| `rule_derived` | **Không có trên bảng công bố** — tính ra từ quy tắc (vd điểm nhóm tổ hợp kỹ thuật = điểm công bố + 0,5) |
| `vision_extracted` | Một lần đọc từ ảnh/scan |
| `html_parsed`, `web_extracted`, `pdf_text` | Bóc từ văn bản có sẵn, không qua ảnh |
| `vision_double_read` | Hai lần đọc **độc lập** từ ảnh, so từng ô khớp nhau; ô bất đồng đã phân xử bằng ảnh phóng to |
| `manual_verified` | **Người** đã mở nguồn gốc so tận mắt — chỉ người gắn được nhãn này | **Từ 2026-10-05:** điểm chuẩn 2024–2026, học phí (2026 theo ngành và 2024–2025 theo nhóm) và liên hệ 10 Trường/Khoa đạt `manual_verified` sau khi người dùng soát tay — đây là các nhóm số liệu người dùng dễ đối chiếu ngược với nguồn gốc nhất. Các bảng còn lại giữ nhãn theo cách bóc. Dữ liệu sửa sau ngày soát phải hạ nhãn về cách bóc mới cho tới khi soát lại.

## 27. Definition of Done

Một chức năng hoàn thành khi: code đã review, có test case, không có lỗi blocker, có logging phù hợp, có xử lý exception, có documentation, được tích hợp vào workflow, pass acceptance criteria tương ứng.

MVP hoàn thành khi: PostgreSQL + RAG + Entity Resolution (kèm clarification) + LangGraph + Multi-turn (kèm reset rules) + Citation + Fallback + Announcement link + Next.js + Evaluation hoạt động end-to-end.

## 28. Rủi ro và phương án giảm thiểu

| Rủi ro | Mức độ | Phương án |
| --- | --- | --- |
| PDF khó parse | Cao | Kiểm tra thủ công + preprocessing |
| OCR lỗi | Trung bình | Chỉ dùng tài liệu có text layer nếu có thể |
| Alias không đầy đủ | Trung bình | Alias dictionary + fuzzy matching |
| LLM hallucination | Cao | Tool-first + RAG + citation + fallback |
| Retrieval sai | Cao | Metadata + validation set |
| TTFT cao | Trung bình | Streaming + giảm số LLM calls |
| Scope quá lớn | Cao | Ưu tiên admission + RAG |
| Dữ liệu không cập nhật | Trung bình | Data versioning + ghi rõ phạm vi dữ liệu |
| LLM/API downtime | Trung bình | Error handling + retry |
| **Entity ambiguity bị tự chọn sai (mới)** | **Cao** | **Bước clarification bắt buộc khi top-1/top-2 score gần nhau (mục 10.3), không để hệ thống tự quyết định** |
| **Chi phí phát sinh do không rate limit (mới)** | **Trung bình** | **Rate limiting theo IP/session (mục 23)** |

## 29. MVP Success Definition

MVP đạt yêu cầu khi người dùng thực hiện thành công chu trình:

```text
Đặt câu hỏi
      ↓
Router xác định intent (kể cả clarification/announcement)
      ↓
Entity được chuẩn hóa (hoặc hỏi làm rõ nếu mơ hồ)
      ↓
Tool/RAG được lựa chọn
      ↓
Dữ liệu được truy xuất (đơn hoặc đa thực thể)
      ↓
Evidence được kiểm tra
      ↓
LLM tổng hợp câu trả lời
      ↓
Citation được hiển thị
      ↓
Context được lưu (theo đúng quy tắc reset)
```

và hệ thống có khả năng từ chối hoặc fallback khi không có đủ dữ liệu để trả lời.

## 30. Technology Stack Summary

| Layer | Technology |
| --- | --- |
| Frontend | Next.js + TailwindCSS |
| Backend | FastAPI + Python 3.11+ |
| Agent Framework | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Embedding | text-embedding-3-large (đổi từ -small ngày 2026-10-04, xem `PLAN - Embedding (v1).md` mục 6.3) |
| Structured DB | PostgreSQL |
| Vector DB | Qdrant / Pinecone |
| Observability | Langfuse |
| API Streaming | SSE |
| Deployment Frontend | Vercel |
| Deployment Backend | Railway / Render |

*(Không có tầng MCP — xem quyết định kiến trúc ở mục 7.2.)*

## 31. Tổng kết

**HUST Info & Admission Assistant** tập trung vào hai nhóm dữ liệu chính:

```text
                    HUST Assistant
                          │
             ┌────────────┴────────────┐
             │                         │
      Structured Data           Unstructured Data
             │                         │
  Admission + Faculty Info            RAG
     (PostgreSQL)             (12 tài liệu đóng)
             │                         │
             └────────────┬────────────┘
                          │
                       LangGraph
                  (function calling,
                   không dùng MCP)
                          │
                    Final Response
```

MVP tập trung vào ba năng lực cốt lõi:

1. Tra cứu tuyển sinh chính xác bằng dữ liệu có cấu trúc, kể cả so sánh nhiều thực thể.
2. Hỏi đáp quy chế dựa trên tài liệu có trích dẫn, trong phạm vi danh sách tài liệu đã chốt.
3. Hội thoại nhiều lượt với Entity Resolution (có bước làm rõ khi mơ hồ), Context Management (có quy tắc reset), và biết giới hạn của chính mình — trả về link thay vì tự bịa khi gặp nội dung ngoài khả năng xác minh (thông báo Khoa/Viện, dữ liệu ngoài HUST, ngoài chủ đề).

Phạm vi giới hạn ở dữ liệu HUST 2024–2026 và các tài liệu đã kiểm chứng, nhằm đảm bảo khả năng hoàn thành trong thời gian triển khai 6 tuần.
