# PLAN — Nền backend + PostgreSQL (v1)

**Ngày:** 2026-10-05 · **Trạng thái:** đã thực hiện 2026-10-06 (xem mục "Đã thực hiện" cuối file; cổng đổi thành **5432**) · Gắn với PRD v1.2 mục 15.1 (schema), 19 (API), 20 (Tuần 3), 22.2 (P95 query < 500 ms), 23 (biến môi trường) · Đi trước: `PLAN - Data Linking (v1).md` (R9, mục "Còn lại")

Mỗi quyết định có dòng **Vì sao**.

Đây là việc số 1 của Tuần 3. Các việc sau (Entity Resolution, Admission SQL Tool, RAG Tool, University Info Tool) đều đọc dữ liệu qua lớp DB dựng ở đây.

---

## 1. Hiện trạng

| Thành phần | Đang có | Còn thiếu |
|---|---|---|
| Dữ liệu | 23 bảng trong `data/db/hust.sqlite`, sinh từ CSV bằng `scripts/build_db.py`; 0 trùng khoá, 0 khoá ngoại mồ côi | Chưa có PostgreSQL |
| Docker | `qdrant` (6333/6334) + `ingest` (profile `tools`, mount chỉ đọc) | Chưa có service `postgres` |
| Backend | Chỉ có khung thư mục `backend/app/*/.gitkeep` | Chưa có config, kết nối DB, test |
| Thư viện trên máy | Python 3.12, `pydantic 2.13`, `pydantic-settings 2.15`, `pytest 9.1`, `langgraph 1.2`, `SQLAlchemy 2.0` | `psycopg`, `psycopg-pool`, `fastapi` |

Ràng buộc đã biết: cổng 5432 trên máy đang bị Postgres của dự án khác chiếm, nên dùng cổng **5433** (R9). Lúc viết plan này Docker Desktop đang tắt, cần bật lên trước khi làm bước 1.

---

## 2. Kiến trúc đích

```
data/processed/*.csv ──(build_db.py)──► SQLite (cổng kiểm tra: trùng khoá, khoá mồ côi)
                                    └──► PostgreSQL :5433
                                          ├── schema "hust"      ← dữ liệu tuyển sinh, chỉ đọc, xoá-dựng lại mỗi lần build
                                          └── schema "langgraph" ← checkpointer hội thoại (Tuần 4), app ghi, KHÔNG bao giờ bị xoá

backend/app/core/config.py   Settings (pydantic-settings) đọc .env
backend/app/db/pool.py       pool psycopg3 async: search_path=hust, chỉ đọc
backend/app/tools/*.py       viết SQL tay, có tham số, gọi qua pool
```

### 2.1 Các quyết định

| # | Quyết định | Vì sao |
|---|---|---|
| D1 | **CSV vẫn là bản gốc, Postgres là sản phẩm sinh ra**, giống SQLite hiện nay. Sửa dữ liệu thì sửa CSV rồi chạy lại `build_db.py --postgres` | Giữ đúng một chỗ sửa dữ liệu. Nếu sửa thẳng trong Postgres thì lần build sau sẽ ghi đè mất |
| D2 | **Không dùng Alembic, không dùng ORM (SQLAlchemy models)** cho dữ liệu tuyển sinh. Schema chỉ khai một lần trong `build_db.py` (chuỗi `DDL`) | Alembic dùng để *nâng cấp dần* một DB đang chứa dữ liệu người dùng ghi. DB này bị xoá và dựng lại mỗi lần build nên không có gì cần nâng cấp. Thêm ORM models thì schema bị khai hai nơi, dễ lệch nhau. `cautrucduan.md` đang ghi `models.py` và `migrations/ (Alembic)` nên sẽ sửa lại cho khớp |
| D3 | **Hai schema trong cùng một database**: `hust` (dữ liệu) và `langgraph` (checkpointer, Tuần 4) | Build chạy `DROP SCHEMA hust CASCADE`. Nếu checkpointer nằm chung schema thì mỗi lần cập nhật dữ liệu sẽ xoá sạch hội thoại đang dở. Tách schema thì không cần dựng thêm database, cũng không cần thêm user |
| D4 | **Nạp Postgres trong một transaction**: `DROP SCHEMA hust` → `CREATE SCHEMA` → tạo bảng → chèn dữ liệu → `COMMIT` | Postgres hỗ trợ DDL trong transaction. Lỗi giữa chừng thì rollback, dữ liệu cũ còn nguyên, backend không bao giờ thấy DB rỗng một nửa. Khoảng 2.500 dòng nên nạp chỉ mất vài giây |
| D5 | **Vẫn dựng SQLite trước làm cổng kiểm tra**, chỉ khi qua mới nạp Postgres. `validate_links.py` giữ nguyên, tiếp tục đọc SQLite | Postgres kiểm khoá ngoại ngay lúc chèn và dừng ở lỗi *đầu tiên*. Còn `PRAGMA foreign_key_check` của SQLite liệt kê *hết* lỗi trong một lần, đúng cách `build_db.py` đang báo lỗi. Giữ được hành vi này mà không phải viết lại phần kiểm tra |
| D6 | **Kiểu cột riêng cho Postgres:** `REAL` → `NUMERIC`. Mọi khoá ngoại thêm `DEFERRABLE INITIALLY DEFERRED`. Cách làm: một chuỗi DDL có hai chỗ giữ chỗ `{REAL}`, `{FK}`, render ra hai bản cho hai loại DB | Trong Postgres `REAL` là số thực 4 byte, nên 82.10 lưu thành 82.0999985. Như vậy so điểm bằng nhau hoặc tính chênh lệch sẽ sai, mà AC1 đòi tool đúng 100%. Còn `DEFERRABLE` thì khoá ngoại chỉ được kiểm lúc COMMIT, nên thứ tự chèn không còn quan trọng. Riêng `admission_methods.parent_method` tự tham chiếu chính bảng nó: không hoãn kiểm tra thì sẽ lỗi nếu dòng con đứng trước dòng cha trong CSV |
| D7 | Các kiểu khác **giữ nguyên** (`TEXT` cho ngày, `INTEGER` 0/1 cho cờ) | PRD ghi "schema và câu SQL giữ nguyên" khi chuyển DB. Đổi sang `DATE`/`BOOLEAN` không đem lại lợi gì cho tool mà làm hai bản schema lệch nhau |
| D8 | **Driver psycopg 3 (async) + psycopg-pool**, viết SQL tay có tham số. Không dùng SQLAlchemy | Checkpointer Postgres của LangGraph (`langgraph-checkpoint-postgres`) chạy trên psycopg 3, dùng chung driver thì chỉ có một kiểu kết nối. FastAPI + stream SSE là async: gọi DB kiểu đồng bộ trong endpoint async sẽ chặn event loop. Mỗi tool chỉ có 1–3 câu SELECT nên không cần lớp trừu tượng |
| D9 | **Pool dữ liệu đặt `default_transaction_read_only=on` và `search_path=hust`** qua tham số `options` của kết nối | Tool nào lỡ chạy lệnh ghi thì Postgres từ chối luôn. Cách này cũng chạy được trên Postgres thuê ngoài (Railway/Render chỉ cấp một user), không phải quản lý role riêng |
| D10 | Thêm bảng **`build_info`** (`built_at`, `git_commit`, `csv_sha256`, `dataset_version`) vào schema `hust` | Khi CSV đã sửa mà quên chạy lại build, test sẽ báo "DB cũ hơn CSV" thay vì chạy qua trên số liệu cũ. Đây là loại lỗi dễ gặp vì CSV đang được soát tay thường xuyên |
| D11 | Image **`postgres:17-alpine`**, volume Docker có tên `hust_pg_data`, chỉ mở `127.0.0.1:5433` | Bản 17 ổn định và được mọi thư viện hỗ trợ. Bản 18 đổi đường dẫn thư mục dữ liệu trong image nên dễ gắn nhầm volume. Dùng volume Docker chứ không dùng thư mục trong dự án: lý do giống Qdrant, dự án nằm trong OneDrive, OneDrive đồng bộ file dữ liệu Postgres sẽ làm hỏng DB. Chỉ mở cho localhost vì đây là DB local, mật khẩu đơn giản |
| D12 | `build_db.py` **chạy trên máy** (ngoài Docker), nối vào `localhost:5433` | Service `ingest` gắn thư mục dự án ở chế độ chỉ đọc nên không ghi được `data/db/hust.sqlite`. Script vốn đang chạy trên máy, chỉ cần cài thêm `psycopg` |
| D13 | Test đụng DB chạy trên **Postgres thật** (gắn marker `db`). Thiếu Postgres thì test **báo lỗi kèm gợi ý lệnh**, không bỏ qua im lặng | SQLite và Postgres khác nhau đúng ở những chỗ tool hay dùng: `NUMERIC` trả về `Decimal`, `= ANY(%s)` với list, so sánh chuỗi tiếng Việt. Test trên SQLite sẽ qua nhưng chạy thật vẫn có thể lỗi. Còn nếu bỏ qua im lặng thì cả bộ test xanh dù chưa test gì. Test không cần DB (chuẩn hoá chuỗi trong Entity Resolution) vẫn chạy được khi Docker tắt |

---

## 3. Các bước thực hiện

| Bước | Việc | Ước lượng | Xong khi | Vì sao ở vị trí này |
|---|---|---|---|---|
| 0 | Commit các CSV đang sửa dở (điểm chuẩn, học phí, `faculties.csv`) | 5 phút | `git status` sạch phần `data/processed/` | `build_info.git_commit` phải trỏ tới đúng phiên bản dữ liệu đã nạp |
| 1 | **Docker + .env:** thêm service `postgres` vào `docker-compose.yml` (healthcheck `pg_isready`, `restart: unless-stopped`, mật khẩu đọc từ `.env` qua `${POSTGRES_PASSWORD:?}`). Thêm vào `.env.example`: `POSTGRES_PASSWORD`, `DATABASE_URL=postgresql://hust:<mk>@localhost:5433/hust` | ~30 phút | `docker compose up -d` bật cả qdrant và postgres; `psql -h localhost -p 5433 -U hust` vào được | Mọi bước sau cần có server để nối vào |
| 2 | **`build_db.py --postgres`:** DDL có chỗ giữ chỗ (D6); `create_pg()` nạp trong một transaction (D4) với `%s` thay cho `?`; ghi `build_info` (D10); sau khi nạp, so số dòng từng bảng giữa SQLite và Postgres. Không có cờ `--postgres` thì chạy như cũ | ~1,5h | Lệnh in số dòng 24 bảng (23 + `build_info`) khớp SQLite; chạy lại lần 2 vẫn sạch | Phần duy nhất đụng dữ liệu: làm xong thì Postgres có đủ dữ liệu, các bước sau chỉ việc đọc |
| 3 | **Khung backend:** `backend/requirements.txt` (ghim phiên bản: `psycopg[binary]`, `psycopg-pool`, `pydantic-settings`, `pytest`, `pytest-asyncio`; FastAPI để Tuần 4); `backend/pyproject.toml` (cấu hình pytest, `pythonpath = .`, khai marker `db`); `app/core/config.py` (`Settings`: `DATABASE_URL`, `QDRANT_URL`, `QDRANT_COLLECTION`, `OPENAI_API_KEY`, `EMBEDDING_MODEL`); `app/db/pool.py` (`open_pool()`, `close_pool()`, `fetch_all(sql, params) -> list[dict]`) | ~1h | `python -c "from app.core.config import settings"` chạy được trong `backend/` | Cung cấp đúng một đường dùng chung cho các tool: tool chỉ viết SQL, không tự mở kết nối |
| 4 | **Test nền** `backend/tests/test_db.py` (marker `db`): (a) `build_info.csv_sha256` khớp CSV hiện tại; (b) số dòng các bảng chính > 0; (c) câu INSERT bị từ chối (D9); (d) đọc một điểm chuẩn mẫu (IT-E10, 2025, THPT = 29.39) đúng như CSV; (e) truy vấn `program_code = ANY(%s)` với list 3 mã trả đủ 3 ngành | ~45 phút | `pytest -m db` xanh; tắt Postgres thì báo lỗi kèm câu "chạy `docker compose up -d postgres`" | Khoá lại các giả định mà mọi tool phía sau dựa vào. Nếu hỏng thì hỏng ở đây, không lan sang test của tool |
| 5 | **Cập nhật tài liệu:** `cautrucduan.md` (bỏ `models.py`/Alembic, thêm `pool.py`, ghi lệnh chạy), dòng "Lệch so với deliverable" ở PRD mục 20, `check_setup.py` thêm bước kiểm Postgres | ~20 phút | Tài liệu khớp code | Theo quy ước: mỗi lần lệch kế hoạch đều ghi lại lý do |

**Tổng: khoảng 4 giờ.**

Lệnh chạy sau khi xong:

```bash
docker compose up -d                        # qdrant + postgres
python scripts/build_db.py --postgres       # CSV -> SQLite (kiểm tra) -> Postgres
cd backend && pytest -m db                  # test nền
```

---

## 4. Các bước sau dùng lớp DB thế nào (để thống nhất từ đầu)

| Việc sau | Dùng gì từ bước này | Ghi chú |
|---|---|---|
| Entity Resolution | Một câu SELECT lúc khởi động để nạp `entity_aliases` + `programs` + `program_years` vào bộ nhớ, sau đó tra cứu bằng Python | Chỉ 253 alias. Bốn quy tắc khớp đã viết bằng Python trong `validate_aliases.py`; nếu viết lại bằng SQL thì một logic phải giữ ở hai nơi. Cột `normalized_alias` (PRD 15.1) tính trong bộ nhớ, không lưu vào DB, để hàm chuẩn hoá chỉ có một bản |
| Admission SQL Tool | `fetch_all("... WHERE program_code = ANY(%(codes)s) AND year = ANY(%(years)s)", ...)` | Danh sách tối đa 3 phần tử (PRD 10.2) truyền thẳng thành mảng Postgres, không phải tự ghép chuỗi `IN (...)`. `score` trả về `Decimal`, chuyển sang `float` ở model Pydantic đầu ra |
| University Info Tool | `faculties` ⨝ `faculty_units` | Không cần gì thêm |
| Checkpointer (Tuần 4) | Pool thứ hai: `search_path=langgraph`, được ghi, `autocommit=True`; gọi `AsyncPostgresSaver.setup()` một lần | Đã chừa sẵn schema riêng (D3) |

Về hiệu năng (PRD 22.2, P95 < 500 ms): bảng lớn nhất khoảng 660 dòng và khoá chính đã bắt đầu bằng `(program_code, year, ...)`, đúng kiểu lọc của tool. Vì vậy **chưa thêm index**, đo lại ở Tuần 6.

---

## 5. Rủi ro

| Rủi ro | Cách xử lý |
|---|---|
| Cổng 5433 cũng bị chiếm | Bước 1 chạy `netstat -ano \| findstr 5433` trước. Nếu bị chiếm thì đổi cổng ở một chỗ (`docker-compose.yml` + `.env`) |
| Quên chạy lại build sau khi sửa CSV | Test (a) ở bước 4 bắt được (D10) |
| Docker Desktop tắt thì test `db` đỏ | Đúng ý đồ (D13). Test không cần DB vẫn chạy được |
| `Decimal` lọt vào JSON trả về cho LLM thành chuỗi `"29.39"` | Ép kiểu `float` ở model Pydantic đầu ra của tool (mục 4) |

---

## 6. Cần anh quyết

1. **Giữ SQLite làm cổng kiểm tra** (D5, khuyến nghị) hay bỏ hẳn SQLite, chỉ dùng Postgres? Bỏ thì phải viết lại phần báo khoá mồ côi và sửa `validate_links.py` để nối vào Postgres.
2. **Bỏ Alembic và ORM** (D2, khuyến nghị) và sửa `cautrucduan.md` cho khớp. Hay anh muốn giữ, vì đồ án cần trình bày migration?
3. **Async** (D8, khuyến nghị) hay đồng bộ? Đồng bộ thì test dễ viết hơn, nhưng sang Tuần 4 làm stream SSE sẽ phải bọc lại.

---

# Đã thực hiện (2026-10-06)

## Quyết định ở mục 6

Anh bảo "làm tiếp theo kế hoạch" mà không chọn riêng từng mục, nên cả ba đi theo khuyến nghị: (1) giữ SQLite làm bước kiểm tra, (2) bỏ Alembic/ORM, (3) async psycopg 3. Muốn đổi mục nào thì báo. Mục (3) nên chốt trước khi viết tool, vì sau đó đổi sẽ phải sửa nhiều.

## Kết quả

| Bước | Kết quả |
|---|---|
| 0 | **Chưa làm**: CSV vẫn chưa commit, nên `build_info.git_commit` ghi `ba60566-dirty` (đuôi `-dirty` do script tự thêm khi `data/processed/` có thay đổi chưa commit) |
| 1 | Service `postgres` (`postgres:17-alpine`, container `hust-postgres`, volume `hust_pg_data`, `127.0.0.1:5432`) trong `docker-compose.yml`. `.env` / `.env.example` thêm `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `DATABASE_URL` |
| 2 | `python scripts/build_db.py --postgres`: 23 bảng + `build_info`, 2.828 dòng, khớp SQLite từng bảng, mất khoảng 3 giây. Chạy lại lần hai vẫn sạch. Thử nạp một dòng có khoá ngoại sai: `ForeignKeyViolation` lúc COMMIT, rollback xong dữ liệu cũ còn nguyên (687 dòng điểm chuẩn, `built_at` không đổi) |
| 3 | `backend/requirements.txt`, `backend/pyproject.toml`, `app/core/config.py` (`get_settings()`), `app/db/pool.py` (`open_pool`, `close_pool`, `get_pool`, `fetch_all`, `fetch_one`) |
| 4 | `backend/tests/test_db.py`: 6/6 xanh trong 0,3 giây. Test so **từng dòng** trong 3 file điểm chuẩn với DB (kiểu `Decimal`, khớp đúng số), không chỉ một dòng mẫu như plan ghi. Tắt Postgres thì mỗi test báo "Không kết nối được PostgreSQL… Chạy: docker compose up -d postgres…" |
| 5 | `check_setup.py` thêm mục 3 "PostgreSQL" (kết nối + thời điểm nạp). `cautrucduan.md` và PRD mục 20 đã cập nhật |

## Các lựa chọn phát sinh lúc làm — và vì sao

| Chỗ | Làm | Vì sao |
|---|---|---|
| Cổng | **5432** thay vì 5433 | Anh báo dự án kia đã giải phóng 5432. Cổng vẫn đổi được qua `POSTGRES_PORT` trong `.env` (mặc định 5432), phòng khi dự án kia bật lại Postgres |
| `DATABASE_URL` | Dùng `127.0.0.1`, **không** dùng `localhost` | Đã gặp: trên Windows `localhost` thử IPv6 (`::1`) trước, mà Postgres chỉ mở `127.0.0.1`. Kết quả là `build_db.py` treo quá 2 phút. Đổi sang `127.0.0.1` thì kết nối mất 0,02 giây. Đã ghi chú trong `.env.example` |
| Đổi DDL sang Postgres (D6) | Hàm `pg_ddl()` đổi DDL SQLite bằng regex (`REAL` → `NUMERIC`, thêm `DEFERRABLE INITIALLY DEFERRED` sau mỗi `REFERENCES`), không dùng chỗ giữ chỗ `{REAL}`/`{FK}` như plan ghi | Chuỗi DDL gốc giữ nguyên, SQLite không bị ảnh hưởng gì, cách nhau chỉ nằm ở một hàm 3 dòng |
| `csv_fingerprint()` | Băm mọi CSV trong `data/processed/` và `linking/`, bỏ khác biệt CRLF/LF | Git trên Windows tự đổi kiểu xuống dòng khi checkout. Không bỏ thì test sẽ báo "DB cũ" dù dữ liệu không đổi |
| `build_info` | Chỉ có ở Postgres | `validate_links.py` duyệt mọi bảng SQLite. Thêm bảng lạ vào đó thì phải sửa thêm validator mà không được lợi gì |
| Đọc `.env` trong `build_db.py` | Hàm `load_env()` tự viết 6 dòng, không dùng python-dotenv | Script chỉ cần thêm `psycopg`, và chỉ cần khi chạy với `--postgres` (import muộn). Build SQLite vẫn không cần cài gì thêm |
| Event loop trên Windows | Hook `pytest_asyncio_loop_factories` trả về `SelectorEventLoop` | psycopg async không chạy trên `ProactorEventLoop`, vòng lặp mặc định của Windows. Fixture `event_loop_policy` cũ đã bị pytest-asyncio 1.4 báo sắp bỏ. **Tuần 4 nhớ xử lý tương tự cho uvicorn** |
| `fetch_all(sql: LiteralString, ...)` | Kiểu `LiteralString` cho câu SQL | Ghép chuỗi từ câu hỏi người dùng vào SQL sẽ bị type checker báo lỗi. Giá trị bắt buộc phải đi qua tham số `%(ten)s` |
| Pool chưa mở | `get_pool()` báo lỗi rõ ràng, không tự mở pool | Vòng đời pool gắn với một event loop. Để FastAPI lifespan và conftest mở một lần thì dễ đoán hơn là tự mở ngầm ở lần gọi đầu |
| `.gitkeep` | `git rm` `app/core/.gitkeep`, `app/db/migrations/.gitkeep` (đã stage) | `core/` đã có file thật; `migrations/` bỏ theo D2 |
| Chạy script trong Git Bash | Đặt `PYTHONUTF8=1` | Terminal Git Bash trên máy này dùng bảng mã cp1258, nên `print` tiếng Việt lỗi `UnicodeEncodeError`. Lỗi này có từ trước, không phải do script; chạy trong terminal VS Code/PowerShell thì không gặp |

## Thứ tự chạy lại khi CSV đổi

```bash
docker compose up -d                        # qdrant + postgres
python scripts/build_db.py --postgres       # CSV -> SQLite (kiểm tra) -> Postgres
python scripts/validate_links.py            # vẫn đọc SQLite
pytest backend                              # test nền: DB khớp CSV, chỉ đọc
```

## Còn lại

- Bước 0: anh commit các CSV đang sửa dở, rồi chạy lại `build_db.py --postgres` để `git_commit` hết đuôi `-dirty`.
- Pool thứ hai cho checkpointer (schema `langgraph`, ghi được): Tuần 4.
- Tiếp theo trong Tuần 3: Entity Resolution (mục 4).
