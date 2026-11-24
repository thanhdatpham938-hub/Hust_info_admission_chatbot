"""Cau mau song ngu Viet-Anh (PLAN - StateGraph (v1), muc 6; nguoi dung duyet 2026-10-19).

Cau mau KHONG qua LLM: tu choi, hoi lai, thong bao, loi he thong deu kiem duoc tuyet doi (AC7, AC9) va nhanh.
Danh sach lua chon dung tu `candidates` cua tool, khong do LLM viet. Ngon ngu khac Viet-Anh: in ca hai ban.
"""

OFFICIAL_URL = "https://ts.hust.edu.vn"     # trang tuyen sinh chinh thuc (nguoi dung chot chi dung link nay)

TEMPLATES: dict[str, dict[str, str]] = {
    "other_university": {
        "vi": "Mình chỉ hỗ trợ thông tin của Đại học Bách khoa Hà Nội (HUST), không có dữ liệu về trường khác. "
              "Bạn có thể hỏi về HUST, ví dụ: \"Điểm chuẩn ngành Khoa học máy tính năm 2025?\"",
        "en": "I can only help with Hanoi University of Science and Technology (HUST) and have no data on other "
              "universities. You could ask, for example: \"What was the 2025 cut-off score for Computer Science?\""},
    "off_topic": {
        "vi": "Mình là trợ lý tra cứu tuyển sinh và học vụ của HUST nên không hỗ trợ được nội dung này. Bạn có thể "
              "hỏi về điểm chuẩn, học phí, ngành học, quy chế, học bổng…",
        "en": "I'm HUST's admissions and academic-affairs assistant, so I can't help with that. You can ask about "
              "cut-off scores, tuition, programs, regulations, scholarships…"},
    "other_language": {
        "vi": "Mình hỗ trợ tiếng Việt và tiếng Anh. Bạn vui lòng hỏi lại bằng một trong hai ngôn ngữ này.",
        "en": "I support Vietnamese and English. Please ask again in one of these languages."},
    "missing_info": {
        "vi": "Bạn muốn hỏi về {missing_info} nào? Ví dụ: \"Điểm chuẩn ngành IT1 năm 2025?\"",
        "en": "Could you be more specific about what you'd like to know? For example: \"What was the 2025 cut-off "
              "score for IT1?\""},
    "ambiguous": {
        "vi": "\"{mention}\" có thể là một trong các {kind} sau, bạn muốn hỏi cái nào?\n{choices}\n"
              "Bạn có thể bấm chọn, gõ mã hoặc số thứ tự.",
        "en": "\"{mention}\" could be one of the following {kind}. Which one do you mean?\n{choices}\n"
              "You can click, type the code or the number."},
    "too_many_choices": {
        "vi": "Mình tra được tối đa 3 {kind} mỗi lần. Bạn chọn giúp tối đa 3 trong danh sách:\n{choices}",
        "en": "I can look up at most 3 {kind} at a time. Please pick up to 3:\n{choices}"},
    "unclear": {
        "vi": "Mình chưa rõ bạn chọn cái nào. Bạn bấm chọn, gõ mã ({codes}) hoặc số thứ tự nhé.\n{choices}",
        "en": "I'm not sure which one you mean. Please click, type the code ({codes}) or the number.\n{choices}"},
    "released": {
        "vi": "Mình bỏ câu hỏi về \"{mention}\" để không chọn nhầm. Bạn có thể hỏi lại kèm mã, ví dụ "
              "\"Điểm {example} năm 2025\", hoặc hỏi câu khác.",
        "en": "I've dropped the question about \"{mention}\" to avoid picking the wrong one. You can ask again with "
              "a code, e.g. \"{example} cut-off score 2025\", or ask something else."},
    "cancel": {                                       # nguoi dung sua 2026-10-19: bo "Da bo cau hoi truoc"
        "vi": "Bạn còn cần giải đáp thắc mắc nào nữa không?",
        "en": "Is there anything else you'd like to ask?"},
    "too_many": {
        "vi": "Vui lòng hỏi từng ngành/năm để đảm bảo độ chính xác (tối đa 3 ngành, 3 năm, 3 phương thức mỗi câu).",
        "en": "Please ask about fewer programs/years at a time (at most 3 programs, 3 years and 3 methods per "
              "question)."},
    "not_found": {
        "vi": "Mình chưa có dữ liệu về {missing}.{available} Bạn có thể kiểm tra tại trang tuyển sinh chính thức: "
              + OFFICIAL_URL,
        "en": "I don't have data on {missing}.{available} You can check the official admissions site: "
              + OFFICIAL_URL},
    "low_confidence": {
        "vi": "Mình không tìm thấy thông tin đủ tin cậy trong nguồn dữ liệu hiện tại để trả lời câu này. Bạn có thể "
              "kiểm tra tại nguồn chính thức của HUST: " + OFFICIAL_URL,
        "en": "I couldn't find reliable enough information in my current sources to answer this. Please check "
              "HUST's official sources: " + OFFICIAL_URL},
    "announcement": {
        "vi": "Thông báo và tin tức của {faculty} thay đổi thường xuyên nên mình chưa tra trực tiếp được. Bạn xem "
              "tại kênh chính thức: {url}",
        "en": "{faculty}'s announcements change frequently, so I can't look them up directly yet. Please see the "
              "official channel: {url}"},
    "database_error": {
        "vi": "Xin lỗi, hệ thống đang gặp sự cố khi tra dữ liệu. Bạn vui lòng thử lại sau ít phút.",
        "en": "Sorry, the system ran into a problem while looking up data. Please try again in a few minutes."},
    "llm_error": {
        "vi": "Xin lỗi, mình đang không xử lý được câu hỏi lúc này. Bạn vui lòng thử lại sau ít phút.",
        "en": "Sorry, I can't process your question right now. Please try again in a few minutes."},
    "no_tool": {
        "vi": "Mình chưa xác định được bạn cần tra thông tin gì. Bạn thử hỏi cụ thể hơn, ví dụ kèm tên ngành hoặc "
              "năm.",
        "en": "I couldn't tell what information you need. Please try a more specific question, e.g. with a program "
              "name or year."},
}
TEMPLATES["internal_error"] = TEMPLATES["database_error"]   # nguoi dung chi can biet "su co, thu lai"

KIND = {"program": ("ngành", "programs"), "program_group": ("ngành", "programs"),
        "faculty": ("Trường/Khoa", "schools/faculties"), "cohort": ("khoá", "cohorts"),
        "purpose": ("mục đích", "purposes"), "certificate": ("chứng chỉ", "certificates"),
        "method": ("phương thức", "methods")}


def _one(code: str, lang: str, **kw) -> str:
    return TEMPLATES[code][lang].format(**kw)


def render(code: str, language: str, **kw) -> str:
    """language: vi | en | other. Ngon ngu khac -> in ca hai ban (khong biet nguoi hoi doc duoc gi)."""
    if language == "en":
        return _one(code, "en", **kw)
    if language == "other":
        return _one(code, "vi", **kw) + "\n\n" + _one(code, "en", **kw)
    return _one(code, "vi", **kw)


def kind_name(entity_type: str, language: str) -> str:
    vi, en = KIND.get(entity_type, KIND["program"])
    return en if language == "en" else vi


def choices_block(candidates: list[dict]) -> str:
    return "\n".join(f"{i}. {c['code']} – {c['name']}" for i, c in enumerate(candidates, 1))


def missing_parts(results: list[dict], language: str) -> tuple[str, str]:
    """Tu ToolResult.missing -> ("chỉ tiêu năm 2024", " Hiện có dữ liệu năm 2025, 2026.") (PRD 13.2)."""
    whats, years = [], set()
    for r in results:
        for m in r.get("missing") or []:
            if m.get("what") and m["what"] not in whats:
                whats.append(m["what"])
            years.update(m.get("available_years") or [])
    what = ", ".join(whats) if whats else ("nội dung bạn hỏi" if language != "en" else "what you asked")
    if not years:
        return what, ""
    ys = ", ".join(str(y) for y in sorted(years))
    return what, (f" Hiện có dữ liệu năm {ys}." if language != "en" else f" Data is available for {ys}.")
