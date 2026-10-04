# PLAN — Embedding dữ liệu vào Qdrant (v1)

**Ngày:** 2026-10-03 · Gắn với PRD v1.2 mục 11.1, 16, Tuần 2 · Tiếp theo `PLAN - Metadata Design (v2).md` · Làm trên nhánh `embedding_data`

Mỗi quyết định có dòng **Vì sao** — theo quy ước ghi chú của dự án.

---

## 1. Bối cảnh và mục tiêu

Dữ liệu văn bản đã chuẩn hoá xong: **637 chunk** trong `data/rag/normalized/` (14 file, `dataset_version = 2026.1`, `validate_metadata.py` 0 lỗi). Bước tiếp theo (PRD Tuần 2) là đưa các chunk này vào kho vector để chatbot tìm được bằng RAG.

**Kết quả mong muốn:** một collection tìm được bằng cả nghĩa lẫn từ khoá, lọc được theo metadata (năm, loại tài liệu, mã ngành…), kèm một con số đo chất lượng tìm kiếm trên bộ 120 câu hỏi.

**Các điểm đã chốt từ trước (không bàn lại ở đây):** model `text-embedding-3-small` (**đổi thành `text-embedding-3-large` ngày 2026-10-04, xem mục 6.3**); Qdrant chạy Docker local; collection `hust_rag_2026_1`; chuỗi embed = `<document_title> <year> | <heading>` + text; giữ học phí trong chunk ngành dù trùng CSV; ưu tiên năm mới nhất khi câu hỏi không nêu năm.

**Hiện trạng môi trường (đo 2026-10-03):** chưa có file `.env`; container Qdrant chưa chạy; thư viện Python trên máy đã đủ (`openai` 1.109, `qdrant-client` 1.19.0, `python-dotenv`); Docker Desktop có sẵn.

**Quy mô:** 637 chunk ≈ 328.000 token, chunk dài nhất 1.291 token (dưới giới hạn 8.191 của model). Chi phí một lần nhúng ≈ 0,007 USD, chạy dưới 1 phút.

**Vì sao chi phí thấp lại quan trọng:** mọi lựa chọn trong kế hoạch này đều **làm lại được** bằng cách nhúng lại toàn bộ — không có quyết định nào ở đây là "một đi không trở lại".

---

## 2. Chọn kho vector: Qdrant (giữ nguyên lựa chọn ban đầu)

| Tiêu chí | Qdrant | pgvector | Chroma |
|---|---|---|---|
| Lọc theo metadata (`year`, `program_code`, `cohort`…) | Có sẵn, có chỉ mục | Có sẵn (SQL `WHERE`) | Có, hạn chế hơn |
| Tìm từ khoá cho mã (`IT-E10`, `K01`, `Điều 19`) | Có sẵn BM25 + gộp kết quả (RRF) | Phải tự viết: full-text search Postgres + SQL gộp kết quả | Bản local gần như không có |
| Số dịch vụ phải chạy thêm | 1 (ngoài Postgres) | **Không thêm** — dùng chung Postgres của bảng số | Không cần server, nhưng file nằm ngay trong thư mục dự án |
| Xem dữ liệu bằng mắt | Dashboard có sẵn (`localhost:6333/dashboard`) | Dùng công cụ SQL | Không có |
| Trạng thái trong dự án | Đã có `docker-compose.yml`, `check_setup.py`, PRD mục 16 | Chưa dựng Postgres (cổng 5432 máy đang bị dự án khác chiếm; nối bảng đang hoãn) | Chưa có gì |

**Vì sao Qdrant:** thứ dự án cần nhất ngoài tìm theo nghĩa là tìm đúng mã ngành / tổ hợp / số Điều — Qdrant có sẵn cả hai (vector nghĩa + BM25) trong một lần gọi. Hạ tầng đã dựng, khớp PRD mục 16.
**Vì sao không Chroma:** thiếu tìm từ khoá; dữ liệu của nó là nhiều file nhỏ nằm trong thư mục dự án, mà thư mục này ở trong OneDrive — đồng bộ liên tục dễ làm hỏng chỉ mục.
**Vì sao chưa chọn pgvector** dù nó gọn hơn (một database cho cả bảng số lẫn vector): Postgres của dự án chưa dựng, và phần tìm từ khoá + gộp kết quả phải tự viết, tự kiểm — việc đó nằm ngoài phạm vi bước này.
**Khi nào nên đổi:** khi triển khai thật và muốn bỏ bớt một dịch vụ. Chi phí đổi thấp — nhúng lại 637 chunk tốn 0,007 USD, chỉ phải viết lại `embed_chunks.py` + `retriever.py`; file chunk, metadata, bộ câu hỏi đo đều giữ nguyên.

---

## 3. Việc duy nhất cần làm tay: tạo `.env`

```powershell
Copy-Item .env.example .env      # rồi điền OPENAI_API_KEY vào .env
```

**Vì sao chỉ mỗi việc này cần làm tay:** key không được phép xuất hiện trong chat hay trong code; mọi bước Docker còn lại không cần thao tác thủ công nào khác.

---

## 4. Xây dựng Docker

**Phạm vi:** Qdrant + một container chạy việc nhúng/tìm thử (`ingest`). Postgres, backend, frontend **chưa thêm** vì chưa có code để build — thêm khi tới đúng bước đó.

### 4.1. `docker-compose.yml` — sửa

| Dịch vụ | Thay đổi | Vì sao |
|---|---|---|
| `qdrant` (đã có) | Thêm `healthcheck` (thử mở cổng 6333 trong container) | Để dịch vụ khác chờ Qdrant **sẵn sàng thật** rồi mới chạy, thay vì đợi một khoảng thời gian cố định bằng tay |
| `ingest` (mới) | Build từ `scripts/Dockerfile`; `profiles: ["tools"]`; `depends_on: qdrant (service_healthy)`; `env_file: .env`; ghi đè `QDRANT_URL=http://qdrant:6333` | Xem bảng lựa chọn bên dưới |

Gắn thư mục cho `ingest`: toàn bộ dự án ở chế độ **chỉ đọc** (`./:/app:ro`), riêng `./docs/ghi_chu` cho ghi (nơi lưu báo cáo đo retrieval).

### 4.2. `scripts/Dockerfile` + `scripts/requirements-ingest.txt` — mới

`python:3.12-slim`, cài 3 thư viện ghim đúng phiên bản đang dùng trên máy: `openai==1.109.1`, `qdrant-client==1.19.0`, `python-dotenv==1.2.3`. Không copy code hay dữ liệu vào image.

### 4.3. Các lựa chọn và vì sao

| Lựa chọn | Vì sao |
|---|---|
| Có container `ingest` thay vì chỉ chạy Python trên máy | Người dùng dự định chạy dự án trên Docker: phiên bản thư viện được ghim trong image (nhất là `qdrant-client` phải khớp server 1.19), máy khác chỉ cần Docker là nhúng lại được. Đây cũng là khuôn cho Dockerfile backend sau này. Chạy bằng Python trên máy vẫn được (khi đó `.env` giữ `QDRANT_URL=http://localhost:6333`). |
| `profiles: ["tools"]` | `docker compose up -d` chỉ bật Qdrant. Nhúng là việc chạy một lần rồi thoát, không phải dịch vụ thường trực — gọi riêng bằng `docker compose run --rm ingest …`. |
| Ghi đè `QDRANT_URL` trong compose thay vì dùng `.env` | Trong container, `localhost` là chính container đó chứ không phải máy chạy Docker; các container gọi nhau bằng tên dịch vụ. `.env` giữ nguyên `localhost` cho lúc chạy ngoài Docker. |
| Gắn thư mục (mount) thay vì copy vào image | Dữ liệu và script đổi thường xuyên; copy thì mỗi lần đổi phải build lại image. `data/raw/` rất nặng (~166MB), không nên nằm trong image. |
| Gắn chỉ đọc | Việc nhúng chỉ cần đọc dữ liệu; chỉ đọc thì container không thể lỡ tay sửa file chunk. |
| Key OpenAI vào container qua `env_file`, không ghi vào Dockerfile/compose | Image và file compose có thể bị chia sẻ hoặc đưa lên git; `.env` đã nằm trong `.gitignore`. |
| Dữ liệu Qdrant ở volume Docker `hust_qdrant_data` (đã có), không phải thư mục trong dự án | Thư mục dự án nằm trong OneDrive — để chỉ mục ở đó sẽ bị đồng bộ liên tục và có thể hỏng. |

### 4.4. Lệnh sẽ dùng

```powershell
docker compose up -d                                              # bật Qdrant
docker compose build ingest                                       # build image (1 lần, hoặc khi đổi requirements)
docker compose run --rm ingest python scripts/check_setup.py --openai
docker compose run --rm ingest python scripts/embed_chunks.py --recreate
docker compose run --rm ingest python scripts/search_chunks.py "điều kiện cảnh báo học tập"
docker compose down                                               # tắt; dữ liệu vẫn còn trong volume
```

### 4.5. Kiểm tra phần Docker

- `docker compose config` không báo lỗi; `docker compose ps` hiện `hust-qdrant` trạng thái `healthy`.
- `check_setup.py --openai` chạy trong container in "SẴN SÀNG".
- Sau `docker compose down` rồi `up -d` lại → collection vẫn đủ 637 điểm (volume giữ dữ liệu).
- Nếu healthcheck không chạy được trong image Qdrant (image tối giản, có thể thiếu công cụ kiểm tra cổng) → đổi cách kiểm tra, hoặc để `ingest` tự thử kết nối lại vài lần; ghi rõ cách đã chọn vào mục "Đã thực hiện".

---

## 5. Hai chỉnh nhỏ trước khi nhúng

Phát hiện khi đo lại dữ liệu ngày 2026-09-30:

| Vấn đề | Số chunk | Cách xử lý |
|---|--:|---|
| Tên tài liệu đã có sẵn năm (`Đề án tuyển sinh 2026`, `Sổ tay sinh viên 2026`…) → ghép năm theo công thức cũ sẽ thành `… 2026 2026 \| …` | 297 | Chỉ ghép năm khi tên tài liệu **chưa chứa** năm đó |
| `page_no` lẫn hai kiểu: số (109 chunk) và chữ (528 chunk, vd `"3-4"`) | 637 | Đổi hết sang chữ trong `scripts/normalize_chunks.py`, chạy lại validator |

**Vì sao sửa `page_no` ở `normalize_chunks.py` chứ không sửa lúc nhúng:** file chuẩn hoá là nguồn duy nhất của sự thật; sửa ở script nhúng thì file và Qdrant lệch nhau. `chunk_id` không đổi nên không ảnh hưởng gì khác.

Dòng `[tiêu đề]` ở đầu `text` (514 chunk) **giữ nguyên**, dù lặp lại một phần `heading`. **Vì sao:** chuỗi embed = tiền tố + đúng nguyên văn `text` là một luật duy nhất, dễ kiểm; phần lặp chỉ tốn khoảng 15 token/chunk.

---

## 6. `scripts/embed_chunks.py` (mới)

Đọc `data/rag/normalized/*.chunks.jsonl` → nhúng → ghi vào Qdrant.

**Trình tự trong script:**

1. Gọi lại `load()` và `check()` của `scripts/validate_metadata.py`; còn lỗi thì dừng, không nhúng. **Vì sao:** metadata nằm cùng vector trong Qdrant — nhúng dữ liệu lỗi nghĩa là phải nhúng lại toàn bộ.
2. Dựng chuỗi embed cho từng chunk (luật ở mục 5).
3. Tạo collection với **hai loại vector** cho mỗi chunk:
   - `dense`: 3.072 chiều, cosine, từ `text-embedding-3-large` (gọi theo lô 100 chunk, 7 lần gọi — xem mục 6.3 vì sao đổi khỏi `-small`/1.536 chiều).
   - `bm25`: vector từ khoá do chính Qdrant tính (`models.Document(model="qdrant/bm25")`, tắt stemmer, giữ dấu tiếng Việt, tokenizer `WORD`).
4. Ghi điểm: ID = `uuid5(chunk_id)`; payload = toàn bộ metadata + `text` gốc + 2 trường suy ra (`is_latest`, `versioned` — mục 6.2).
5. Tạo chỉ mục payload: `year`, `document_type`, `program_code`, `faculty_code`, `cohort`, `dieu_no`, `chunk_id`, `is_latest`, `versioned`.
6. Tự kiểm (mục 7) rồi in báo cáo.

### 6.1. Sửa lại so với bản nháp đầu: bỏ vector `bm25`, dùng chỉ mục full-text có sẵn của Qdrant

Lúc viết code mới phát hiện: `models.Document(model="qdrant/bm25")` **không tính phía server** như bản nháp đầu giả định — đọc source `qdrant_client/qdrant_fastembed.py` thì đây là model **tính ở phía client bằng thư viện `fastembed`** (docstring ngay trong code: *"Configuration of the **local** bm25 models"*). Nghĩa là muốn dùng phải thêm `fastembed` vào image `ingest` — kéo theo `onnxruntime` và phải tải ~18 file (tokenizer, stopword, bảng stemmer) từ HuggingFace **qua mạng** ngay trong lúc nhúng (đã thử: tải được nhưng có cảnh báo lỗi quyền symlink trên Windows, phải lùi sang cách tải dự phòng).

Kiểm tra lại cũng thấy phần lớn lý do cần BM25 (tìm đúng mã) **đã có lời giải tốt hơn** bằng trường lọc chính xác sẵn có, không cần đoán qua điểm số:

| Mã cần tìm đúng | Đã có trường lọc chính xác | Số chunk có trường |
|---|---|--:|
| `IT-E10`, `EE1`... (mã ngành) | `program_code` | 152 |
| `5445/QĐ-ĐHBK`... (số quyết định) | `document_no` | 157 |
| `Điều 19`... | `dieu_no` | 158 |

**Quyết định:** bỏ vector `bm25`, thay bằng **chỉ mục full-text payload** (`TextIndexParams`, có sẵn trong Qdrant, không cần thư viện nào thêm) trên trường `text` — dùng làm **bộ lọc** (`MatchText`) cho các mã *không* có trường riêng (ví dụ `K01` — mã tổ hợp chỉ nằm trong nội dung, chưa có cột metadata). Vector nghĩa (`dense`) vẫn là đường tìm chính.

**Vì sao không cố giữ BM25 bằng cách khác (tự viết tokenizer + `Modifier.IDF`):** làm được, nhưng là TF-IDF tự chế (không có hệ số bão hoà `k1`/chuẩn hoá độ dài `b` như BM25 thật), lại phải tự viết và tự kiểm một tầng tách từ tiếng Việt mới — chi phí không nhỏ cho một việc mà bảng trên cho thấy phần lớn đã có trường chính xác giải quyết. Để dành việc này cho lúc đo thực tế (mục 7) cho thấy thật sự cần.

**Khi nào nên quay lại BM25/fastembed:** nếu đo trên bộ 120 câu hỏi thấy nhiều câu hỏi chứa từ khoá/mã **không** rơi vào 3 trường trên mà dense vector vẫn tìm sai — lúc đó thêm `fastembed` vào `requirements-ingest.txt` và nhúng lại (rẻ, không phải thiết kế lại collection).

### 6.2. Các lựa chọn khác và vì sao

| Lựa chọn | Vì sao |
|---|---|
| Chỉ mục full-text trên `text` dùng `MatchText` làm **bộ lọc**, không chấm điểm | Mục đích duy nhất là bắt đúng chuỗi như `K01` mà dense vector có thể bỏ sót do mã này không mang nhiều ngữ nghĩa. Không cần xếp hạng bằng từ khoá vì `dense` đã xếp hạng theo nghĩa. |
| ID điểm = `uuid5(chunk_id)` | Qdrant chỉ nhận ID dạng số hoặc UUID. `uuid5` sinh cùng một UUID cho cùng `chunk_id` → chạy lại là ghi đè đúng chunk cũ, không sinh bản trùng. `chunk_id` gốc vẫn nằm trong payload để đọc được. |
| Mỗi lần chạy **dựng lại cả collection** (cờ `--recreate` nếu collection đã tồn tại) | Rẻ (0,007 USD) và loại hẳn lỗi "chunk cũ còn sót" khi một chunk bị xoá hay đổi ID. Cờ `--recreate` để không xoá nhầm khi chạy lệnh không cố ý. Khi backend chạy thật mới cần cách cập nhật không gián đoạn (ngoài phạm vi lần này). |
| Payload lưu `text` gốc, không lưu chuỗi đã ghép tiền tố | `text` dùng để trích dẫn cho người dùng; tiền tố ghép thêm chỉ phục vụ tính vector, không nên lộ ra citation. |

### 6.2. Luật "ưu tiên năm mới nhất"

Chỉ 2 nhóm tài liệu có nhiều năm: Đề án tuyển sinh (2024/25/26) và Công bố điểm chuẩn (2024/25/26) — 53 chunk thuộc bản cũ.

- `versioned` = chunk thuộc nhóm tài liệu có nhiều hơn một năm.
- `is_latest` = chunk thuộc năm mới nhất trong nhóm đó.
- Câu hỏi **không nêu năm** → lọc `is_latest = true`.
- Câu hỏi **có nêu năm X** → lấy chunk có `year = X` **hoặc** `versioned = false`.

**Vì sao không lọc thẳng `year = 2026`:** Quy chế đào tạo mang năm 2025, Quy chế thi TSA mang năm 2024, KKHT mang năm 2022 — cả ba đều là bản hiện hành. Lọc cứng `year = 2026` sẽ loại mất chúng.
**Vì sao tính `is_latest`/`versioned` lúc nhúng chứ không ghi vào file chuẩn hoá:** đây là tính chất của cả kho dữ liệu tại một thời điểm, không phải của riêng một chunk. Thêm đề án 2027 rồi nhúng lại là cờ tự lật đúng, không phải sửa tay 9 chunk đề án 2026.

---

### 6.3. Đổi model: `text-embedding-3-small` → `text-embedding-3-large`

Lúc chạy `check_setup.py` phát hiện `.env` đang đặt `text-embedding-3-large` chứ không phải `-small` như các mục trước của plan giả định. Hỏi lại người dùng — **chốt dùng `-large`** (3072 chiều thay vì 1536).

**Vì sao chấp nhận đổi:** chi phí vẫn rất nhỏ ở quy mô 637 chunk (~0,045 USD so với ~0,007 USD của `-small`, chênh lệch không đáng kể), và `-large` có chất lượng ngữ nghĩa nhỉnh hơn theo benchmark của OpenAI — hợp lý khi chi phí không phải vấn đề. Đồng bộ lại: `EMBED_DIM = 3072` trong `embed_chunks.py`, giá trị mặc định `EMBEDDING_MODEL` trong `embed_chunks.py`/`search_chunks.py`/`check_setup.py`/`.env.example` đổi theo (`.env` là nguồn quyết định thật khi chạy; giá trị mặc định trong code chỉ dùng khi `.env` không có biến này).

**Việc phải làm theo vì đổi model:** đây là quyết định làm **trước** lần nhúng đầu tiên nên không có "chunk cũ" để dọn — không giống việc đổi model sau khi đã có dữ liệu trong collection. Nếu sau này muốn đổi model lần nữa, phải nhúng lại toàn bộ (collection khác kích thước vector không tương thích ngược) và cập nhật `docs/PRD.md` mục 16/17.

---

## 7. `scripts/search_chunks.py` (mới)

Công cụ tìm thử và đo, dùng chung cấu hình với `embed_chunks.py` (import trực tiếp — theo đúng cách các script hiện có đang import lẫn nhau).

```powershell
python scripts/search_chunks.py "điều kiện cảnh báo học tập"
python scripts/search_chunks.py "học phí IT1" --program IT1
python scripts/search_chunks.py --eval
```

- Tìm bằng vector `dense`; có thể thêm bộ lọc payload (`--program`, `--year`, `--cohort`) và `--text-filter` (dùng chỉ mục full-text mục 6.1 — xem mã như `K01` có lọt filter không).
- In: thứ hạng, điểm, `chunk_id`, tên tài liệu, heading.
- `--eval`: đọc `backend/tests/eval/120_question_check_data.md`, lấy cột câu hỏi và cột "Tài liệu tham chiếu"; với khoảng 83 câu có tham chiếu tới tài liệu văn bản, kiểm xem top-5 có chunk thuộc đúng tài liệu đó không. Ghi bảng kết quả vào `docs/ghi_chu/<ngày> - Ket qua retrieval.md`, kèm nhận xét có cần thêm BM25 (mục 6.1) hay không.

**Vì sao đo ở mức tài liệu, không phải mức chunk:** bộ câu hỏi hiện chỉ ghi tên file nguồn, chưa ghi `chunk_id` mong đợi. Đây là số đo nền; khi bổ sung `chunk_id` mong đợi thì đổi sang đo chính xác hơn (hit@k theo chunk).
**Cột "đáp án mong đợi" trong bộ 120 câu không dùng để chấm** — theo quyết định đã chốt trước đó, chỉ để tham khảo.
**Lưu ý khi đọc kết quả:** 21 câu đã được xác định là thiếu dữ liệu nguồn (ghi chú `2026-09-26 - Kiem tra 120 cau hoi.md`) sẽ trượt ở bước đo này — đó là thiếu dữ liệu, không phải lỗi tìm kiếm; báo cáo tách riêng nhóm này để không đánh giá sai retriever.

---

## 8. Kiểm tra (tự động, cuối `embed_chunks.py`)

| Kiểm tra | Bắt lỗi gì |
|---|---|
| Số điểm trong collection = 637 và tập `chunk_id` trùng khớp `data/rag/normalized/_chunk_ids.txt` | Thiếu / thừa chunk |
| Lấy ngẫu nhiên 20 chunk, nhúng lại, so với vector đã lưu (cosine ≥ 0,98) | Vector gắn nhầm chunk do lệch thứ tự trong lô |
| Lấy 5 điểm, so payload với dòng jsonl gốc | Metadata bị đổi kiểu hoặc rơi trường khi ghi |
| Tìm "phương thức tuyển sinh" không nêu năm → kết quả đầu phải là đề án 2026; nêu "2024" → đề án 2024 | Luật ưu tiên năm mới nhất |
| Tìm "chuẩn ngoại ngữ đầu ra" lọc `cohort = K71+` → không lẫn bản K70 | Cặp tài liệu giống nhau 100% ở 3 Điều |
| Lọc `--text-filter K01` → chỉ trả chunk có chứa đúng chuỗi "K01" | Chỉ mục full-text hoạt động đúng cho mã không có trường riêng |

---

## 9. Ghi lại sau khi làm xong

- Cập nhật mục "Đã thực hiện" ở cuối file này với kết quả thực tế và mọi lựa chọn phát sinh lúc làm (theo quy ước ghi lý do của dự án).
- Cập nhật `README.md` (dòng trạng thái Embedding, thêm các lệnh Docker) và `docs/cautrucduan.md` (thêm 2 script + Dockerfile, thêm bước embed vào "Thứ tự chạy lại", sửa mô tả `docker-compose.yml`).

---

## 10. File đụng tới

| File | Việc |
|---|---|
| `docker-compose.yml` | thêm healthcheck cho `qdrant`, thêm dịch vụ `ingest` |
| `scripts/Dockerfile`, `scripts/requirements-ingest.txt` | mới |
| `scripts/embed_chunks.py` | mới |
| `scripts/search_chunks.py` | mới |
| `scripts/normalize_chunks.py` | sửa 1 chỗ: `page_no` thống nhất về kiểu chữ |
| `docs/ghi_chu/<ngày> - Ket qua retrieval.md` | mới |
| `README.md`, `docs/cautrucduan.md` | cập nhật |

**Dùng lại, không viết mới:** `load()` / `check()` trong `scripts/validate_metadata.py`; cách đọc `.env` và tên biến (`QDRANT_URL`, `QDRANT_COLLECTION`, `EMBEDDING_MODEL`) như `scripts/check_setup.py`.

---

## 11. Ngoài phạm vi lần này

- `backend/app/rag/retriever.py` — viết ở Tuần 3; sẽ lấy luật lọc và tham số BM25 đã thử nghiệm ở `search_chunks.py`.
- Ngưỡng điểm cho fallback (PRD mục 13.1) — cần bộ test có nhãn ở mức chunk mới đặt được ngưỡng có căn cứ.
- Reranker — chỉ xét nếu hit@5 đo ở mục 7 thấp.
- Nối bảng dữ liệu (`PLAN - Data Linking (v1).md`) — đang hoãn theo quyết định của người dùng, không liên quan tới embedding.

---

# Đã thực hiện (2026-10-04)

## Kết quả

| Hạng mục | Kết quả |
|---|---|
| Collection | `hust_rag_2026_1` trên Qdrant 1.19.1 (Docker local) — 641 điểm, vector `dense` 3072 chiều, cosine |
| Model | `text-embedding-3-large` (đổi từ `-small` lúc chạy, xem mục 6.3) |
| Chi phí | ~0,045 USD / lần nhúng toàn bộ, ~10 giây gọi OpenAI (7 lô x 100) |
| Chỉ mục payload | `year`, `document_type`, `program_code`, `faculty_code`, `cohort`, `dieu_no`, `chunk_id`, `is_latest`, `versioned` + full-text trên `text` |
| Tự kiểm (mục 8) | 6/6 OK: số điểm đúng 641, `chunk_id` khớp manifest, cosine tái nhúng ≥ 0,98 (đo thực tế 0,9966–1,0), payload khớp jsonl gốc, luật năm mới nhất đúng, lọc `cohort` đúng, chỉ mục full-text bắt đúng "K01" |
| Retrieval (`search_chunks.py --eval`, dense top-5) | **60/77 (78%)**; bỏ 18 câu đã biết thiếu dữ liệu nguồn (⛔) → **48/59 (81%)**. Báo cáo đầy đủ: `docs/ghi_chu/2026-10-04 - Ket qua retrieval.md`. Số đo này đo **sau** khi sửa lỗi chunking ở mục dưới — xem mục đó vì sao số liệu không tăng dù dữ liệu đúng hơn |

## Lỗi chunking phát hiện qua việc đọc kết quả miss (đề án 2024/2025/2026)

Soi câu Q10 ("Trường có tính hệ số 2 đối với môn chính... khi xét tuyển theo điểm thi THPT không?", top-1 trả nhầm sang quy định XTTN) phát hiện lỗi thật trong `de_an_to_rag.py`: cả 3 năm đề án đánh số phương thức **(2) Xét tuyển theo điểm thi ĐGTD** và **(3) Xét tuyển theo điểm thi THPT** bằng ngoặc đơn, trong khi `HEADING_RE` chỉ nhận dạng số có dấu chấm (`1.1.`, `1.2.`...). Hệ quả: toàn bộ nội dung phương thức (2)/(3) — gồm đúng đoạn "Tổ hợp xét tuyển: Gồm 8 tổ hợp... Công thức K01..." — bị gộp lẫn vào **đuôi của mục "1.3. Xét tuyển theo Hồ sơ năng lực"** (sai hoàn toàn về chủ đề), tên `heading` và chuỗi embed vẫn ghi "1.3 Hồ sơ năng lực" dù nội dung thật là phương thức điểm thi THPT.

**Đã sửa:** thêm `TOP_METHOD_RE` nhận diện 2 heading này theo từ khoá nội dung ("Đánh giá tư duy" / "tốt nghiệp THPT"), không theo số thứ tự — tránh bắt nhầm các dòng liệt kê khác cũng dạng `(N) Xét tuyển...` (vd "(3) Xét tuyển và xác nhận nhập học" trong đề án 2024, "(4) Xét tuyển diện cử tuyển..."). Test 4 trường hợp đúng / 3 trường hợp nhiễu trước khi áp dụng. Kết quả: 622→**641 chunk gốc** (+4), `de_an_tuyen_sinh_2024` 37→38, `2025` 7→9, `2026` 9→10. Cũng sửa `normalize_chunks.py` để `muc_no` nhận dạng heading dạng `(N)` (trước đó rơi vào `m0-1`/`m0-2` vô nghĩa).

**Vì sao đúng mà điểm retrieval không tăng (77 câu: 81%→78%, hay 59 câu: 85%→81%):** đo lại sau khi sửa thì Q10 **vẫn trượt**, và xuất hiện thêm 2 câu trượt mới (Q12, Q24 — cả hai đều có dữ liệu, không phải nhóm ⛔). Tra trực tiếp: chunk đúng cho Q10 (`dean2026::m3-1`, nội dung "Toán x 3 + Ngữ văn x 1...") **không hề chứa chữ "hệ số"**; trong khi `qui-dinh-ve-xttn-nam-2026-ky` (`xttn2026::d3k2`, bảng quy đổi chứng chỉ quốc tế) lại chứa đúng cụm "**hệ số** thang 10" — ở nghĩa hoàn toàn khác (quy đổi điểm chứng chỉ, không phải nhân hệ số môn chính). Vector ngữ nghĩa bắt theo từ "hệ số" dùng chung giữa hai ngữ cảnh khác nhau. **Đây không phải lỗi có thể sửa bằng BM25/tìm từ khoá chính xác** — tìm đúng chữ "hệ số" sẽ CÀNG trỏ về tài liệu sai (nó có chữ đó, chunk đúng thì không). Việc tách chunk đúng hơn (1.3 ra khỏi (2)(3)) làm mất đi khối văn bản dài trước đó vô tình "trúng" một số câu nhờ chứa nhiều từ khoá dàn trải — tách nhỏ, đúng chủ đề hơn nhưng mỗi chunk có ít từ để "bắt" được các câu hỏi diễn đạt khác lạ.

**Thử lọc theo cụm từ có trong câu hỏi (gợi ý của người dùng):** chạy lại Q10 với `--text-filter "môn chính"` → tài liệu sai (`xttn2026::d3k2`) bị loại hẳn; top-2 là `ts::diem-chuan-2026-3` (công thức "tổ hợp có môn chính là Toán: [(Môn 1 + Môn 2 + Môn 3 + Môn chính) × 3/4]", tức Toán tính 2 lần) và `dean2026::m3-1` (8 tổ hợp + công thức riêng K01: Toán × 3). Đủ nguyên liệu cho câu trả lời đúng: *"Có, với tổ hợp có môn chính là Toán thì Toán được tính 2 lần; riêng K01 không theo cơ chế môn chính mà Toán × 3"* (khớp `scoring_formulas_2026.csv`: dòng `mon_chinh_toan` và `K01` là hai công thức tách biệt). **Ghi cho `retriever.py` (Tuần 3):** tách cụm từ chuyên ngành trong câu hỏi (môn chính, điểm sàn, mã tổ hợp, mã ngành...) rồi gộp kết quả dense có lọc `MatchText` với dense không lọc (Prefetch + RRF của Qdrant) — dùng lại chỉ mục full-text đã tạo, không cần BM25. Lưu ý thêm: bộ 120 câu chỉ ghi `de_an_tuyen_sinh_2026` là nguồn của Q10, trong khi `trang_tuyen_sinh` (bài điểm chuẩn 2026) cũng là nguồn đúng → cột tham chiếu nên bổ sung để chấm không bị trượt oan.

**Kết luận:** vẫn giữ lại fix này — `heading`/`document_title` đúng chủ đề quan trọng cho **citation** (PRD mục 12, không được trích dẫn sai tên mục) và cho các bộ lọc tương lai, kể cả khi chưa thấy cải thiện ở hit@5. Việc phân biệt "hệ số quy đổi chứng chỉ" với "hệ số môn chính" cần ngữ cảnh câu hỏi (nêu rõ đang hỏi về phương thức nào) — thuộc về Entity Resolution/Router (Tuần 3), không giải quyết được ở riêng bước embedding.

## Các lựa chọn phát sinh lúc làm — và vì sao

| Lựa chọn | Vì sao |
|---|---|
| Đổi `text-embedding-3-small` → `text-embedding-3-large` (mục 6.3) | `.env` của người dùng đã đặt sẵn `-large`; hỏi lại và được chốt dùng — chênh lệch chi phí không đáng kể ở quy mô này (0,045 so với 0,007 USD) |
| Bỏ vector `bm25` qua `fastembed`, dùng chỉ mục full-text có sẵn của Qdrant (mục 6.1) | Đọc source `qdrant_client` mới phát hiện `models.Document(model="qdrant/bm25")` tính ở **client** (cần thêm `fastembed`+`onnxruntime`+tải model qua mạng), không phải server như bản nháp đầu giả định; đối chiếu lại thấy phần lớn nhu cầu "tìm đúng mã" đã có trường lọc chính xác sẵn (`program_code`, `document_no`, `dieu_no`) |
| Ngưỡng tự kiểm cosine đổi 0,999 → 0,98 | Đo thực tế: nhúng lại cùng 1 chunk (kể cả gọi riêng lẻ, không qua lô) cho cosine 0,9966–1,0 — `text-embedding-3-large` không hoàn toàn deterministic ở tầng API của OpenAI. 0,999 là ngưỡng sai (cảnh báo giả); lỗi gán nhầm vector thật sẽ cho cosine rất thấp (nội dung khác hẳn), không phải 0,996 |
| `search_chunks.py` tự suy `slug -> tên nguồn` từ `data/rag/normalized/*.chunks.jsonl` thay vì import `normalize_chunks.py` | `normalize_chunks.py` import `pymupdf` (chỉ dùng để dò `page_no` cho đề án 2024) — image `ingest` cố tình tối giản 3 thư viện (mục 4.2); import cả module kéo theo `pymupdf` dù không dùng tới |
| Thêm `TZ: Asia/Ho_Chi_Minh` vào service `ingest` | Container mặc định chạy UTC; `search_chunks.py --eval` đặt tên file báo cáo theo `date.today()` — chạy sau 17h giờ VN sẽ ra sai ngày hôm trước (gặp thật: chạy 01:11 ngày 4/10 giờ VN nhưng container tính ra 3/10) |

## Còn lại chưa làm trong phạm vi plan này

9 câu trượt thật (không do thiếu dữ liệu) đều lẫn giữa đề án 2025/2026 hoặc giữa `gioi_thieu_truong_khoa` và `nganh_dao_tao` — là các cặp tài liệu giống nhau nhiều (đã nêu ở `PLAN - Metadata Design (v2)` mục 1: đề án 2025↔2026 giống 78-79% mục phương thức). Để dành việc tinh chỉnh (ví dụ ép boost theo `document_type` khi câu hỏi thuộc nhóm "giới thiệu") cho lúc viết `retriever.py` ở Tuần 3, khi có thêm dữ liệu từ Entity Resolution về loại câu hỏi.
