# PLAN — StateGraph: nối các mảnh thành một luồng (v1)

**Ngày:** 2026-10-18 · **Trạng thái:** đã thực hiện G1–G6 (2026-10-19), xem mục 12 · Phần còn lại của bước 2, `PLAN - Tuan 4 LangGraph (v1).md` mục 9 · Dùng: `PLAN - State va Context Rules (v1).md` (đã code), `PLAN - Router (v1).md` (đã code, AC3 94,7% trên nhãn đã duyệt) · PRD 13.2, 14, 19, 24, 4.6

Mỗi quyết định có dòng **Vì sao**. Tôi chỉ code sau khi anh duyệt.

**Deliverable:** một graph LangGraph chạy được một lượt hỏi từ đầu đến cuối: tin nhắn → hỏi lại / từ chối / thông báo / trả lời → lưu ngữ cảnh theo `thread_id`. Mọi nhánh của sơ đồ có test.

**Bước này KHÔNG tốn tiền API:** mọi test dùng Router giả và tool giả, checkpointer trong bộ nhớ. Không gọi OpenAI, không cần Postgres hay Qdrant để chạy test.

**Không làm ở bước này:**
- Synthesizer thật và kiểm số (bước 3). Nhánh trả lời dùng bản nháp từ dữ liệu thô (mục 7).
- Checkpointer Postgres (bước 4).
- FastAPI, SSE, giới hạn tần suất (bước 6).
- Langfuse (bước 7).

---

## 1. Hiện trạng: các mảnh đã có và cách ghép

| Mảnh | File | Vai trò trong graph |
|---|---|---|
| `ChatState`, `ConvContext`, `Turn`, `Pending` | `graph/state.py` | Kiểu của state graph |
| `pick_choice`, `merge_pick`, `merge_context`, `build_pending`, `update_context`, `register_unclear` | `graph/context_rules.py` | Logic của node `pick_choice`, `merge`, `clarification`, `save_context` |
| `route()` → `RouterOutput` (intent, language, calls, pick_status, picked…) | `graph/router.py` | Node `router` |
| 7 tool `async fn(inp, ctx) -> ToolResult` | `tools/*.py` | Node `run_tools` qua `dispatch.py` (mới) |
| `ToolContext` nạp một lần | `tools/context.py` | Truyền vào tool; `program_group` cho `pick_choice` |
| `TOO_MANY_MESSAGE` | `tools/common.py` | Câu mẫu "quá 3 thực thể" (đã có) |

`sodothietke.md` viết **trước** khi có Router và quy tắc ngữ cảnh, nên thiếu `merge_pick`, `register_unclear`, trường `choice`, `pick_status`. Mục 2 dưới đây là bản thay thế; xong bước này tôi cập nhật lại `sodothietke.md`.

---

## 2. Luồng một lượt

```text
START
  │
start_turn          Turn mới; thêm tin nhắn người dùng vào lịch sử (cắt mục 8)
  ├─ có pending ──► pick_choice      đường tắt không LLM (nút bấm / khớp chữ, không phần thừa)
  │                   ├─ chọn được ──────────────► run_tools
  │                   ├─ "tất cả" mà > 3 lựa chọn ► clarification (xin chọn tối đa 3)
  │                   └─ không ───────────────────┐
  ▼                                               │
router  ◄─────────────────────────────────────────┘   1 lần LLM; lỗi 2 lần → fallback LLM_ERROR
  │  (đang chờ chọn — xét pick_status trước)
  ├─ cancel ─────────────────────────────────────► fallback (câu mẫu "đã bỏ câu hỏi trước")
  ├─ unclear ──► register_unclear ─ lần 1 ───────► clarification (hỏi lại, kèm cách chọn)
  │                                └ lần 2 ───────► fallback (thả câu hỏi lại)
  ├─ picked ─────────────────────────────────────► merge (merge_pick)
  │  (new_question / không có pending — xét intent)
  ├─ OTHER_UNIVERSITY / GENERAL_OFF_TOPIC / UNKNOWN ► fallback
  ├─ CLARIFICATION_NEEDED ───────────────────────► clarification (thiếu thông tin)
  └─ còn lại ────────────────────────────────────► merge (merge_context)
                                                     │
                                                  run_tools     dispatch song song; lệnh có `done` thì không chạy lại
                                                     │
                                                  check_status  (mục 4)
                                                     ├─► clarification   (tool trả ambiguous)
                                                     ├─► announcement    (link kênh chính thức)
                                                     ├─► fallback        (invalid, không có dữ liệu, lỗi)
                                                     └─► answer          (tạm: bản nháp từ dữ liệu thô, mục 7)
clarification / announcement / fallback / answer ──► save_context ──► END
```

**Vì sao `pick_choice` đứng trước Router mà vẫn có nhánh `picked` sau Router:** đây đúng là "cách 3 gọn" anh đã chốt (PLAN State 4.3b). Tin nhắn chỉ có lựa chọn ("TE-E2", nút bấm) đi đường tắt, không tốn LLM. Có thêm thông tin ("TE-E2, năm 2024") thì Router xử lý cả câu, rồi `merge_pick` ghép.

**Vì sao mọi nhánh kết thúc ở `save_context`:** một chỗ duy nhất quyết định ngữ cảnh sau lượt, đúng bảng 4.4 của PLAN State. Nhánh nào quên cập nhật ngữ cảnh là lỗi khó thấy; gom về một node thì test một chỗ là đủ.

---

## 3. Node

| Node | Có LLM | Việc | Ghi vào `turn` |
|---|---|---|---|
| `start_turn` | Không | `new_turn(question, choice)`; thêm tin nhắn người dùng vào `messages` | `question`, `choice` |
| `pick_choice` | Không | Gọi `pick_choice(question, pending, choice, ctx.program_group)` | `calls` (nếu chọn được), `outcome` |
| `router` | **Có** | Gọi `route(question, context, messages, today)`; bắt `RouterError` | `router`, `language`, `intent` |
| `merge` | Không | `picked` → `merge_pick`; còn lại → `merge_context`; `new_question` thì bỏ `pending` trước (C5) | `calls` |
| `run_tools` | Không | `dispatch.run_calls(calls, ctx)` (mục 5) | `results` |
| `check_status` | Không | Chọn nhánh theo bảng mục 4 | `route` |
| `clarification` | Không | Dựng câu hỏi lại + danh sách lựa chọn; `build_pending` | `answer`, `clarification`, `outcome = clarify`, `pending_new` |
| `announcement` | Không | Lấy `official_channel_url` từ kết quả T6 | `answer`, `citations`, `outcome = answered` |
| `fallback` | Không | Câu mẫu theo `fallback_reason` | `answer`, `outcome` (refused / cancel / released / answered) |
| `answer` | Không (tạm) | Bản nháp từ dữ liệu thô (mục 7); bước 3 thay bằng `generate` → `verify` | `answer`, `citations`, `outcome = answered` |
| `save_context` | Không | `update_context(...)` theo `outcome`; thêm câu trả lời vào lịch sử | `intent_final` |

`outcome` là cầu nối giữa các node trả lời và `save_context`:

| `outcome` | Đặt bởi | `save_context` làm |
|---|---|---|
| `answered` | `answer`, `announcement`, fallback "không có dữ liệu" | `update_context("answered")`: lưu mã đã xác nhận, xoá `pending` |
| `clarify` | `clarification` | `update_context("clarify", pending=...)` |
| `refused` | fallback từ chối, lỗi hệ thống | Không đổi gì (M10, M25) |
| `cancel`, `released` | fallback huỷ / thả câu hỏi lại | Chỉ bỏ `pending` |

**Vì sao fallback "không có dữ liệu" tính là `answered`:** người dùng hỏi hợp lệ về IT1 năm 2020; ngữ cảnh vẫn nên nhớ IT1 để lượt sau "thế còn 2025?" chạy đúng. Chỉ từ chối và lỗi hệ thống mới giữ nguyên ngữ cảnh.

---

## 4. `check_status`: rẽ nhánh khi có nhiều kết quả

Xét theo thứ tự, gặp điều kiện đúng đầu tiên thì dừng:

| # | Điều kiện | Nhánh | Vì sao |
|---|---|---|---|
| 1 | Có tool `ambiguous` | `clarification`. Kết quả tool khác đã xong được giữ trong `pending.done` | Anh đã chốt "giữ sẵn kết quả có được". Hỏi lại trước khi trả lời để không trả lời một nửa câu hỏi |
| 2 | Có tool `invalid` | `fallback` với `message` của tool (vd "Vui lòng hỏi từng ngành/năm…") | **Cần anh quyết (Q1).** Người dùng hỏi quá 3 thực thể; trả lời phần còn lại dễ gây hiểu là đã trả lời đủ |
| 3 | intent = ANNOUNCEMENT và T6 có `official_channel_url` | `announcement` | AC9 |
| 4 | Mọi tool `not_found` (kể cả T7 độ tin cậy thấp) hoặc lỗi | `fallback` với lý do cụ thể (mục 6.2) | PRD 13.2: nói rõ thiếu gì, có gì; không bịa |
| 5 | Còn lại (ít nhất một tool `ok` / `partial`) | `answer`. Tool `not_found` / lỗi đi kèm được ghi vào phần "thiếu" | Có dữ liệu thì trả lời phần có, nói rõ phần thiếu (PRD 13.2) |
| 6 | Intent nội dung mà Router không gọi tool nào | `fallback` "chưa xác định được cần tra gì" + gợi ý cách hỏi | Phòng hờ: Router hiếm khi làm vậy, nhưng không được trả lời khi không có dữ liệu (AC5) |

---

## 5. `dispatch.py`: chạy tool

```python
TOOLS = {"admission_scores": (admission_scores, AdmissionScoresInput), ...}   # 7 tool

async def run_calls(calls, ctx, tools=TOOLS) -> list[dict]:
    """Chạy song song; lệnh có `done` thì trả lại `done`; mỗi lệnh một kết quả dict."""
```

| Việc | Làm | Vì sao |
|---|---|---|
| Chạy song song | `asyncio.gather` | 2–3 tool (bảng số + RAG) chạy tuần tự sẽ cộng dồn độ trễ |
| Dùng lại `done` | Lệnh có `done` → trả `done`, không gọi tool | `pending.done` (anh chốt): tránh chạy lại T7, tốn embedding |
| Kiểm tham số | `*Input.model_validate(args)` trước khi gọi | `merge_context` / `merge_pick` sinh dict; kiểm lại để lỗi tham số thành `INVALID_REQUEST` rõ ràng, không thành lỗi lạ trong tool |
| Thời gian chờ | `asyncio.wait_for`, mỗi tool **10 giây** (Q6) | Một tool treo không được làm treo cả lượt |
| Bắt lỗi | `psycopg.Error` → `DATABASE_ERROR`; lỗi OpenAI (embedding của T7) → `LLM_ERROR`; timeout và lỗi khác → `INTERNAL_ERROR`. Ghi log đầy đủ | PRD 24. Người dùng chỉ thấy câu xin lỗi, không thấy chi tiết kỹ thuật |
| Kết quả lỗi | `{"status": "error", "error_code": ...}` (dict, không đổi `ToolResult`) | Không sửa schema 7 tool đã có test |
| Bảng tool truyền vào được | Tham số `tools=` | Test dùng tool giả, không cần DB |

---

## 6. Câu mẫu song ngữ (`templates.py`) — **cần anh duyệt câu chữ**

Chọn bản theo `language` của lượt. Ngôn ngữ khác Việt–Anh: in cả hai bản. Khi Router không chạy (đường tắt `pick_choice`), dùng ngôn ngữ của lượt trước (Q4).

### 6.1 Từ chối, huỷ, hỏi lại

| Mã | Tiếng Việt | Tiếng Anh |
|---|---|---|
| `other_university` | Mình chỉ hỗ trợ thông tin của Đại học Bách khoa Hà Nội (HUST), không có dữ liệu về trường khác. Bạn có thể hỏi về HUST, ví dụ: "Điểm chuẩn ngành Khoa học máy tính năm 2025?" | I can only help with Hanoi University of Science and Technology (HUST) and have no data on other universities. You could ask, for example: "What was the 2025 cut-off score for Computer Science?" |
| `off_topic` | Mình là trợ lý tra cứu tuyển sinh và học vụ của HUST nên không hỗ trợ được nội dung này. Bạn có thể hỏi về điểm chuẩn, học phí, ngành học, quy chế, học bổng… | I'm HUST's admissions and academic-affairs assistant, so I can't help with that. You can ask about cut-off scores, tuition, programs, regulations, scholarships… |
| `other_language` (in cả hai) | Mình hỗ trợ tiếng Việt và tiếng Anh. Bạn vui lòng hỏi lại bằng một trong hai ngôn ngữ này. | I support Vietnamese and English. Please ask again in one of these languages. |
| `missing_info` | Bạn muốn hỏi về {missing_info} nào? Ví dụ: "Điểm chuẩn ngành IT1 năm 2025?" | Which {missing_info} do you mean? For example: "What was the 2025 cut-off score for IT1?" |
| `ambiguous` | "{mention}" có thể là một trong các {kind} sau, bạn muốn hỏi cái nào?<br>1. TE1 – Kỹ thuật Ô tô<br>2. TE-E2 – Kỹ thuật Ô tô (CT tiên tiến)<br>Bạn có thể bấm chọn, gõ mã hoặc số thứ tự. | "{mention}" could be one of the following {kind}. Which one do you mean? (list) You can click, type the code or the number. |
| `too_many_choices` | Mình tra được tối đa 3 {kind} mỗi lần. Bạn chọn giúp tối đa 3 trong danh sách: (list) | I can look up at most 3 {kind} at a time. Please pick up to 3: (list) |
| `unclear` (lần 1) | Mình chưa rõ bạn chọn cái nào. Bạn bấm chọn, gõ mã (TE1 / TE-E2) hoặc số thứ tự nhé. (list) | I'm not sure which one you mean. Please click, type the code (TE1 / TE-E2) or the number. (list) |
| `released` (lần 2) | Mình bỏ câu hỏi về "{mention}" để không chọn nhầm. Bạn có thể hỏi lại kèm mã, ví dụ "Điểm TE-E2 năm 2025", hoặc hỏi câu khác. | I've dropped the question about "{mention}" to avoid picking the wrong one. You can ask again with a code, e.g. "TE-E2 cut-off score 2025", or ask something else. |
| `cancel` | Bạn còn cần giải đáp thắc mắc nào nữa không? | Is there anything else you'd like to ask? |
| `too_many` (tool `invalid`) | Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác (tối đa 3 ngành, 3 năm, 3 phương thức mỗi câu). | Please ask about fewer programs/years at a time (at most 3 programs, 3 years and 3 methods per question). |

`{kind}` lấy theo `entity_type`: ngành / Trường-Khoa / khoá / mục đích / chứng chỉ (program / school-faculty / cohort / purpose / certificate). Danh sách lựa chọn dựng từ `candidates`, **không** do LLM viết.

**Vì sao câu mẫu cho trường khác có gợi ý câu hỏi:** ghi chú anh duyệt ở R122. Người dùng hỏi so sánh với trường khác vẫn đi tiếp được với HUST.

### 6.2 Không có dữ liệu, thông báo, lỗi

| Mã | Tiếng Việt | Tiếng Anh |
|---|---|---|
| `not_found` | Mình chưa có dữ liệu về {missing}. {available} Bạn có thể kiểm tra tại trang tuyển sinh chính thức: https://ts.hust.edu.vn | I don't have data on {missing}. {available} You can check the official admissions site: https://ts.hust.edu.vn |
| `low_confidence` | Mình không tìm thấy thông tin đủ tin cậy trong nguồn dữ liệu hiện tại để trả lời câu này. Bạn có thể kiểm tra tại nguồn chính thức của HUST: https://ts.hust.edu.vn | I couldn't find reliable enough information in my current sources to answer this. Please check HUST's official sources: https://ts.hust.edu.vn |
| `announcement` | Thông báo và tin tức của {faculty} thay đổi thường xuyên nên mình chưa tra trực tiếp được. Bạn xem tại kênh chính thức: {url} | {faculty}'s announcements change frequently, so I can't look them up directly yet. Please see the official channel: {url} |
| `database_error` / `internal_error` | Xin lỗi, hệ thống đang gặp sự cố khi tra dữ liệu. Bạn vui lòng thử lại sau ít phút. | Sorry, the system ran into a problem while looking up data. Please try again in a few minutes. |
| `llm_error` | Xin lỗi, mình đang không xử lý được câu hỏi lúc này. Bạn vui lòng thử lại sau ít phút. | Sorry, I can't process your question right now. Please try again in a few minutes. |
| `no_tool` | Mình chưa xác định được bạn cần tra thông tin gì. Bạn thử hỏi cụ thể hơn, ví dụ kèm tên ngành hoặc năm. | I couldn't tell what information you need. Please try a more specific question, e.g. with a program name or year. |

`{missing}` và `{available}` dựng từ `ToolResult.missing` (`what`, `available_years`), ví dụ: "chỉ tiêu năm 2024" / "Hiện có dữ liệu năm 2025, 2026."
**Vì sao:** PRD 13.2: "nói rõ thiếu cái gì và có sẵn cái gì", không trả lời cụt.

**Vì sao link `https://ts.hust.edu.vn`:** đây là trang tuyển sinh chính thức đã dùng làm nguồn cho nhiều bảng trong dataset. Anh kiểm giúp có muốn dùng link khác cho câu hỏi về quy chế/học vụ (ví dụ `ctt.hust.edu.vn`) không (Q2).

---

## 7. Nhánh `answer` tạm thời (trước khi có Synthesizer)

Đề xuất: `answer` = **bản nháp có cấu trúc từ dữ liệu thô**, mỗi tool một khối JSON gọn (bỏ trường rỗng), cộng danh sách nguồn từ `sources`, cộng phần "thiếu" từ `missing`. Gắn cờ `draft = True` trong `turn`.

**Vì sao:** bước này cần chứng minh **luồng** đúng (đúng tool, đúng tham số, đúng ngữ cảnh), không cần câu văn hay. Viết lời văn bằng template cho 7 loại dữ liệu là việc tốn công mà bước 3 sẽ thay hết. Bước 3 thay node `answer` bằng `generate` → `verify` → `template_answer` như sơ đồ gốc; các node khác không đổi.

---

## 8. Lịch sử đưa vào Router

- Giữ **3 lượt** (`MAX_HISTORY_TURNS`, anh đã chốt Q8 plan Tuần 4).
- **Cắt mỗi câu trả lời của bot còn 500 ký tự** khi lưu vào `messages` (Q3); câu hỏi người dùng giữ nguyên (cắt 1.000 ký tự để phòng dán văn bản dài).
  **Vì sao:** Router chỉ cần biết lượt trước nói chủ đề gì; bảng điểm 3 ngành × 3 năm hay đoạn trích quy chế dài làm phình prompt (đã có khoảng 10.300 token cố định) mà không giúp phân loại. Bản đầy đủ vẫn nằm trong `turn.answer` trả cho API.
- Câu mẫu hỏi lại vẫn vào lịch sử, kèm danh sách lựa chọn.
  **Vì sao:** Router cần thấy bot vừa hỏi gì để hiểu câu trả lời.

---

## 9. Thay đổi nhỏ ở code đã có

| Chỗ | Thay đổi | Vì sao |
|---|---|---|
| `ConvContext` | Thêm `last_language` | Đường tắt `pick_choice` không gọi Router nên không biết ngôn ngữ; dùng ngôn ngữ của lượt trước để chọn câu mẫu (Q4) |
| `Turn` | Thêm `language`, `outcome`, `clarification` (mention + danh sách lựa chọn cho nút bấm), `pending_new`, `draft` | Cầu nối giữa node trả lời và `save_context`; API Tuần 5 cần `clarification` để hiện nút |
| `update_context` | Nhận thêm `kind="released"` (giống `cancel`) và ghi `last_language` | Bảng `outcome` mục 3 |
| `ToolContext` | Không đổi | — |

Mọi thay đổi chạy lại test cũ (399) phải vẫn xanh.

---

## 10. Cần anh quyết

**Đã chốt 2026-10-19:** anh duyệt cả 6 câu theo đề xuất (Q1 = A; câu mẫu mục 6 như viết, câu `cancel` đã sửa; chỉ link `ts.hust.edu.vn`; cắt 500 ký tự; `last_language`; nhánh trả lời tạm là JSON gọn; chờ 10 giây/tool). Thêm:
- **Hỏi quá 3 ngành:** tạm bỏ qua; Router tự lấy 3 ngành cũng chấp nhận được (không sửa prompt Router).
- **`invalid` không phải "quá 3"** (thiếu đầu vào, tham số ngoài khoảng, nhóm ngành vào tool một ngành, khoá lạ): dùng câu `no_tool`, **không** hiện `message` của tool. **Vì sao:** các `message` đó là câu kỹ thuật, chỉ có tiếng Việt ("top_k phải từ 1 đến 10", "dùng list_programs"); PRD 24 cấm lộ chi tiết kỹ thuật. Chưa sửa 7 tool để phân loại kỹ hơn (đề xuất trong trao đổi 2026-10-19, chưa chốt).

1. **Tool trả `invalid` (quá 3 thực thể) trong lượt có tool khác thành công:** (A, đề xuất) từ chối cả lượt bằng câu mẫu `too_many`; (B) trả lời phần thành công, kèm câu nhắc phần bị bỏ. **Vì sao đề xuất A:** người hỏi 4 ngành mà nhận câu trả lời cho các tool khác dễ tưởng đã được trả lời đủ; câu mẫu bảo hỏi lại từng phần thì rõ ràng hơn.
2. **Duyệt câu chữ mục 6** (vi + en), và link dùng trong câu "không có dữ liệu": chỉ `https://ts.hust.edu.vn` (đề xuất), hay tách link riêng cho câu hỏi quy chế/học vụ.
3. **Cắt câu trả lời cũ còn 500 ký tự** khi đưa vào Router (mục 8): đồng ý không?
4. **Câu mẫu ở đường tắt dùng ngôn ngữ lượt trước** (`last_language`, mục 9): đồng ý không?
5. **Nhánh `answer` tạm = JSON gọn từ dữ liệu thô** (mục 7): đồng ý không?
6. **Thời gian chờ mỗi tool 10 giây** (mục 5): đồng ý không? T7 gồm một lần gọi embedding OpenAI và một lần Qdrant; chưa có số đo thời gian chạy tool nào, nên 10 giây là mức rộng tay để không cắt nhầm. Bước 8 (chạy đầu-cuối) sẽ đo thật rồi chỉnh.

---

## 11. Thứ tự làm và cách kiểm

| Bước | Việc | Xong khi |
|---|---|---|
| G1 | `templates.py` + test (mọi mã có đủ vi/en; dựng danh sách lựa chọn; `{missing}`/`{available}`) | Test xanh |
| G2 | `dispatch.py` + test với tool giả (song song, dùng lại `done`, timeout, 3 loại lỗi, tham số sai) | Test xanh |
| G3 | Thay đổi nhỏ mục 9 | 399 test cũ vẫn xanh |
| G4 | `nodes.py` + `build.py` (StateGraph, `InMemorySaver`, Router và tool tiêm vào được) | Graph dựng được; vẽ được sơ đồ bằng `get_graph()` để đối chiếu mục 2 |
| G5 | `test_graph_flow.py`: mỗi nhánh mục 2 và mục 4 + hội thoại nhiều lượt qua **cả graph**: M1, M2, M4, M5, M6, M10, M15, M20, M22, M25, M27, M28, M29–M30, thông báo, độ tin cậy thấp, lỗi DB, lỗi Router, ngôn ngữ khác, câu tiếng Anh, hai `thread_id` không lẫn ngữ cảnh | Toàn bộ test xanh, **không gọi OpenAI** |
| G6 | Cập nhật `sodothietke.md` (sơ đồ, bảng node) và plan Tuần 4 | — |

**Chi phí API của cả bước: 0.** Nếu sau G5 anh muốn thử graph với Router thật trên vài câu, tôi sẽ báo số câu và chi phí ước tính trước, chờ anh đồng ý.

---

## 12. Đã thực hiện (2026-10-19)

| Bước | Kết quả |
|---|---|
| G1 | `backend/app/graph/templates.py`: 17 câu mẫu, đủ vi + en; danh sách lựa chọn và phần "thiếu / có sẵn" dựng bằng code |
| G2 | `backend/app/graph/dispatch.py`: chạy song song, dùng lại `done`, kiểm tham số, chờ tối đa 10 giây, lỗi → `DATABASE_ERROR` / `LLM_ERROR` / `INTERNAL_ERROR` |
| G3 | `state.py`: `last_language`, `Pending.intent`, các trường `Turn` mới, cắt lịch sử (bot 500 / người dùng 1.000 ký tự); `update_context` nhận `released` |
| G4 | `nodes.py` (11 node, phụ thuộc tiêm qua `GraphDeps`) + `build.py` (`build_graph`, `chat`). Sơ đồ LangGraph tự vẽ khớp mục 2 |
| G5 | `tests/test_graph_parts.py` (14 test) + `tests/test_graph_flow.py` (32 test, hội thoại chạy qua cả graph: M1, M2, M4, M5, M6, M10, M15, M20, M22, M25, M27, M28, M29–M30, thông báo, độ tin cậy thấp, không có dữ liệu, quá 3, `invalid` khác, lỗi DB, lỗi Router, ngôn ngữ khác, tiếng Anh, hai thread). Toàn bộ **445 passed**, không gọi OpenAI |
| G6 | `sodothietke.md` mục 0 (graph theo code); plan Tuần 4 |

**Khác plan:**
- Không có node riêng cho `register_unclear`: node `router` gọi luôn khi `pick_status = unclear`, rồi rẽ sang `clarification` (lần 1) hoặc `fallback` (lần 2). **Vì sao:** chỉ một lệnh gọi hàm, tách node không thêm gì.
- `invalid` không phải "quá 3": dùng câu `no_tool`, không hiện `message` kỹ thuật của tool (mục 10).

**Chưa làm (đúng phạm vi):** Synthesizer và kiểm số (bước 3), checkpointer Postgres (bước 4), API (bước 6), Langfuse (bước 7). Graph chưa chạy với Router thật và tool thật; muốn thử thì tôi báo số câu và chi phí trước.

