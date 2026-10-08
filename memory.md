# memory.md — Đúc kết để tiếp tục ở session mới

> **Session mới: đọc file này trước khi làm bất cứ việc gì.** Cập nhật lần cuối: 2026-10-07.
> Chi tiết và lý do của từng quyết định nằm trong các file `docs/PLAN - *.md` (mỗi quyết định có dòng "Vì sao"). File này chỉ là bản đồ.

## 1. Dự án

**HUST Info & Admission Assistant**: chatbot tiếng Việt (LangGraph) trả lời về tuyển sinh và học vụ Đại học Bách khoa Hà Nội.
Hai tầng dữ liệu:
- **Bảng số** (điểm chuẩn, chỉ tiêu, học phí, tổ hợp, chứng chỉ…): CSV → SQLite (bước kiểm tra) → PostgreSQL (schema `hust`, từ 2026-10-06).
- **Văn bản** (quy chế, đề án, sổ tay, giới thiệu ngành/Khoa): chunk → Qdrant (RAG).

Nguyên tắc trả lời: **số lấy từ SQL, RAG chỉ để giải thích và trích dẫn.**
Yêu cầu sản phẩm: `docs/PRD.md` (lộ trình 6 tuần ở mục 20).

## 2. Trạng thái (2026-10-06)

| Giai đoạn | Trạng thái | Tài liệu |
|---|---|---|
| Thu thập dữ liệu | Xong: 14 nguồn văn bản, 24 bảng CSV | `PLAN - Data Collection (v1).md`, `docs/nguon_du_lieu.md` |
| Metadata chunk | Xong: 641 chunk trong `data/rag/normalized/`, `dataset_version = 2026.1` | `PLAN - Metadata Design (v2).md` |
| Embedding | Xong: Qdrant collection `hust_rag_2026_1`, `text-embedding-3-large` (3072 chiều); hit@5 = 81% (bỏ câu đã biết thiếu dữ liệu) | `PLAN - Embedding (v1).md`, `docs/ghi_chu/2026-10-04 - Ket qua retrieval.md` |
| Data Linking | Xong: SQLite `data/db/hust.sqlite`, 23 bảng, 0 trùng khoá, 0 khoá ngoại mồ côi; liên hệ + đơn vị trực thuộc 10 Trường/Khoa | `PLAN - Data Linking (v1).md` (cả mục "Đã thực hiện" và "Bổ sung 2026-10-05") |
| Soát tay | Xong: điểm chuẩn 2024–2026, học phí, liên hệ Trường/Khoa mang nhãn `manual_verified` | PRD mục 20, 26 |
| **Tuần 1 (Data Foundation)** | **Xong.** (Lệch "chưa phải PostgreSQL" đã khép 2026-10-06) | PRD mục 20 |
| **Tuần 3 — bước 1: Backend + PostgreSQL** | **Xong 2026-10-06**: Postgres `127.0.0.1:5432` (container `hust-postgres`), `build_db.py --postgres`, `backend/app/core/config.py`, `backend/app/db/pool.py`, `pytest backend` 6/6. Ba quyết định mục 6 đi theo khuyến nghị (SQLite làm bước kiểm tra, không Alembic/ORM, async psycopg3) vì người dùng bảo "làm theo kế hoạch" | `docs/PLAN - Backend PostgreSQL (v1).md` (mục "Đã thực hiện") |
| Backend (tool, API, graph) / Frontend | Chưa có code, mới có khung thư mục | `docs/cautrucduan.md` |

Sơ đồ ER (hiện trạng CSV + mô hình đích): https://claude.ai/artifact/GVonC7WEHGSsyN8nToHprG (trang riêng tư của người dùng). Bản mermaid cũng nằm trong `PLAN - Data Linking (v1).md` mục 1 và 2.4.

## 3. Việc đang dở / làm tiếp

1. **Chưa commit** (lúc viết file này): đổi nhãn `manual_verified` ở 7 file CSV + `docs/PRD.md`, toàn bộ phần backend Postgres (docker-compose, build_db, check_setup, backend/, docs), `memory.md`. Hỏi người dùng đã commit chưa (`git status`). Commit CSV xong thì chạy lại `build_db.py --postgres` để `build_info.git_commit` hết đuôi `-dirty`.
2. **Tool (2026-10-07): Entity Resolution + T1 `admission_scores` + T2 `list_programs` ĐÃ XONG** (`docs/PLAN - Entity Resolution + Admission Tool (v1).md`, mục "Đã thực hiện"). `pytest backend` 204 passed; T1 quét đủ 687 dòng điểm chuẩn đúng 100%. 13 alias phương thức đã ghi vào CSV; `validate_aliases.py` dùng resolver backend, kiểm mọi loại thực thể: 0/0. 2026-10-08: thêm 6 alias (Công nghệ thông tin, Leibniz, Điện - Điện tử, Vật liệu, Quản trị kinh doanh, Cơ điện tử); bộ ca có nhãn `backend/tests/eval/entity_cases.csv` 104 ca **người dùng đã duyệt hết** → **AC2 100%, AC8 100%** (`scripts/eval_entity_cases.py`); mỗi ca là một test trong `test_entity_cases.py`. **T3 `program_info` XONG 2026-10-08** (`docs/PLAN - T3 program_info (v1).md`, 18 ca đã duyệt xanh). Tiếp theo: T4 `tuition_fees` + T5 `certificate_lookup` (bước 5 của `PLAN - Tools (v1)` mục 9) — làm theo cùng quy trình: plan chi tiết có bảng đáp án mong đợi → người dùng duyệt → code.
3. **Thứ tự Tuần 3** (đã thống nhất): nền backend + Postgres → Entity Resolution (4 quy tắc PRD 10.3; logic khớp đã có trong `scripts/validate_aliases.py` hàm `simulate_lookup`) → Admission SQL Tool → RAG Tool (`backend/app/rag/retriever.py`) → University Info Tool → test từng tool (dùng bộ 120 câu).
4. **Ghi sẵn cho `retriever.py`:** câu Q10 trượt vì chữ "hệ số" có ở tài liệu sai. Lọc thêm theo cụm từ chuyên ngành có trong câu hỏi ("môn chính") bằng chỉ mục full-text `MatchText` thì ra đúng. Hướng làm: Prefetch dense có lọc + không lọc, gộp bằng RRF (xem `PLAN - Embedding (v1).md` phần "Đã thực hiện").
5. **Việc nhỏ người dùng tự làm:** bộ 120 câu thiếu Q99–Q104; cột tham chiếu của Q10 nên thêm `trang_tuyen_sinh` (bài điểm chuẩn 2026); link nguồn cho lệ phí TSA 2026.
6. **Khoảng trống dữ liệu đã biết** (validator báo cảnh báo, không phải lỗi): năm 2024 không có bảng chỉ tiêu và phương thức; bảng học phí theo năm 2024–2025 không có PFIEV và FL3; SEM, SOFL chưa có đơn vị trực thuộc; tổ hợp theo ngành chỉ có năm 2026.

## 4. Bản đồ file

```
data/processed/*.csv              24 bảng nguồn (bóc từ văn bản) — LÊN GIT
data/processed/linking/*.csv      8 bảng nối do người gán (faculties, faculty_units, program_groups,
                                  admission_methods, certificates, tuition_rule_members,
                                  language_req_members, program_combinations_extra) — LÊN GIT
data/processed/entity_aliases.csv 253 alias: ngành, nhóm ngành, Trường/Khoa, chứng chỉ
data/rag/normalized/              641 chunk (đầu vào embedding) — KHÔNG lên git
data/raw/                         PDF, ảnh, HTML gốc (~166MB) — KHÔNG lên git
data/db/hust.sqlite               sinh ra bằng build_db.py — KHÔNG lên git, đừng sửa tay
data/link.md                      danh sách link + liên hệ Trường/Khoa do người dùng ghi — KHÔNG lên git
backend/tests/eval/120_question_check_data.md   bộ 120 câu đánh giá
docs/CONVENTIONAL_COMMIT.md       quy ước commit của người dùng
```

Script chính (35 script, để phẳng trong `scripts/`):

| Script | Việc |
|---|---|
| `normalize_chunks.py` → `validate_metadata.py [--selftest]` | Chuẩn hoá metadata chunk, kiểm tra (19/19 lỗi cài cố ý bị bắt) |
| `normalize_csv_meta.py` | Bù 6 cột chuẩn cho CSV (idempotent, giữ cột lạ) |
| `validate_aliases.py` | Kiểm alias, có giả lập tra cứu |
| `build_db.py [--postgres]` | CSV → SQLite; báo hết trùng khoá + khoá mồ côi rồi mới dừng; `--postgres` nạp thêm vào schema `hust` trong một transaction |
| `validate_links.py [--selftest]` | Kiểm liên kết bảng ↔ bảng ↔ chunk RAG (16/16) |
| `embed_chunks.py --recreate`, `search_chunks.py [--eval]` | Nhúng vào Qdrant, tìm thử / đo hit@5 (chạy qua container `ingest`) |
| `check_setup.py --openai` | Kiểm `.env`, Qdrant, Postgres, OpenAI (không in key) |

## 5. Lệnh chạy

```powershell
# Môi trường (Docker Desktop phải bật)
docker compose up -d                                         # Qdrant + Postgres
docker compose run --rm ingest python scripts/check_setup.py --openai

# Sau khi sửa dữ liệu nguồn
python scripts/<script bóc nguồn vừa đổi>.py
python scripts/normalize_csv_meta.py
python scripts/normalize_chunks.py ; python scripts/validate_metadata.py     # 0 lỗi
python scripts/validate_aliases.py                                          # 0 lỗi, 0 cảnh báo (dùng resolver backend)
python scripts/build_db.py --postgres ; python scripts/validate_links.py    # 0 lỗi; Postgres khớp SQLite
pytest backend                                                              # 80 passed
docker compose run --rm ingest python scripts/embed_chunks.py --recreate    # chỉ khi chunk đổi
docker compose run --rm ingest python scripts/search_chunks.py --eval
```

Kết quả chuẩn hiện tại: `validate_metadata` 0 lỗi 0 cảnh báo · `validate_aliases` 0/0 · `validate_links` 0 lỗi 7 cảnh báo (khoảng trống mục 3.6) · `validate_admission_csv` 0 lỗi 1 cảnh báo cũ (FL2/ĐGTD lệch 18 điểm).

## 6. Quyết định người dùng đã chốt (đừng đề xuất lại trừ khi người dùng mở lại)

- Embedding `text-embedding-3-large` (người dùng tự đặt trong `.env`), không phải `-small` như PRD gốc.
- Qdrant (không pgvector/Chroma). Bỏ vector BM25 (fastembed tính ở client); dùng chỉ mục full-text `MatchText` làm bộ lọc.
- Chuỗi embed = `<document_title>[ <year> nếu tên chưa có năm] | <heading>` + text.
- Giữ học phí trong chunk ngành dù trùng `tuition_2026.csv`; dựa vào `year`, ưu tiên năm mới nhất (cờ `is_latest`, `versioned` trong payload Qdrant).
- Tên ngành chuẩn theo đề án 2026, bỏ hậu tố "(mới)". Ngành nào phải chọn giữa nhiều tên thì **hỏi người dùng**.
- Giữ EM4, TROY-BA (dừng tuyển 2026).
- Bảng học phí tín chỉ 2024–2025 **dùng chung cho mọi năm** (5 ngành mở 2026 gán theo "các chương trình khác"); khi trả lời phải ghi "mức năm học 2024–2025".
- Lệ phí TSA: dòng 2024 trong `admission_fees.csv` là 500.000đ do người dùng sửa và chọn giữ, dù đề án 2024 ghi 450.000đ. **Đừng tự sửa lại.**
- Liên hệ Trường/Khoa: khi `data/link.md` lệch với mục "Đơn vị quản lý" trên trang ngành thì lấy trang ngành; nguồn ghi nhiều hotline thì giữ đủ.
- Cột môn chính lấy từ tuyensinh247 (`main_subject_status = third_party`): **không** đưa vào danh sách nguồn, chatbot **không** trích dẫn.
- "Đáp án mong đợi" trong bộ 120 câu chỉ để tham khảo, không dùng để chấm.
- Làm việc trên nhánh **`embedding_data`** (có thêm `main`, `develop`). Không tạo nhánh mới khi chưa hỏi.

## 7. Cách làm việc với người dùng

- Trả lời **tiếng Việt**, giải thích dễ hiểu, chữ có dấu. Người dùng hay gõ tắt, không dấu.
- **Viết plan trước, code sau**: `docs/PLAN - <tên> (v1).md`, mỗi quyết định có **"Vì sao"**, có mục "Cần anh quyết". Làm xong thì thêm mục "Đã thực hiện" (kết quả + lựa chọn phát sinh + vì sao).
- Dữ liệu lệch giữa các nguồn, hoặc quyết định thật sự thuộc người dùng → **hỏi** (AskUserQuestion, có phương án khuyến nghị). Không tự chọn.
- **Người dùng tự commit/push**: đưa câu lệnh, chia commit theo mục đích (`docs/CONVENTIONAL_COMMIT.md`: type viết thường, mệnh lệnh, message không dấu cho an toàn trong PowerShell).
- Sửa dữ liệu thì sửa CSV (nguồn), không sửa DB. Mỗi lần sửa xong chạy lại validator và báo kết quả thật, kể cả khi số đo xấu đi.
- Không đọc/in giá trị `OPENAI_API_KEY`; chỉ kiểm độ dài.
- Chỉ đẩy lên git phần CSV trong `data/processed/` (và `linking/`), không đẩy dữ liệu thô hay chunk.

## 8. Bẫy kỹ thuật đã gặp

- **Heredoc nuốt dấu `\`**: chạy `python - <<'EOF'` qua Bash tool thì `\\1` thành `\x01`, `\b` thành `\x08`. Sửa code có `\` bằng Edit/Write tool, hoặc tạo bằng `chr(92)`. Sau đó kiểm `grep -c $'[\x01-\x08]' <file>` phải ra 0.
- Đường dẫn dự án có dấu và dấu cách (`Máy tính`, OneDrive): luôn đặt trong ngoặc kép.
- Giữ nguyên kiểu xuống dòng (CRLF/LF) và BOM khi ghi lại CSV, nếu không diff sẽ đổi cả file.
- Container mặc định chạy UTC → service `ingest` đã đặt `TZ: Asia/Ho_Chi_Minh`.
- Postgres dùng cổng **5432** (2026-10-06 dự án khác đã giải phóng; bị chiếm lại thì đổi `POSTGRES_PORT` + `DATABASE_URL` trong `.env`).
- `DATABASE_URL` phải dùng **`127.0.0.1`**, không dùng `localhost`: Windows thử IPv6 `::1` trước, kết nối treo hàng phút.
- Git Bash trên máy này dùng bảng mã cp1258 → `print` tiếng Việt lỗi `UnicodeEncodeError`; chạy script với `PYTHONUTF8=1`.
- psycopg async không chạy trên `ProactorEventLoop` (mặc định Windows): test dùng hook `pytest_asyncio_loop_factories`; Tuần 4 nhớ xử lý cho uvicorn.
- Dữ liệu Qdrant/Postgres dùng **volume Docker**, không dùng thư mục trong dự án (OneDrive đồng bộ sẽ làm hỏng index).
- Windows: DBeaver hoặc công cụ khác đang mở `hust.sqlite` thì `build_db.py` không xoá được file → ngắt kết nối trước.
- `text-embedding-3-large` không hoàn toàn deterministic (nhúng lại cho cosine 0,9966–1,0) → ngưỡng tự kiểm là 0,98.
- `cert_value` là chữ ("5.5÷6.5"); DB có cột số `value_min`/`value_max` để SQL so sánh.
