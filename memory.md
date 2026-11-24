# memory.md — Đúc kết để tiếp tục ở session mới

> **Session mới: đọc file này trước khi làm bất cứ việc gì.** Cập nhật lần cuối: 2026-10-21 (mục 2b là trạng thái Tuần 4 mới nhất; mục 2 bên dưới còn số liệu cũ của 2026-10-06).
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
| **Tuần 3 — Tools** | **Xong 2026-10-11**: Entity Resolution + 7 tool T1–T7, 281 test + 15 ca `rag`; AC2, AC8 100%; hit@5 RAG 88% | `PLAN - Tools (v1).md` và các PLAN T3–T7 |
| **Tuần 4 — LangGraph** | **Đã code Router, StateGraph, Synthesizer, guardrails, đã đo và đang sửa lỗi** (nhánh `langgraph`, chưa commit). Xem mục 2b | `docs/PLAN - Tuan 4 LangGraph (v1).md` và các PLAN con |
| API / Frontend | Chưa có code (`backend/app/api/` còn rỗng) | `docs/cautrucduan.md` |

## 2b. Tuần 4 — trạng thái 2026-10-21 (nhánh `langgraph`, CHƯA COMMIT)

**Kiến trúc** (`backend/app/graph/`): `route()` (gpt-4o-mini, structured output) → `merge` (quy tắc ngữ cảnh C1–C5) → `run_tools` (7 tool song song) → `check_status` → `generate` (Synthesizer) → `verify` (chỉ code) → viết lại tối đa 2 lần → `template_answer` (dựng từ dữ liệu). Mọi nhánh kết thúc ở `save_context`. Sơ đồ thật: `docs/ghi_chu/sodothietke.md` mục 0.
- Router: `language` → `need` (tiếng Việt) → `topic` (11 giá trị, code ánh xạ sang intent) → `calls`. Có chốt chặn bằng code: chống injection, từ chỉ trỏ, `looks_english`. Bộ quét `Scanner` gợi ý trước + `router_check.reconcile` sửa sau (tên kèm mã "(IT1)" → mã; "Bách khoa" ở ô Trường/Khoa → bỏ; cụm Router tự dịch → giữ nếu bộ quét không thấy cụm thay).
- Synthesizer: bằng chứng đánh số `[n]`, bảng dài (> 15 dòng) do code dựng, khối Nguồn do code ghép. `verify` kiểm: số lạ (hai cách đọc dấu , .), trích dẫn `[n]`, văn bản phải có trích dẫn, học phí phải có đơn vị + năm, câu tiếng Anh ≤ 20% từ có dấu tiếng Việt. Kiểm bằng code **không bắt được lỗi hiểu sai nghĩa** (S12, S38).
- Dữ liệu: nhãn `bac_dao_tao` (chung / dai_hoc / ky_su / thac_si / tien_si) cho Quy chế đào tạo, gắn theo chương (script `set_bac_dao_tao.py`, đã cập nhật Qdrant, không nhúng lại). T7 mặc định bỏ `ky_su`, `thac_si`, `tien_si` trừ khi câu nêu rõ.
- Ngôn ngữ: chỉ vi + en. **Toàn câu tiếng Anh mới trả lời tiếng Anh**; câu lẫn → tiếng Việt; ngôn ngữ khác → câu mẫu song ngữ. Không làm dữ liệu sinh viên trao đổi.

**Số đo (mỗi phép chạy 1 lần):** Router AC3 **95,9%** (mục tiêu 95%); Retrieval T7 88%; Synthesizer 41 câu: 0 số lạ, trích dẫn văn bản 22/22, tôi chấm sơ bộ 35/41 đúng. Test: **529 passed** (có Docker). Chi phí đo cả ngày 2026-10-21 ≈ 0,31 USD. P95 thời gian cả lượt ≈ 10 s, **chưa đạt** mục tiêu PRD < 4 s đến chữ đầu (câu có số liệu đệm cả câu rồi mới gửi; chưa quyết đổi sang stream).

**Còn sai (lần đo 2):** S12 (bịa ngưỡng CPA), S17 (bảo lưu: dữ liệu đại học không có điều đó, bản dựng từ dữ liệu dán đoạn lạc đề), S29 (Router viết `need` tiếng Anh), S38 (suy diễn "không yêu cầu"; người dùng chấp nhận là hạn chế đã biết, N7).

**Việc tiếp theo, chờ người dùng:**
1. Chấm lần 2: `docs/ghi_chu/2026-10-21 - Do Synthesizer (lan 2).md`; duyệt 11 câu mới S31–S41 trong `synth_cases.csv` (cột `duyet` trống).
2. Duyệt **N13–N15**: N13 bỏ đoạn thô khỏi bản dự phòng cho câu văn bản (S17); N14 gọi lại Router khi `need` tiếng Anh (S29); N15 kiểm số theo đúng đoạn được trích (S12).
3. **N12 (để sau)**: mức tin cậy 3 bậc do code tính + liên hệ người thật khi tin cậy thấp. Không dùng phần trăm (PRD 13.1). Liên hệ: Ban Tuyển sinh 024 3868 3408 / ts@hust.edu.vn; Ban Đào tạo 024 3869 2104 / dt@hust.edu.vn; Ban Công tác sinh viên 024 3869 2896 / ctsv@hust.edu.vn.
4. Có đo lại Router (≈ 0,19 USD) sau N2/N3/N4 không; rà 13 alias tiếng Anh mới trong `entity_aliases.csv` (281 → 294 dòng); quyết định TTFT; chạy `code-review` rồi người dùng commit.

**Báo cáo chính:** `docs/ghi_chu/2026-10-21 - Bao cao sua loi Synthesizer.md` (kèm các PLAN: State và Context Rules, Router, StateGraph, Synthesizer, Sua loi sau chay thu Synthesizer).

Sơ đồ ER (hiện trạng CSV + mô hình đích): https://claude.ai/artifact/GVonC7WEHGSsyN8nToHprG (trang riêng tư của người dùng). Bản mermaid cũng nằm trong `PLAN - Data Linking (v1).md` mục 1 và 2.4.

## 3. Việc đang dở / làm tiếp

1. **Chưa commit** (lúc viết file này): đổi nhãn `manual_verified` ở 7 file CSV + `docs/PRD.md`, toàn bộ phần backend Postgres (docker-compose, build_db, check_setup, backend/, docs), `memory.md`. Hỏi người dùng đã commit chưa (`git status`). Commit CSV xong thì chạy lại `build_db.py --postgres` để `build_info.git_commit` hết đuôi `-dirty`.
2. **Tool (2026-10-07): Entity Resolution + T1 `admission_scores` + T2 `list_programs` ĐÃ XONG** (`docs/PLAN - Entity Resolution + Admission Tool (v1).md`, mục "Đã thực hiện"). `pytest backend` 281 passed; T1 quét đủ 687 dòng điểm chuẩn đúng 100%. 13 alias phương thức đã ghi vào CSV; `validate_aliases.py` dùng resolver backend, kiểm mọi loại thực thể: 0/0. 2026-10-08: thêm 6 alias (Công nghệ thông tin, Leibniz, Điện - Điện tử, Vật liệu, Quản trị kinh doanh, Cơ điện tử); bộ ca có nhãn `backend/tests/eval/entity_cases.csv` 104 ca **người dùng đã duyệt hết** → **AC2 100%, AC8 100%** (`scripts/eval_entity_cases.py`); mỗi ca là một test trong `test_entity_cases.py`. **T3 `program_info` XONG 2026-10-08** (`docs/PLAN - T3 program_info (v1).md`, 18 ca đã duyệt xanh). Tiếp theo: T4 `tuition_fees` + T5 `certificate_lookup` — plan chi tiết `docs/PLAN - T4 T5 hoc phi va chung chi (v1).md` (2026-10-08), ****T4, T5 XONG 2026-10-09** (mục E của plan; 23 + 19 ca đã duyệt xanh). Đã thêm học phí tín chỉ 2025–2026 (QĐ 10232) và 2026–2027 (QĐ 12006). **T6 `university_info` XONG 2026-10-09** (18 ca đã duyệt xanh; kèm sửa fuzzy bỏ chữ đầu chung trường/khoa/viện/ngành). **T7 retrieval XONG 2026-10-11 — đủ 7 tool Tuần 3** (`docs/PLAN - T7 retrieval (v2).md` mục 7). hit@5 dense 85% → T7 88% (+Q10, Q18, không trượt thêm); thêm 2 chunk học phí khác 2025–2026/2026–2027 (Qdrant 643 điểm, `embed_chunks.py --add-missing`); ca `rag` chạy tay `pytest -m rag`. Câu trường khác (ĐHQGHN 0,645) ngưỡng không chặn → Router Tuần 4. **Tuần 4: plan `docs/PLAN - Tuan 4 LangGraph (v1).md` đã viết 2026-10-12** — sơ đồ graph chi tiết ở `docs/ghi_chu/sodothietke.md` (người dùng vẽ bản đầu, trợ lý sửa 2026-10-12: gộp guard+router+select_tools, bỏ node entity_resolution riêng, tách turn/context, judge ra ngoài luồng) — chờ người dùng trả lời 11 câu ở mục 10 (judge/review_queue là Q11; Router trả JSON hay function calling, SDK openai hay langchain, mốc "năm nay", kiểm số, câu tư vấn, Langfuse ở đâu, rate limit, lịch sử hội thoại, bộ test, quy tắc gán intent + ca M2/M10/G-26). Duyệt xong mới code, bắt đầu từ bước 0 (sửa môi trường) rồi Router + bộ đo AC3.
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
pytest backend                                                              # 529 passed (bỏ qua ca llm, rag; cần Docker)
# Tuần 4 — TỐN TIỀN API, chỉ chạy khi người dùng bảo (mỗi lệnh 1 lần):
python scripts/eval_router.py                                               # ≈ 0,19 USD, 215 câu
python scripts/eval_synth.py                                                # ≈ 0,05 USD, 41 câu
python scripts/set_bac_dao_tao.py                                           # miễn phí: gắn nhãn bậc đào tạo vào Qdrant
pytest backend -m rag                                                       # 15 passed (gọi API embedding, tốn phí nhỏ)
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
- Học phí tín chỉ: có **3 năm học riêng** (2024–2025, 2025–2026 QĐ 10232, 2026–2027 QĐ 12006 — bổ sung 2026-10-09); trả theo đúng năm học, mặc định 2026–2027 (thay quyết định cũ "dùng chung").
- Lệ phí TSA: dòng 2024 trong `admission_fees.csv` là 500.000đ do người dùng sửa và chọn giữ, dù đề án 2024 ghi 450.000đ. **Đừng tự sửa lại.**
- Liên hệ Trường/Khoa: khi `data/link.md` lệch với mục "Đơn vị quản lý" trên trang ngành thì lấy trang ngành; nguồn ghi nhiều hotline thì giữ đủ.
- Cột môn chính lấy từ tuyensinh247 (`main_subject_status = third_party`): **không** đưa vào danh sách nguồn, chatbot **không** trích dẫn.
- "Đáp án mong đợi" trong bộ 120 câu chỉ để tham khảo, không dùng để chấm.
- Tuần 4 (2026-10-21): nhánh **`langgraph`**. Nguyên tắc: **việc gì code làm được thì để code làm, LLM chỉ làm phần hiểu ngôn ngữ**; không thêm quy tắc riêng từng lỗi vào prompt Router (prompt đã ~10.300 token). Hotline/mức tin cậy do code ghép, không để LLM tự viết. Chỉ tiêu dữ liệu chỉ có tổng ngành: phải nói rõ "không tìm thấy chỉ tiêu theo phương thức" rồi mới nêu tổng. S07: chỉ trả lời theo tín chỉ. Chấp nhận lỗi suy diễn trên văn bản là hạn chế đã biết (N7).
- Làm việc trên nhánh **`tool`** từ Tuần 3 (trước đó `embedding_data`; có thêm `main`, `develop`). Không tạo nhánh mới khi chưa hỏi.

## 7. Cách làm việc với người dùng

- Trả lời **tiếng Việt**, giải thích dễ hiểu, chữ có dấu. Người dùng hay gõ tắt, không dấu.
- **Viết plan trước, code sau**: `docs/PLAN - <tên> (v1).md`, mỗi quyết định có **"Vì sao"**, có mục "Cần anh quyết". Làm xong thì thêm mục "Đã thực hiện" (kết quả + lựa chọn phát sinh + vì sao).
- **KHÔNG tự chạy việc tốn tiền API** (`eval_router.py`, `eval_synth.py`, `pytest -m llm|rag`, embedding): nói số lần + chi phí ước tính rồi **chờ người dùng bảo**. Đo **1 lần**, không 3. Người dùng đã từng phản đối vì chi phí.
- Code theo kiểu test trước (skill `mattpocock-skills:tdd`): chốt các "seam" cần test với người dùng trước, mỗi lát một test đỏ → code → xanh. Trước khi commit có thể chạy `code-review`.
- Dữ liệu lệch giữa các nguồn, hoặc quyết định thật sự thuộc người dùng → **hỏi** (AskUserQuestion, có phương án khuyến nghị). Không tự chọn.
- **Người dùng tự commit/push**: đưa câu lệnh, chia commit theo mục đích (`docs/CONVENTIONAL_COMMIT.md`: type viết thường, mệnh lệnh, message không dấu cho an toàn trong PowerShell).
- Sửa dữ liệu thì sửa CSV (nguồn), không sửa DB. Mỗi lần sửa xong chạy lại validator và báo kết quả thật, kể cả khi số đo xấu đi.
- Không đọc/in giá trị `OPENAI_API_KEY`; chỉ kiểm độ dài.
- Chỉ đẩy lên git phần CSV trong `data/processed/` (và `linking/`), không đẩy dữ liệu thô hay chunk.

## 8. Bẫy kỹ thuật đã gặp

- **Heredoc nuốt dấu `\`**: chạy `python - <<'EOF'` qua Bash tool thì `\\1` thành `\x01`, `\b` thành `\x08`. Sửa code có `\` bằng Edit/Write tool, hoặc tạo bằng `chr(92)`. Sau đó kiểm `grep -c $'[\x01-\x08]' <file>` phải ra 0.
- **Lặp lại nhiều lần (Tuần 4):** heredoc làm `\b` thành ký tự điều khiển trong regex (`router.py`, `synthesizer.py`). Regex và văn bản dài chứa nhiều loại nháy → dùng Edit/Write tool. Heredoc dài trộn nháy đơn/kép còn gây `unexpected EOF`.
- OpenAI strict mode: ví dụ few-shot của Router phải điền **đủ mọi trường** schema, nếu không model sinh tab vô tận; thứ tự trường = thứ tự sinh.
- Lỗi mạng OpenAI chập chờn có thể làm hỏng cả lần đo (client `max_retries = 0`, timeout 20 s); lần đo hỏng vẫn tốn tiền. Kiểm kết quả (số câu `llm_error`) trước khi tin.
- Tool giả trong test graph phải trả object có `.model_dump(mode="json")` như `ToolResult` thật.
- Ruff có sẵn nhiều cảnh báo kiểu `re.I` (FURB167) trong dự án: để nguyên, chỉ sửa cái do mình thêm.
- Đường dẫn dự án có dấu và dấu cách (`Máy tính`, OneDrive): luôn đặt trong ngoặc kép.
- Giữ nguyên kiểu xuống dòng (CRLF/LF) và BOM khi ghi lại CSV, nếu không diff sẽ đổi cả file.
- Container mặc định chạy UTC → service `ingest` đã đặt `TZ: Asia/Ho_Chi_Minh`.
- Postgres dùng cổng **5432** (2026-10-06 dự án khác đã giải phóng; bị chiếm lại thì đổi `POSTGRES_PORT` + `DATABASE_URL` trong `.env`).
- `DATABASE_URL` phải dùng **`127.0.0.1`**, không dùng `localhost`: Windows thử IPv6 `::1` trước, kết nối treo hàng phút.
- Git Bash trên máy này dùng bảng mã cp1258 → `print` tiếng Việt lỗi `UnicodeEncodeError`; chạy script với `PYTHONUTF8=1`.
- psycopg async không chạy trên `ProactorEventLoop` (mặc định Windows): test dùng hook `pytest_asyncio_loop_factories`; Tuần 4 nhớ xử lý cho uvicorn.
- Dữ liệu Qdrant/Postgres dùng **volume Docker**, không dùng thư mục trong dự án (OneDrive đồng bộ sẽ làm hỏng index).
- Windows: DBeaver hoặc công cụ khác đang mở `hust.sqlite` thì `build_db.py` không xoá được file → ngắt kết nối trước.
- **`import langgraph` lỗi** (`Reviver.__init__() got an unexpected keyword argument 'allowed_objects'`, đo 2026-10-12): máy có `langgraph 1.2.11` nhưng `langchain-core 0.2.43` (kèm `langchain` 0.2, `langchain-openai` 0.1, `langchain-community` 0.2 cài từ trước, không file nào trong dự án dùng). Sửa ở bước 0 Tuần 4 theo câu trả lời Q2.
- `text-embedding-3-large` không hoàn toàn deterministic (nhúng lại cho cosine 0,9966–1,0) → ngưỡng tự kiểm là 0,98.
- `cert_value` là chữ ("5.5÷6.5"); DB có cột số `value_min`/`value_max` để SQL so sánh.
