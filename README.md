# HUST Info & Admission Assistant

Chatbot tra cứu thông tin tuyển sinh và học vụ Đại học Bách khoa Hà Nội (LangGraph, tiếng Việt).
Hai tầng dữ liệu: **bảng số** (PostgreSQL) cho điểm chuẩn, chỉ tiêu, học phí… và **văn bản** (RAG trên Qdrant) cho quy chế, đề án, sổ tay, giới thiệu ngành.

## Trạng thái (2026-09-30)

| Hạng mục | Trạng thái |
|---|---|
| Thu thập dữ liệu | Xong — 14 nguồn văn bản, 24 bảng CSV |
| Chuẩn hoá metadata | Xong — 637 chunk trong `data/rag/normalized/`, `dataset_version = 2026.1` |
| Nối bảng dữ liệu | Chưa làm — xem `docs/PLAN - Data Linking (v1).md` |
| Embedding | Đang chuẩn bị — Qdrant chạy Docker |
| Backend / Frontend | Chưa bắt đầu (mới có khung thư mục) |

## Bố cục

```
backend/    code service (chưa có) + tests/eval/ (bộ câu hỏi đánh giá)
frontend/   giao diện (chưa có)
data/       raw/ (nguồn gốc) · processed/ (CSV) · rag/ (chunk) · programs/ · faculty/
scripts/    xử lý dữ liệu theo lô: thu thập, dựng bảng, sinh chunk, chuẩn hoá, kiểm tra
docs/       PRD, các PLAN, ghi chú, danh sách nguồn
```

Chi tiết: [docs/cautrucduan.md](docs/cautrucduan.md) · Yêu cầu sản phẩm: [docs/PRD.md](docs/PRD.md)

## Chạy thử môi trường

```powershell
Copy-Item .env.example .env          # rồi điền OPENAI_API_KEY vào .env
docker compose up -d                 # khởi động Qdrant
python scripts/check_setup.py --openai
```

## Kiểm tra dữ liệu

```powershell
python scripts/validate_metadata.py            # metadata chunk + CSV, phải 0 lỗi
python scripts/validate_metadata.py --selftest # cài lỗi cố ý, validator phải bắt được
python scripts/validate_aliases.py
python scripts/validate_admission_csv.py
```

Bước embed đọc `data/rag/normalized/`, **không** đọc `data/rag/raw_chunks/`.
