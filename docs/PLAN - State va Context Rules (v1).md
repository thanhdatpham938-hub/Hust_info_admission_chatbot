# PLAN — State và quy tắc ngữ cảnh nhiều lượt (v1)

**Ngày:** 2026-10-12 · **Trạng thái:** đề xuất, chờ anh duyệt mục 8 · Thuộc bước 2 của `PLAN - Tuan 4 LangGraph (v1).md` mục 9 · Gắn với PRD mục 10.3, 14, 21 (AC6, AC8) và sơ đồ `docs/ghi_chu/sodothietke.md` mục 3–4

Mỗi quyết định có dòng **Vì sao**. Tôi chỉ code sau khi anh duyệt.

**Phạm vi:** hai file thuần Python, **không LLM, không DB, không mạng**:

```text
backend/app/graph/state.py            ChatState, ConvContext, Turn, Pending, hàm dựng state rỗng
backend/app/graph/context_rules.py    pick_choice(), merge_context(), update_context()
backend/tests/test_graph_context.py   test từng quy tắc C1–C5 và các ca M1–M10
```

**Vì sao tách riêng và không đụng LLM:** AC6 là phép đo "hội thoại có đúng không", mà quy tắc PRD 14 là quy tắc cứng. Hàm thuần thì test được bằng dict vào dict ra, chạy trong vài mili giây, không tốn tiền, và khi AC6 trượt thì biết ngay lỗi nằm ở quy tắc chứ không phải ở LLM. Đây cũng là phần anh không phải chờ OpenAI key để kiểm.

---

## 1. Dữ liệu thật mà quy tắc phải khớp (đã đọc code, 2026-10-12)

Bảy tool đều có chữ ký `async fn(inp, ctx) -> ToolResult` nhưng **đặt tên tham số không giống nhau**:

| Tool | Ngành | Năm | Phương thức | Trường/Khoa | Khoá | Khác |
|---|---|---|---|---|---|---|
| T1 `admission_scores` | `programs` | `years` | `methods` | — | — | |
| T2 `list_programs` | `programs`, `program_group` | `years` | `method` (1 giá trị) | `faculty` (1 giá trị) | — | `metric`, `combination`… |
| T3 `program_info` | `programs` | `years` | — | — | — | `fields` |
| T4 `tuition_fees` | `programs`, `program_group` | `years` | — | — | — | `kinds` |
| T5 `certificate_lookup` | `programs` | **`year`** (1 giá trị) | — | — | `cohort` | `certificate`, `value`, `purpose` |
| T6 `university_info` | `programs` | **`year`** (1 giá trị) | — | `faculties` | — | `fields` |
| T7 `rag_search` | `programs` | `years` | — | `faculties` | `cohort` | `query`, `document_types` |

Và `ToolResult.clarifications[].candidates[]` có `entity_type` là `program`, `program_group`, `cohort` hay `purpose`; mã khoá là `K71+` / `K70-` (đã kiểm: `cohort_number("K71+")` ra 71, tool nhận được).

**Hệ quả thiết kế:** ngữ cảnh phải lưu theo **khái niệm** (ngành, năm, phương thức, Trường, khoá), không lưu theo tên tham số của một tool. Khi điền vào lệnh gọi, một bảng ánh xạ khái niệm → tên tham số theo từng tool (mục 4.1) lo phần khác nhau đó.
**Vì sao:** nếu lưu thẳng `args` của tool trước thì "Thế còn 2025?" sau T5 (`year`, một giá trị) sang T1 (`years`, danh sách) phải viết 7×7 trường hợp. Lưu theo khái niệm thì mỗi tool chỉ cần một dòng trong bảng.

---

## 2. State

```python
class Pending(TypedDict):
    calls: list[dict]          # TOÀN BỘ lệnh gọi của lượt đã hỏi lại: {"tool", "args", "done"}
    mention: str               # cụm người dùng gõ gây mơ hồ: "kỹ thuật ô tô"
    field: str                 # tham số cần thay: "programs" | "faculties" | "cohort" | "purpose"
    entity_type: str           # program | program_group | faculty | cohort | purpose
    candidates: list[dict]     # {"code", "name"}; đủ danh sách hay cắt 3 do tool quyết
    index: int                 # lệnh gọi nào trong `calls` đã hỏi lại. Thêm khi code: T5 hỏi khoá/mục đích bằng
                               # cụm tự đặt ("khoá học"), không nằm trong tham số, nên phải biết gán mã vào lệnh nào
    retries: int               # số lần LIÊN TIẾP Router xếp `unclear` (4.3c); đến 2 thì thả pending

class ConvContext(TypedDict, total=False):
    programs: list[str]        # mã ĐÃ xác nhận, tối đa 3
    years: list[int]           # tối đa 3
    methods: list[str]         # tối đa 3
    faculties: list[str]       # tối đa 3
    cohort: str | None
    last_tool: str | None      # tool "chính" của lượt trước
    last_intent: str | None    # intent cuối cùng (có thể là CLARIFICATION_NEEDED)
    pending: Pending | None

class Turn(TypedDict, total=False):   # sống một lượt, start_turn ghi đè bằng dict mới
    ...                               # như sodothietke.md mục 4
```

Quyết định:

1. **Ngữ cảnh chỉ chứa mã đã xác nhận, lấy từ `ToolResult.resolved`, không lấy từ chữ Router chép.**
   **Vì sao:** PRD 14 dòng 3: khi đang CLARIFICATION_NEEDED, state không được coi là đã xác nhận. Tool trả `ambiguous` thì `resolved` rỗng cho cụm đó, nên quy tắc này **tự đúng** mà không cần `if` riêng. Lưu chữ người dùng gõ thì lượt sau "ngành này" sẽ đi phân giải lại một cụm đã từng mơ hồ.

2. **`years`/`methods` lưu theo giá trị người dùng nêu hoặc tool đã dùng, không lưu "năm mới nhất" do tool tự chọn.**
   **Vì sao:** người dùng hỏi "Điểm IT1?" (không nêu năm) và tool tự lấy 2026. Nếu lưu 2026 thì lượt sau "Học phí ngành này?" bị coi là đã chọn năm 2026 trong khi người dùng chưa từng nói. Chỉ lưu thứ họ **nói ra**.

3. **`pending` chỉ có một mục (cụm mơ hồ đầu tiên), nhưng giữ `calls` của cả lượt kèm kết quả đã có (`done`).**
   **Vì sao:**
   - Một lượt có thể có 2 cụm mơ hồ, nhưng hỏi hai câu một lúc làm người dùng rối, và `pick_choice` phải khớp trong một danh sách. Hỏi từng cụm: sau khi chọn xong, chạy lại lệnh gọi thì tool sẽ tự báo `ambiguous` tiếp cho cụm còn lại, nên không cần code riêng.
   - `done` giữ kết quả tool đã `ok`/`partial` của cùng lượt (anh chốt "giữ sẵn các kết quả sẵn có"). Chạy lại T7 là tốn thêm một lần embedding và Qdrant; kết quả của lệnh gọi đã xong không đổi trong cùng hội thoại.

4. **Không lưu `purpose`, `query`, `fields`, `metric` vào ngữ cảnh.**
   **Vì sao:** đó là phần câu hỏi, không phải thực thể. "Thế còn năm 2025?" sau câu hỏi chuẩn đầu ra không có nghĩa là hỏi lại chuẩn đầu ra của năm 2025. Mang cả `fields` thì "Học phí ngành này?" sau câu hỏi chỉ tiêu bị lọc nhầm phần.

5. **Chỉ lưu `programs` khi tool dùng **đã chạy tới truy vấn** (status `ok`/`partial`/`not_found`), không lưu khi `invalid`.**
   **Vì sao:** `invalid` là quá 3 thực thể hoặc đầu vào sai; chẳng có gì được xác nhận.

6. **Lượt từ chối (OTHER_UNIVERSITY, GENERAL_OFF_TOPIC, tiếng Anh, UNKNOWN) không đổi `context`.** (M10)
   **Vì sao:** người dùng hỏi "Điểm UET?" rồi quay lại "Thế còn năm 2025?" vẫn muốn nói tiếp chuyện IT1. Xoá ngữ cảnh khi từ chối là phạt người dùng vì một câu lạc đề.

---

## 3. Ba hàm và hợp đồng của chúng

```python
def pick_choice(text: str, pending: Pending, choice: str | None = None) -> list[dict] | None:
    """Đường tắt không LLM (4.3, 4.3b). Trả lệnh gọi đã thay mã (giữ `done`) khi: `choice` hợp lệ,
    hoặc khớp chữ đúng một lựa chọn VÀ không còn phần thừa. Mọi trường hợp khác → None (đi Router)."""

def merge_pick(pending: Pending, picked: list[str], router_calls: list[dict]) -> list[dict] | None:
    """Ghép khi Router xử lý câu chọn (4.3b): kiểm mọi mã trong `picked` ∈ candidates, ≤ 3 (sai → None = C5),
    khoá mã đã chọn, ghép C2/C3 với pending.calls làm lượt trước, giữ lệnh gọi gốc, ≤ 3, xét lại `done`."""

def merge_context(calls: list[dict], refers: bool, ctx: ConvContext) -> list[dict]:
    """Điền chỗ trống cho từng lệnh gọi theo C1–C3. Không bao giờ ghi đè giá trị câu hỏi đã nêu."""

def update_context(ctx: ConvContext, calls: list[dict], results: list[dict],
                   intent_final: str, route: str) -> ConvContext:
    """save_context: gom `resolved`, cập nhật last_tool/last_intent, đặt hoặc xoá pending."""
```

**Vì sao ba hàm thuần, trả giá trị mới thay vì sửa tại chỗ:** LangGraph ghi lại từng bước vào checkpoint; hàm không sửa đầu vào thì test so sánh được "trước/sau" và không có lỗi "sửa nhầm dict của lượt cũ".

---

## 4. Quy tắc

### 4.1 Bảng ánh xạ khái niệm → tham số

| Khái niệm | T1 | T2 | T3 | T4 | T5 | T6 | T7 |
|---|---|---|---|---|---|---|---|
| ngành | `programs` | `programs` | `programs` | `programs` | `programs` | `programs` | `programs` |
| năm | `years` | `years` | `years` | `years` | `year` ← phần tử đầu | `year` ← phần tử đầu | `years` |
| phương thức | `methods` | `method` ← phần tử đầu | — | — | — | — | — |
| Trường/Khoa | — | `faculty` ← phần tử đầu | — | — | — | `faculties` | `faculties` |
| khoá | — | — | — | — | `cohort` | — | `cohort` |

Ô "—" nghĩa là tool đó không có tham số ấy: **không điền**.
**Vì sao:** điền một tham số tool không có thì Pydantic `*Input` từ chối cả lệnh gọi, và đó là lỗi của code mình chứ không phải của người dùng.

Tool chỉ nhận một giá trị (T2 `method`/`faculty`, T5/T6 `year`) mà ngữ cảnh đang giữ nhiều giá trị (ví dụ `years=[2024, 2025]`): **không điền**, để tool tự xử lý như câu không nêu năm.
**Vì sao:** lấy phần tử đầu là đoán. Người đã so sánh 2024 với 2025 rồi hỏi "Học phí?" không có nghĩa là muốn năm 2024. Nên chỉ điền khi ngữ cảnh có đúng **một** giá trị.

### 4.2 C1–C5

| # | Điều kiện | Làm gì | Vì sao |
|---|---|---|---|
| C1 | `refers_to_context = false` | Không điền gì | PRD 14 dòng 1. Chặn việc mang ngành IT1 sang "Điều kiện cảnh báo học tập?" (M3) |
| C2 | Có tham chiếu **và cùng tool** với `last_tool` | Điền ngành, năm, phương thức, Trường, khoá vào **ô còn trống** | "Thế còn 2025?" (M1), "Thế còn TSA năm 2024?" (M9) |
| C3 | Có tham chiếu nhưng **khác tool** | Chỉ điền **ngành** và **Trường/Khoa** vào ô trống | PRD 14 dòng 2: chỉ mang thực thể, không mang năm/phương thức. M2: "Học phí ngành này?" sau điểm 2024 không mang 2024 |
| C4 | Có `pending` và `pick_choice` khớp | Chạy lại các lệnh gọi trong `pending.calls` với mã đã chọn, giữ `done` | PRD 14 dòng 3 |
| C5 | Có `pending` nhưng không khớp và Router coi là câu mới | Bỏ `pending`, xử lý như C1 | M6: người dùng đổi chủ đề giữa chừng |

Nguyên tắc chung của C2/C3: **chỉ điền ô trống, không ghi đè.**
**Vì sao:** câu mới "Thế còn IT2?" có `programs=[IT2]` nên IT1 trong ngữ cảnh bị bỏ qua, và vẫn mang năm 2024. Câu nêu rõ thứ gì thì thứ đó thắng, và số lượng không vượt 3 vì không bao giờ cộng dồn hai danh sách.

**Vì sao C2/C3 so theo tool chứ không theo intent:** ADMISSION_QUERY gồm cả điểm chuẩn lẫn học phí (bảng 3.2 của plan Tuần 4). Theo intent thì "Điểm IT1 2024" rồi "Học phí ngành này?" vẫn cùng intent nên mang năm 2024, và T4 sẽ tra học phí nhóm 2024 trong khi người hỏi gần như chắc đang hỏi học phí hiện tại.

**Một lượt có nhiều lệnh gọi:** `last_tool` là tool **đầu tiên** trong `calls` của lượt trước. Lệnh gọi nào của lượt mới cùng tool đó thì áp C2, còn lại áp C3.
**Vì sao:** thứ tự do Router chọn là tool "trả lời chính" (T1–T6 đứng trước T7 theo nguyên tắc tầng bảng số). Chọn một tool đại diện đơn giản và đoán được, hơn là so với cả tập.

### 4.3 `pick_choice` — thứ tự khớp

Chỉ chạy khi `pending` có. Duyệt theo thứ tự, **dừng ở bước đầu tiên cho đúng một kết quả**; nếu một bước cho nhiều kết quả thì trả `None` chứ không đi tiếp bước sau.

0. **Nút bấm** (chốt 2026-10-12): request có trường `choice` (mã lựa chọn, do nút ở giao diện Tuần 5 gửi) thì bỏ qua mọi bước khớp chữ; chỉ kiểm `choice` nằm trong `pending.candidates`, không nằm thì coi như không có `choice`.
   **Vì sao:** phần lớn người dùng sẽ bấm nút; nút gửi mã có cấu trúc thì đường tắt đúng gần như 100% mà không phải đoán chữ. Rasa CALM làm cùng cách (payload `/SetSlots(...)` của nút đi thẳng vào hệ thống, không qua LLM). Các bước khớp chữ dưới đây chỉ phục vụ người tự gõ.
1. **Mã.** So `compact()` của cụm 1–3 từ liên tiếp trong tin nhắn với `compact(code)`: "TE-E2", "te e2", "tee2" đều ra TE-E2. Dùng lại `normalize.py` của Entity Resolution. Gõ **nhiều mã** ("TE1 và TE-E2") thì lấy cả, tối đa 3, vì mã gõ đúng là ý rõ ràng (thêm khi code).
   **Vì sao:** một bản chuẩn hoá duy nhất cho cả bộ phân giải và bộ chọn, nên "ITE10" khớp ở cả hai chỗ.
2. **Khoá** (`entity_type = cohort`): lấy số bằng `cohort_number()` có sẵn rồi so: ≥ 71 → `K71+`, ngược lại → `K70-`. "khoá 69", "K70", "năm 2025" đều khớp.
   **Vì sao:** người dùng không gõ "K70-". Dùng lại `cohort_number` để cùng một cách hiểu "khoá 2026" với T5.
3. **"Cả hai" / "cả 2" / "cả ba" / "tất cả"** (chốt 2026-10-12): danh sách lựa chọn ≤ 3 → thay cụm mơ hồ bằng **toàn bộ** mã; > 3 → câu mẫu "Mình tra được tối đa 3 ngành mỗi lần, bạn chọn giúp tối đa 3" kèm danh sách, `pending` giữ, **không** tăng `retries`.
   **Vì sao:** người dùng muốn so sánh là nhu cầu hợp lệ, tool nhận tới 3 thực thể (PRD 10.2). Quá 3 thì không phải người dùng trả lời sai, nên không tính vào giới hạn hỏi lại.
4. **Số thứ tự**, chỉ khi tin nhắn ngắn (≤ 6 từ): "cái thứ hai", "số 2", "đầu tiên", "cái cuối", "2". Phải nằm trong 1…số lựa chọn, tính theo **thứ tự hiển thị** cho người dùng. Từ nào nằm trong **tên một lựa chọn** thì không tính là số thứ tự, và không có "nhất" đứng riêng.
   **Vì sao (phát hiện khi code):** "Việt **Nhật**" chứa "nhất" sau khi bỏ dấu; không chặn thì bị hiểu là "thứ nhất" và chọn nhầm lựa chọn số 1 trước khi tới bước 5a.
   **Vì sao giới hạn độ dài:** câu dài như "Học phí năm 2 là bao nhiêu?" có chữ "2" nhưng không phải chọn lựa chọn thứ hai.
5. **Tên/đặc điểm** (anh chốt cách C, 2026-10-12), hai lớp, mỗi lớp chỉ nhận khi ra **đúng một** lựa chọn:
   - **5a. Từ riêng tự sinh từ tên:** với mỗi lựa chọn, lấy các từ (sau `normalize()`) chỉ có trong tên của nó, không có trong tên lựa chọn khác. Tin nhắn chứa từ riêng của đúng một lựa chọn → chọn. Ví dụ: danh sách CNTT, "Việt Nhật" → IT-E6, "Global" → IT-E7; danh sách Cơ điện tử, "Nagaoka" → ME-NUT.
   - **5b. Nhóm chương trình:** 5a trượt thì tra bảng từ đồng nghĩa → `program_group_code` (cột có sẵn trong bảng `programs`: `chuan` / `elitech` / `pfiev` / `lien_ket`, không theo năm; nạp sẵn vào `ToolContext.program_group`. Bản đầu plan ghi `quotas_<năm>`, khi code thấy bảng `programs` đã có cột này nên dùng luôn):

     | Người dùng gõ | `program_group` |
     |---|---|
     | chuẩn, đại trà, thường | CHƯƠNG TRÌNH CHUẨN |
     | tiên tiến, Elitech | … ELITECH |
     | PFIEV, Việt Pháp | VIỆT - PHÁP (PFIEV) |
     | liên kết, hợp tác quốc tế | LIÊN KẾT ĐÀO TẠO QUỐC TẾ |

     Đúng một lựa chọn thuộc nhóm đó → chọn. Ví dụ: TE1/TE-E2 + "hệ chuẩn" → TE1; ME1/ME-E1/ME-LUH/ME-NUT + "Elitech" → 3 ngành cùng nhóm → `None`.

   **Vì sao cần 5b:** HUST đặt tên hệ chuẩn không có chữ nào phân biệt ("Kỹ thuật Ô tô" nằm trọn trong "Kỹ thuật Ô tô (CT tiên tiến)"), nên chỉ có 5a thì cả 7 cặp chuẩn/tiên tiến không chọn được hệ chuẩn bằng chữ.
   **Vì sao bảng trỏ vào nhóm, không trỏ vào mã:** cùng một từ trỏ mã khác nhau tuỳ danh sách ("tiên tiến" là TE-E2 với Ô tô, EE-E8 với Tự động hoá). Trỏ vào nhóm thì bảng chỉ 4 dòng và năm sau thêm ngành Elitech mới không phải sửa.
   **Vì sao không có "chất lượng cao":** alias "kỹ sư chất lượng cao" trỏ về 3 ngành PFIEV, trong khi tên nhóm ELITECH lại là "CHƯƠNG TRÌNH CHẤT LƯỢNG CAO - ELITECH". Đưa vào thì khớp nhầm nhóm.
   **Vì sao chỉ nhận khi duy nhất:** khớp trượt chỉ làm chậm (Router đoán hoặc hỏi lại), khớp nhầm thì trả dữ liệu ngành khác, đúng rủi ro PRD xếp mức **Cao**.
6. Không bước nào khớp → `None`, chuyển sang Router (mục 4.3b, 4.3c).

**Thay vào lệnh gọi:** `field = "programs"`/`"faculties"` thì thay **đúng phần tử bằng `mention`** bằng mã (giữ vị trí, giữ các phần tử khác); `field = "cohort"`/`"purpose"` thì gán giá trị.
**Vì sao thay đúng phần tử:** lệnh gọi `programs=["kỹ thuật ô tô", "IT2"]` chỉ có một cụm mơ hồ; thay cả danh sách là làm mất IT2.

### 4.3b Câu chọn kèm thông tin khác — "cách 3 gọn" (chốt 2026-10-12)

Người dùng hay vừa chọn vừa nói thêm: "TE-E2, năm 2024", "tiên tiến, so với IT1", "TE-E2, học phí bao nhiêu?". Quy tắc: **mỗi lượt chỉ một bên chọn ngành**: code khi tin nhắn chỉ có lựa chọn, Router khi có thêm bất kỳ gì.

```text
tin nhắn ──► pick_choice (code)
              ├─ có `choice` hợp lệ, hoặc khớp chữ và KHÔNG còn phần thừa ──► chạy lại pending.calls   (không LLM)
              └─ mọi trường hợp khác ─────► Router xử lý CẢ câu, kèm pending
                                              ├─ đọc `pick_status` (4.3c); chỉ `picked` mới đi tiếp xuống dưới
                                              ├─ kiểm mọi mã `picked` ∈ candidates, ≤ 3   (sai → C5, câu mới)
                                              ├─ thay cụm mơ hồ bằng mã đã chọn trong mọi lệnh gọi
                                              ├─ ghép: pending.calls làm "lượt trước" + C2/C3     (xung đột 2)
                                              ├─ giữ lệnh gọi gốc + lệnh gọi mới, tổng ≤ 3        (xung đột 3)
                                              └─ dùng lại `done` chỉ khi tham số giống hệt        (xung đột 4)
```

**"Còn phần thừa"** = sau khi bỏ phần đã khớp (mã, số thứ tự, từ đặc điểm) và từ đệm (`nhé`, `nha`, `ạ`, `ơi`, `cái`, `hệ`, `ngành`, `chương trình`, `chọn`, `lấy`, `đi`, `thôi`, `số`, `thứ`, `mình`, `em`, `tôi`, `và`, dấu câu) và các từ trong **tên của lựa chọn đã chọn**, tin nhắn còn ít nhất một từ.
**Vì sao chỉ tên lựa chọn đã chọn (phát hiện khi code):** "Khoa học máy tính với Việt Nhật" khớp IT-E6 ở bước 5a. Nếu coi chữ trong tên của **mọi** lựa chọn là đã dùng thì vế "khoa học máy tính" biến mất, bot chỉ chọn IT-E6. Chỉ trừ tên của lựa chọn đã chọn thì vế kia còn lại, và câu đi sang Router để chọn cả hai (P015).
**Vì sao từ đệm không cần đầy đủ:** thiếu một từ đệm thì chỉ đi nhầm sang Router (tốn 1 lần LLM), không ra sai dữ liệu.

**Router nhận cả tin nhắn**, không chỉ phần thừa, kèm danh sách lựa chọn và lệnh gọi đang chờ.
**Vì sao:** "năm 2024" hay "so với IT1" đứng riêng thì Router không biết đang nói về câu hỏi nào.

Bốn chỗ có thể xung đột và quy tắc cho từng chỗ:

| # | Xung đột | Quy tắc | Vì sao |
|---|---|---|---|
| 1 | Code và Router chọn khác nhau | Không xảy ra: có phần thừa thì code **không chọn**, Router chọn cả câu | Hai bên cùng chọn thì phải có luật ai thắng; một bên chọn thì khỏi cần |
| 2 | Tham số cũ (`years=[2025]`) và mới ("năm 2024") | Gọi lại `merge_context()` với `pending.calls` làm "lượt trước": cùng tool → giá trị vừa nói thắng, ô trống lấy từ lệnh cũ (C2); khác tool → chỉ mang ngành đã chọn (C3) | Không viết quy tắc mới. Router ở chế độ này làm đúng việc như mọi lượt: chỉ chép thứ người dùng vừa nói, không tự điền ngữ cảnh. Một hành vi Router, một bộ quy tắc ghép, một bộ test |
| 3 | Router chỉ trả lệnh gọi mới (T4 học phí), bỏ mất câu hỏi gốc (T1 điểm chuẩn) | **Luôn chạy lệnh gọi gốc** (đã ghép theo dòng 2) + lệnh gọi mới Router thêm, tổng tối đa 3 | Câu hỏi gốc chưa được trả lời; người dùng chỉ trả lời "ngành nào?", không nói "thôi khỏi". Muốn bỏ hẳn thì họ hỏi câu mới không kèm lựa chọn, đó là C5 |
| 4 | `pending.done` giữ kết quả cũ mà tham số vừa đổi | Chỉ dùng lại `done` khi dict tham số **giống hệt** sau khi ghép; khác thì chạy lại | Giữ kết quả là để tiết kiệm, không được đổi lấy câu trả lời sai năm |

Mã đã chọn **bị khoá**: không lệnh gọi nào được xoá hay thay nó. Router vẫn được **thêm** ngành người dùng vừa gõ ("so với IT1"); ngành thêm đi qua Entity Resolution trong tool như mọi cụm khác, mơ hồ thì tool vẫn hỏi lại.

Router xếp lượt này vào nhánh từ chối ("TE-E2, mà UET thì sao?") → từ chối như thường, `pending` **giữ nguyên** (lượt từ chối không đổi ngữ cảnh, mục 2 (6)).

**Vì sao không chọn "chỉ lấy lựa chọn" (đề xuất cũ):** "TE-E2, năm 2024" sẽ ra điểm 2025, "so với IT1" mất IT1, "học phí bao nhiêu?" ra điểm chuẩn: trả lời câu người dùng không hỏi và lặng lẽ bỏ ý của họ.
**Vì sao không đưa mọi tin nhắn cho Router (cách 2):** xung đột 2–4 vẫn còn, chỉ chuyển vào prompt cho LLM tự quyết mà không test được (mục 5 plan Tuần 4: để LLM tự điền thì sẽ có lúc mang nhầm năm). Thêm nữa, gõ đúng mã là cách trả lời phổ biến nhất mà vẫn tốn 1 lần LLM, và LLM phải tự chọn giữa hai tên gần như giống hệt ("Kỹ thuật Ô tô" / "Kỹ thuật Ô tô (CT tiên tiến)").
**Đối chiếu bên ngoài:** Rasa CALM dùng cùng mô hình: LLM đọc cả câu, xuất lệnh có cấu trúc (`SetSlot`, `Clarify`…), bộ quản lý tất định thực thi; có đường tắt `NLUCommandAdapter` bỏ qua LLM khi khớp chắc. Không dùng `interrupt()` của LangGraph vì nó giả định tin nhắn kế tiếp **là** câu trả lời (C5 vẫn phải tự định tuyến) và chạy lại cả node khi tiếp tục.

### 4.3c Phân loại tin nhắn khi đang chờ chọn (chốt 2026-10-12)

Khi có `pending` và tin nhắn đi qua Router, Router trả thêm `pick_status` (và `picked: list[str]` khi chọn):

| `pick_status` | Ví dụ (bot vừa hỏi TE1 hay TE-E2) | Xử lý | Tăng `retries`? |
|---|---|---|---|
| `picked` | "cái tiên tiến, năm 2024"; "cả hai năm 2024" | `merge_pick` như 4.3b | Không (đặt về 0) |
| `new_question` | "Học phí IT1 bao nhiêu?", "Thôi kệ, điều kiện học bổng là gì?" | C5: bỏ `pending`, trả lời câu mới như bình thường | Không |
| `cancel` | "thôi", "không cần nữa", "bỏ qua" | bỏ `pending`, câu mẫu "Đã bỏ câu hỏi trước. Bạn muốn hỏi gì?" | Không |
| `unclear` | "cái kia", "ừ", "không biết", "cái nào cũng được" | `retries = 1`: hỏi lại, kèm cách chọn (bấm nút, gõ mã, gõ số thứ tự). `retries = 2`: **thả** `pending`, câu mẫu "Mình bỏ câu hỏi về <cụm> để không chọn nhầm. Bạn có thể hỏi lại kèm mã, ví dụ 'Điểm TE-E2 năm 2025', hoặc hỏi câu khác." | Có |

- **Đổi chủ đề không bao giờ bị chặn:** đó là `new_question`, xử lý ngay ở bất kỳ lần hỏi lại nào.
- **Giới hạn chỉ đếm `unclear` liên tiếp.** Đến giới hạn thì thả hẳn, không hỏi lần thứ ba.
  **Vì sao thả thay vì hỏi tiếp:** hỏi lần ba vẫn là vòng lặp, chỉ đổi lời; thả thì người dùng không bị kẹt mà bot cũng không chọn bừa. Dialogflow CX cũng chuyển sang handler mặc định sau các lần hỏi lại đánh số; Genesys cảnh báo không giới hạn thì lặp vô tận.
- **Lượt từ chối khi đang chờ** ("TE-E2, mà UET thì sao?"): `pending` giữ, `retries` **không** tăng; người dùng không trả lời sai câu hỏi đang chờ.
- **Đường tắt của code** (nút bấm, gõ đúng mã không kèm gì) không qua Router nên không đụng `retries`.
- `pick_status` chỉ có nghĩa khi đang có `pending`; không có `pending` thì code bỏ qua trường này.

**Vì sao cần trường riêng, không suy từ `picked = None`:** "hỏi câu khác" và "trả lời không rõ" đều không có `picked`, nhưng một bên phải trả lời ngay, một bên phải hỏi lại. Suy từ tổ hợp intent/calls thì dễ lệch và không đo được; có trường riêng thì đo được bằng `router_pick_cases.csv`. Rasa CALM tách cùng cách bằng các lệnh `StartFlow` / `CancelFlow` / `Clarify`.

**Router đoán sai thì sao:** câu mới bị xếp `unclear` → bị hỏi lại thêm tối đa 1 lần rồi thả; trả lời không rõ bị xếp `new_question` → trả lời lạc hoặc fallback; `picked` ngoài danh sách → code chặn. Không trường hợp nào trả số liệu của ngành người dùng không chọn.

### 4.4 `update_context`

| Tình huống lượt vừa xong | `programs/years/methods/faculties/cohort` | `last_tool` / `last_intent` | `pending` |
|---|---|---|---|
| Trả lời có dữ liệu (`ok`/`partial`/`not_found`) | Ghi đè từng ô bằng giá trị lượt này đã **nêu hoặc xác nhận**; ô lượt này không đề cập thì **giữ** | cập nhật | xoá |
| Hỏi lại (`ambiguous`) | Giữ nguyên, **không** ghi cụm mơ hồ | `last_intent = CLARIFICATION_NEEDED`; `last_tool` giữ như cũ | ghi mới |
| Từ chối, thông báo `invalid`, lỗi hệ thống | Giữ nguyên | giữ nguyên | giữ nguyên |
| Câu mới trong khi đang `pending` (C5) | theo hàng "trả lời" | cập nhật | xoá |

**Vì sao ô không nhắc thì giữ:** "Điểm IT1 2024?" rồi "Chỉ tiêu ngành IT2?" (C3, không mang năm): lượt này không nêu năm nên `years` giữ 2024. Nếu xoá thì "Thế còn 2025?" ngay sau đó mất luôn chủ đề IT1/IT2 đang bàn. Một ô ngữ cảnh chỉ đổi khi lượt này có giá trị mới cho đúng ô đó; đổi ngành không làm mất năm, vì người dùng thường muốn so cùng một năm.

**Vì sao `last_tool` giữ nguyên khi hỏi lại:** lượt hỏi lại chưa trả lời gì. Sau khi người dùng chọn, lượt chạy lại dùng đúng `pending.calls` nên không cần so `last_tool`; còn nếu họ bỏ đi hỏi chuyện khác thì C3 so với tool của lượt đã trả lời gần nhất.

---

## 5. Bảng ca kiểm (từ mục 8.2 plan Tuần 4, thêm ca biên)

| # | Ngữ cảnh trước | Lượt mới (đầu ra Router giả) | Kỳ vọng | Quy tắc |
|---|---|---|---|---|
| M1 | T1, IT1, [2024] | T1 `programs=[]`, `years=[2025]`, refers | `programs=[IT1]` được điền, năm 2025 giữ | C2 |
| M2 | T1, IT1, [2024] | T4 `programs=[]`, refers | `programs=[IT1]`, `years=[]` | C3 |
| M3 | T1, IT1, [2024] | T7 `query=...`, refers = false | không điền gì | C1 |
| M4 | pending TE1/TE-E2, T1 `years=[2025]` | "TE-E2" | T1 `programs=[TE-E2]`, `years=[2025]` | C4 |
| M5 | như M4 | "cái thứ hai" | như M4 | C4 |
| M6 | như M4 | "Học phí IT1 bao nhiêu?" | `pending` bị bỏ, T4 `[IT1]` | C5 |
| M7 | pending cohort `K71+`/`K70-` | "K70" | T5 `cohort="K70-"` | C4 |
| M8 | T6 `faculties=[SoICT]` | T6 `fields=[channel]`, refers | `faculties=[SoICT]` | C3 |
| M9 | T1 `[IT1, IT2]`, [2025] | T1 `years=[2024]`, `methods=[TSA]`, refers | `programs=[IT1, IT2]` | C2 |
| M10 | T1 IT1, rồi lượt từ chối | "Thế còn 2025?" | `programs=[IT1]` vẫn còn | mục 2 (6) |
| M11 | T1 IT1 | T1 `programs=[IT2]`, refers | `programs=[IT2]` (không ghi đè), năm giữ | "chỉ điền ô trống" |
| M12 | T1, `years=[2024, 2025]` | T5 `year` rỗng, refers | không điền `year` (nhiều giá trị) | mục 4.1 |
| M13 | pending TE1/TE-E2 | "ô tô" | `None`, không đoán | 4.3 bước 5 |
| M14 | pending TE1/TE-E2 | "Học phí năm 2 là bao nhiêu?" | `None` (câu dài, không phải thứ tự) | 4.3 bước 4 |
| M15 | `pending.done` có kết quả T7 | "TE-E2" | `done` của T7 giữ nguyên, chỉ T1 chạy lại | mục 2 (3) |
| M16 | pending 2 cụm mơ hồ | chọn cụm đầu | lượt chạy lại báo `ambiguous` cụm còn lại, `pending` mới | mục 2 (3) |
| M17 | như M4 | `choice="TE-E2"` (nút bấm), tin nhắn bất kỳ | như M4, không khớp chữ | 4.3 bước 0 |
| M18 | như M4 | `choice="IT1"` (không có trong danh sách) | bỏ `choice`, xét tin nhắn như thường | 4.3 bước 0 |
| M19 | như M4 | "TE-E2 nhé" | đường tắt (chỉ còn từ đệm) | 4.3b |
| M20 | như M4 | "TE-E2, năm 2024" → Router giả: `picked=TE-E2`, T1 `years=[2024]` | T1 `[TE-E2]`, `[2024]` | 4.3b xung đột 2 |
| M21 | như M4 | "tiên tiến, so với IT1" → Router giả: `picked=TE-E2`, T1 `programs=[IT1]` | T1 `[TE-E2, IT1]`, `[2025]` | 4.3b xung đột 2, mã bị khoá |
| M22 | như M4 | "TE-E2, học phí bao nhiêu?" → Router giả: `picked=TE-E2`, chỉ T4 | T1 `[TE-E2]`, `[2025]` **và** T4 `[TE-E2]` | 4.3b xung đột 3 |
| M23 | như M4 + `done` T7 lọc `years=[2025]` | như M20 | T7 chạy lại (năm đổi); ở M19 thì T7 dùng lại `done` | 4.3b xung đột 4 |
| M24 | như M4 | Router giả: `picked=IT1` (không có trong danh sách) | `None` → câu mới, bỏ `pending` | 4.3b, C5 |
| M25 | như M4 | Router giả: intent `OTHER_UNIVERSITY` | từ chối, `pending` giữ nguyên, `retries` không tăng | 4.3b, 4.3c |
| M26 | như M4 | "cả hai" | T1 `[TE1, TE-E2]`, `[2025]` | 4.3 bước 3 |
| M27 | pending 7 ngành "BK CNTT" | "tất cả" | câu mẫu chọn tối đa 3, `pending` giữ, `retries` = 0 | 4.3 bước 3 |
| M28 | như M4 | Router giả: `pick_status=cancel` | bỏ `pending`, câu mẫu hỏi muốn hỏi gì | 4.3c |
| M29 | như M4 | Router giả: `unclear` | hỏi lại, `retries` = 1 | 4.3c |
| M30 | như M29 (`retries` = 1) | Router giả: `unclear` | thả `pending`, câu mẫu hướng dẫn hỏi kèm mã | 4.3c |
| M31 | như M29 (`retries` = 1) | Router giả: `new_question`, T4 `[IT1]` | bỏ `pending`, trả lời học phí IT1 | 4.3c, C5 |
| M32 | như M4 | Router giả: `picked=[TE1, TE-E2]`, T1 `years=[2024]` ("cả hai năm 2024") | T1 `[TE1, TE-E2]`, `[2024]` | 4.3b, 4.3c |

---

## 6. Phần chưa làm ở bước này (cố ý)

- **Router thật và `pick_status` / `picked`**: bước 3 (prompt + đo bằng `router_pick_cases.csv`). Ở đây Router được giả bằng dict định sẵn.
- **Kiểm số `verify`**: anh gửi ghi chú về lỗ hổng R159 (số trong câu hỏi qua được bước kiểm số). Đó là `guardrails/numbers.py`, bước 3 của plan Tuần 4; tôi sẽ sửa mục 6.3 của plan khi tới đó: số lấy từ câu hỏi chỉ được chấp nhận khi không mâu thuẫn với số tool trả cho cùng ngành và năm.
- **Checkpointer Postgres**: bước 4. State ở đây là dict thuần nên chạy được với `InMemorySaver` ngay.

---

## 7. Thứ tự làm và cách kiểm

| Bước | Việc | Xong khi |
|---|---|---|
| 2a | `state.py` + hàm dựng state rỗng + `Pending` | import được, có test dựng state rỗng |
| 2b | `merge_context()` + bảng ánh xạ 4.1 | M1, M2, M3, M8, M9, M11, M12 pass |
| 2c | `pick_choice()` + `merge_pick()` | M4, M5, M7, M13, M14, M17–M24, M26, M27, M32 pass |
| 2d | `update_context()` + xử lý `pick_status` | M6, M10, M15, M16, M25, M28–M31 pass |
| 2e | Chạy cả bộ `pytest backend` | 281 cũ vẫn pass, thêm ca mới pass, không cần DB cho `test_graph_context.py` |

---

## 8. Cần anh quyết

1. ~~**Chọn lựa chọn bằng tên/đặc điểm (4.3 bước 5)** dùng danh sách từ khoá nào?~~ **Đã chốt 2026-10-12: cách C** (từ riêng tự sinh + bảng 4 dòng trỏ vào `program_group`), xem 4.3 bước 5.
2. ~~**Câu chọn kèm thông tin khác** ("TE-E2, năm 2024")?~~ **Đã chốt 2026-10-12: cách 3 gọn** + trường `choice` cho nút bấm + luôn chạy câu hỏi gốc, xem 4.3 bước 0 và 4.3b.
3. ~~**Số lần hỏi lại liên tiếp tối đa**~~ **Đã chốt 2026-10-12:** chỉ đếm `unclear` liên tiếp, đến 2 thì thả `pending`; đổi chủ đề (`new_question`) và `cancel` không bị tính, xem 4.3c.
4. ~~**Ca M12**~~ **Đã chốt 2026-10-12:** ngữ cảnh có nhiều năm mà tool chỉ nhận một năm thì không điền (mục 4.1).
6. ~~**"Cả hai" / "tất cả"**~~ **Đã chốt 2026-10-12:** ≤ 3 lựa chọn thì lấy hết, > 3 thì xin chọn tối đa 3 (4.3 bước 3).
5. ~~Ghi chú nhãn `router_cases.csv`~~ **Đã áp dụng 2026-10-12** (R021 → ADMISSION, R100 sửa tool, thêm 10 ca UNIVERSITY_INFO R160–R169, tách `required_tools`/`optional_tools`; 169 dòng).
