# Cấu trúc thư mục — HUST Info & Admission Assistant

Cập nhật 2026-09-30 sau khi sắp xếp lại dự án. Cấu trúc phản ánh 2 pipeline đã chốt trong PRD: **structured** (PostgreSQL) và **unstructured/RAG** (Qdrant), tách rõ backend / frontend / data / scripts.

Ký hiệu: ✅ đã có nội dung · ⬜ mới có khung thư mục, chưa có code.

```
hust_chatbot/
├── backend/                               ✅ nền DB, Entity Resolution, Admission Tool T1/T2 (2026-10-07); API, graph chưa có
│   ├── app/
│   │   ├── api/                           # chat.py (POST /api/chat, /api/chat/stream), health.py
│   │   ├── graph/                         # LangGraph: state, router, checkpointer, synthesizer
│   │   │   └── guardrails/                # input_guard.py, llm_judge.py
│   │   ├── tools/                         ✅ context.py (dữ liệu nạp 1 lần), common.py (hàm dùng chung),
│   │   │                                  ✅ admission.py (T1, T2), program_info.py (T3), tuition.py (T4), certificate.py (T5),
│   │   │                                  ✅ university_info.py (T6); còn: rag_tool (T7)
│   │   ├── entity_resolution/             ✅ normalize.py, index.py, resolver.py (4 quy tắc PRD 10.3 + fuzzy), scan.py
│   │   ├── rag/                           # retriever.py (đọc Qdrant)
│   │   ├── db/                            ✅ pool.py (psycopg3 async, chỉ đọc, search_path=hust) — không ORM/Alembic
│   │   ├── schemas/                       ✅ common.py (ToolResult), admission.py, program_info.py, tuition.py, certificate.py, university_info.py
│   │   └── core/                          ✅ config.py (Settings đọc .env); logging.py (Langfuse) — Tuần 4
│   ├── requirements.txt, pyproject.toml   ✅ thư viện backend (ghim phiên bản) + cấu hình pytest
│   └── tests/
│       ├── conftest.py, test_db.py        ✅ test nền lớp DB (marker db)
│       ├── test_entity_resolution.py, test_scan.py   ✅ không cần DB
│       ├── test_admission_scores.py, test_list_programs.py, test_program_info.py,
│       │   test_tuition.py, test_certificate.py, test_university_info.py   ✅ marker db
│       ├── test_entity_cases.py           ✅ 104 ca có nhãn AC2/AC8 đã duyệt
│       └── eval/                          ✅ 120_question_check_data.md (bộ câu hỏi đánh giá)
│
├── frontend/                              ⬜ (khung: app/, components/{Chat,Citation,ClarificationPrompt}/, lib/)
│
├── data/
│   ├── raw/                               ✅ nguồn gốc chưa xử lý
│   │   ├── admission/                     # 10 PDF văn bản gốc + ma_nganh_truong.md
│   │   ├── program_pages/                 # HTML 68 trang ngành (ts.hust.edu.vn)
│   │   ├── de_an/, pages/, faculty/       # HTML đề án, bài tuyển sinh, web Trường/Khoa
│   │   ├── admission_scores/, tuition/, de_an_2025_img/, diem_chuan_2025_img/   # ảnh bảng
│   │   ├── tsa_quyche/, kkht_2022/        # ảnh từng trang + bản chép tay (scan)
│   │   ├── sotay_pages/, sotay_overrides/ # ảnh trang Sổ tay + 22 trang chép tay
│   │   └── mon_chinh/                     # trang bên thứ ba dùng đối chiếu môn chính
│   ├── processed/                         ✅ 24 bảng CSV (nguồn bóc từ văn bản) -> DB
│   │   └── linking/                       ✅ bảng nối do người gán: danh mục Trường/Khoa, mã chứng chỉ, bảng cầu
│   ├── db/hust.sqlite                     ⚙ sinh ra bằng build_db.py, không lên git
│   ├── programs/                          ✅ <mã_ngành>.json (68 ngành)
│   ├── faculty/                           ✅ <mã_khoa>/info.json + gioi_thieu.md (10 đơn vị)
│   ├── rag/
│   │   ├── raw_chunks/                    ✅ 622 chunk gốc (14 file .chunks.jsonl + bản .md để đọc)
│   │   └── normalized/                    ✅ 641 chunk đã chuẩn hoá metadata -> ĐEM ĐI EMBED
│   ├── link.md                            ✅ danh sách link nguồn do anh lập (đầu vào thu thập)
│   └── link_dao_tao_nganh.md              ✅ link 68 trang ngành (đầu vào của crawl_program_pages.py)
│
├── scripts/                               ✅ 35 script xử lý dữ liệu (chạy theo lô, không phải service)
│   ├── crawl_*.py, extract_departments.py         # thu thập
│   ├── build_*.py, fix_*.py, add_main_subject.py, verify_subject_combinations.py, aliases.py   # dựng bảng CSV
│   ├── pdf_to_rag_md.py, sotay_to_rag.py, de_an_to_rag.py, scan_md_to_rag.py, faculty_to_rag.py # sinh chunk
│   ├── normalize_chunks.py, normalize_csv_meta.py # chuẩn hoá metadata
│   ├── validate_*.py, check_dangling_refs.py, coverage_report.py, probe_questions.py            # kiểm tra
│   ├── eval_entity_scan.py                        # chạy Entity Resolution trên bộ 120 câu -> docs/ghi_chu/
│   ├── check_setup.py                             # kiểm tra .env + Qdrant + OpenAI
│   ├── embed_chunks.py, search_chunks.py          # nhúng vào Qdrant + tìm thử/đo retrieval
│   ├── build_db.py, validate_links.py             # CSV -> SQLite (+ Postgres với --postgres) + kiểm liên kết
│   ├── Dockerfile, requirements-ingest.txt        # image cho service "ingest" (docker-compose.yml)
│   └── build_source_list.py                       # sinh docs/nguon_du_lieu.md
│
├── docs/                                  ✅
│   ├── PRD.md                             # PRD v1.2 (trước đây: "PRD - HUST Info & Admission Assistant (v1.1).md")
│   ├── PLAN - Data Collection (v1).md
│   ├── PLAN - Metadata Design (v1).md     # lịch sử; bản hiện hành là v2
│   ├── PLAN - Metadata Design (v2).md
│   ├── PLAN - Data Linking (v1).md        # đã thực hiện — SQLite 23 bảng
│   ├── PLAN - Backend PostgreSQL (v1).md  # đã thực hiện — Postgres + pool + test nền
│   ├── PLAN - Tools (v1).md               # kế hoạch 7 tool Tuần 3
│   ├── PLAN - Entity Resolution + Admission Tool (v1).md   # đã thực hiện — chi tiết bước 1–3
│   ├── PLAN - T3 program_info (v1).md     # đã thực hiện — thông tin ngành
│   ├── PLAN - T4 T5 hoc phi va chung chi (v1).md   # đã thực hiện — học phí, lệ phí, chứng chỉ
│   ├── PLAN - T6 university_info (v1).md  # đã thực hiện — Trường/Khoa
│   ├── PLAN - Embedding (v1).md           # đã thực hiện — 641 chunk trong Qdrant
│   ├── nguon_du_lieu.md                   # tổng hợp link nguồn (sinh tự động)
│   ├── cautrucduan.md                     # file này
│   └── ghi_chu/                           # ghi chú theo ngày
│
├── docker-compose.yml                     ✅ Qdrant + Postgres (127.0.0.1:5432) + service "ingest" (sẽ thêm backend + frontend)
├── .env.example                           ✅
├── .gitignore                             ✅
└── README.md                              ✅
```

## Khác với bản đề xuất ban đầu — và vì sao

| Bản đề xuất | Thực tế | Vì sao |
|---|---|---|
| Thư mục gốc `hust-info-assistant/` | Giữ `hust_chatbot/` | Đổi tên thư mục gốc làm đổi đường dẫn của VS Code, OneDrive và bộ nhớ phiên làm việc; không đem lại lợi ích gì cho code. Muốn đổi thì đổi khi tạo repo git. |
| Không có chỗ cho PDF nguồn | `data/raw/admission/` | 10 PDF là "nguồn gốc chưa xử lý" đúng nghĩa `data/raw/`; trước đây nằm lẻ ở `data/admission/`. |
| Không có `data/programs/` | Giữ `data/programs/` | 68 file JSON ngành là dữ liệu đã có, cùng vai trò với `data/faculty/`. |
| `processed/admission_scores.csv`, `quotas.csv` (gộp năm) | Vẫn tách theo năm (`admission_scores_2024/25/26.csv`…) | Gộp bảng là việc của `PLAN - Data Linking` (chưa thực hiện) — gộp bây giờ là làm một nửa kế hoạch đó. |
| `scripts/` liệt kê 4 file | 31 script, để phẳng | Các script import lẫn nhau (`from crawl_pages import fetch`…); chia thư mục con phải sửa import mà chưa cần. Nhóm theo tiền tố tên là đủ tìm. |
| `seed_db.py` | Chưa có | Thuộc Data Linking (nạp CSV -> DB). |
| `backend/app/entity_resolution/validate_aliases.py` | Chỉ có ở `scripts/validate_aliases.py`, nhưng **import resolver của backend** (từ 2026-10-07) | Phép kiểm chạy theo lô nằm ở `scripts/`; thuật toán khớp chỉ có một bản trong backend để validator kiểm đúng cái bot chạy. |
| `backend/app/rag/ingestion.py`, `chunking.py` | Không tạo; việc này do `scripts/` làm | Trích xuất và cắt chunk đã làm xong bằng script (mỗi nguồn một cách cắt riêng, không phải "header-based" chung). Backend chỉ cần `retriever.py`; bước embed sẽ là một script. Viết lại trong backend là có hai bộ cắt chunk cho cùng dữ liệu. |
| `docs/evaluation_report.md` | Chưa có | Tạo khi có kết quả đánh giá (Tuần 2 trở đi). |
| `docker-compose.yml`: postgres + qdrant + backend + frontend | Qdrant + Postgres (2026-10-06) | Thêm từng dịch vụ khi tới bước đó. Postgres dùng cổng 5432 (dự án khác đã giải phóng); bị chiếm lại thì đổi `POSTGRES_PORT` + `DATABASE_URL` trong `.env`. |
| `backend/app/db/models.py`, `migrations/` (Alembic) | Chỉ có `pool.py`, SQL viết tay | DB sinh lại từ CSV mỗi lần build nên không có gì cần migration; thêm ORM model thì schema khai hai nơi (`PLAN - Backend PostgreSQL (v1)` D2). |

## Ranh giới dữ liệu (PRD mục 3.C)

- Bảng số -> `data/processed/` -> PostgreSQL.
- Văn xuôi -> `data/rag/raw_chunks/` -> (chuẩn hoá) -> `data/rag/normalized/` -> Qdrant.
- `scripts/` chỉ chứa xử lý theo lô; `backend/app/` là code service chạy thường trực.

## Thứ tự chạy lại khi nguồn thay đổi

```
python scripts/<script bóc nguồn vừa đổi>.py     # sotay_to_rag, de_an_to_rag, crawl_program_pages --offline, ...
python scripts/add_main_subject.py              # chỉ khi chạy lại verify_subject_combinations --write
python scripts/normalize_csv_meta.py            # bù 6 cột chuẩn cho CSV
python scripts/normalize_chunks.py              # -> data/rag/normalized/
python scripts/validate_metadata.py             # phải 0 lỗi
python scripts/build_db.py --postgres           # -> data/db/hust.sqlite + Postgres schema hust
pytest backend                                  # test nền: DB khớp CSV, chỉ đọc
python scripts/validate_links.py                # phải 0 lỗi
python scripts/build_source_list.py             # cập nhật docs/nguon_du_lieu.md
docker compose run --rm ingest python scripts/embed_chunks.py --recreate   # nhúng lại vào Qdrant
docker compose run --rm ingest python scripts/search_chunks.py --eval     # đo lại retrieval
```
