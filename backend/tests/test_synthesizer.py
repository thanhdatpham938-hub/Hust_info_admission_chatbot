"""build_evidence, verify, finalize, template_answer (PLAN - Synthesizer (v1)). Khong mang."""

from app.graph.guardrails.check import finalize, verify
from app.graph.render import template_answer
from app.graph.synthesizer import build_evidence

SRC = {"title": "Điểm chuẩn 2025", "url": "https://ts.hust.edu.vn/dc2025"}


def t1_result(n_rows=1):
    rows = [{"program_code": f"P{i}", "program_name": f"Ngành {i}", "year": 2025, "method_code": "THPT",
             "score": 20.5 + i, "scale": 30, "source": SRC, "verification_status": "manual_verified"}
            for i in range(n_rows)]
    return {"status": "ok", "data": {"rows": rows, "deltas": []}, "sources": [SRC],
            "resolved": [{"mention": "x", "entity_type": "program", "codes": ["IT1"], "matched_by": "exact"}]}


CALL = {"tool": "admission_scores", "args": {}}


def test_danh_so_nguon_va_bo_truong_noi_bo():
    ev = build_evidence("Điểm IT1?", "ADMISSION_QUERY", "vi", None, [CALL], [t1_result()])
    item = ev["payload"]["evidence"][0]
    assert item["source_ids"] == [1] and ev["sources"][0]["url"] == SRC["url"]
    assert "source" not in item["data"]["rows"][0] and "verification_status" not in item["data"]["rows"][0]


def test_bang_dai_do_code_dung():
    ev = build_evidence("Bảng điểm?", "ADMISSION_QUERY", "vi", None, [CALL], [t1_result(20)])
    assert len(ev["tables"]) == 1 and ev["tables"][0].count("\n") == 21          # tieu de + gach + 20 dong
    assert ev["payload"]["evidence"][0]["data"]["rows"] == {"bang_da_hien_thi": 1, "so_dong": 20}
    assert "tables_note" in ev["payload"]


def test_ten_nganh_tieng_anh_do_code_chon():
    names = {"IT1": ("CNTT: Khoa học Máy tính", "Computer Science")}
    ev = build_evidence("IT1 score?", "ADMISSION_QUERY", "en", None, [CALL], [t1_result()], names)
    assert ev["payload"]["program_names"] == {"IT1": {"en": "Computer Science", "vi": "CNTT: Khoa học Máy tính"}}
    assert "program_names" not in build_evidence("q", "X", "vi", None, [CALL], [t1_result()], names)["payload"]


def test_xoa_trich_dan_sai_va_ghep_nguon():
    ev = build_evidence("Điểm IT1?", "ADMISSION_QUERY", "vi", None, [CALL], [t1_result()])
    text, issues, used = verify("Điểm P0 năm 2025 là 20,5 [1] [7].", ev)
    assert issues == [] and "[7]" not in text and used == {1}
    answer, cites = finalize(text, ev, used, "vi")
    assert answer.endswith("[1] Điểm chuẩn 2025 — https://ts.hust.edu.vn/dc2025") and cites[0]["n"] == 1


def test_hoc_phi_thieu_don_vi_nam():
    res = {"status": "ok", "data": {"programs": [{"program_code": "TROY-IT", "amount_min": 34.0,
                                                  "unit": "triệu đồng/học kỳ", "per": "học kỳ", "year": 2026}]},
           "sources": [SRC]}
    ev = build_evidence("Học phí TROY-IT?", "ADMISSION_QUERY", "vi", None, [{"tool": "tuition_fees", "args": {}}], [res])
    assert any("đơn vị" in i for i in verify("Học phí TROY-IT là 34 triệu đồng.", ev)[1])
    assert verify("Học phí TROY-IT năm 2026 là 34 triệu đồng/học kỳ.", ev)[1] == []


def test_ban_dung_tu_du_lieu_co_bang_va_nguon():
    ev = build_evidence("Điểm IT1?", "ADMISSION_QUERY", "vi", None, [CALL], [t1_result(2)])
    text = template_answer(ev, [t1_result(2)], "vi")
    assert text.startswith("Dưới đây là dữ liệu tra được:") and "| P1 |" in text and "20,5" in text
    assert "[1] Điểm chuẩn 2025" in text


# ---------------------------------------------------------------- PLAN Sua loi sau chay thu Synthesizer (v1)
RAG_CHUNK = {"document_title": "Quy chế đào tạo", "heading": "Điều 3", "dieu_no": "3", "khoan_no": "3", "page_no": "5",
             "year": 2025, "text": "Thời gian tối đa ...",
             "citation": {"title": "Quy chế đào tạo — Điều 3 khoản 3 — Trang 5", "url": "https://x/qcdt"}}
RAG_CALL = {"tool": "rag_search", "args": {}}


def rag_result(*chunks):
    return {"status": "ok", "data": {"chunks": list(chunks) or [RAG_CHUNK]}, "sources": []}


def test_buoc1_chenh_lech_am_chap_nhan_gia_tri_tuyet_doi():           # S03
    res = t1_result()
    res["data"]["deltas"] = [{"kind": "program", "a": "IT1", "b": "IT2", "value_a": 29.39, "value_b": 29.03,
                              "diff": -0.36}]
    ev = build_evidence("So sánh IT1 IT2?", "ADMISSION_QUERY", "vi", None, [CALL], [res])
    assert verify("IT1 cao hơn IT2 0,36 điểm [1].", ev)[1] == []
    assert verify("IT1 cao hơn IT2 0,63 điểm [1].", ev)[1]              # so sai that van bi bat


def test_buoc1_khoi_nguon_khong_lap_vi_tri():
    ev = build_evidence("Thời gian tối đa?", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result()])
    text, _, used = verify("Tối đa ... [1].", ev)
    answer, _ = finalize(text, ev, used, "vi")
    assert "[1] Quy chế đào tạo — Điều 3, khoản 3, trang 5 — https://x/qcdt" in answer
    assert answer.count("Điều 3") == 1


def test_buoc1_bang_chenh_lech_ten_cot_de_doc():
    from app.graph.render import md_table
    t = md_table([{"kind": "year", "program_code": "IT1", "a": "2024", "b": "2025", "value_a": 28.5,
                   "value_b": 29.0, "diff": 0.5}], "vi")
    assert t.startswith("| So sánh | Mã ngành | A | B | Giá trị A | Giá trị B | Chênh lệch (B − A) |")
    assert "| giữa các năm |" in t and "kind" not in t


def test_buoc2_cau_tieng_anh_tra_loi_tieng_viet_phai_viet_lai():      # S26-S28, S30
    ev = build_evidence("What was the score of IT2 in 2025?", "ADMISSION_QUERY", "en", None, [CALL], [t1_result()])
    vi = "Điểm chuẩn của ngành P0 năm 2025 theo phương thức THPT là 20,5 điểm trên thang 30 [1]."
    assert any("English" in i for i in verify(vi, ev)[1])
    en = ("The 2025 admission score of P0 via the THPT method was 20.5 on a 30-point scale, according to "
          "\"Điểm chuẩn 2025\" (Vietnamese document) [1].")
    assert verify(en, ev)[1] == []
    assert not any("English" in i for i in verify(vi, build_evidence("q", "X", "vi", None, [CALL], [t1_result()]))[1])


def test_buoc2_nhac_ngon_ngu_ngay_sau_du_lieu():
    from app.graph.synthesizer import build_messages
    assert build_messages({"language": "en"})[1]["content"].endswith("Write the answer in ENGLISH.")
    assert build_messages({"language": "vi"})[1]["content"].endswith("Viết câu trả lời bằng tiếng Việt.")


def test_buoc5_muc_hoc_phi_kem_ten_nganh_bo_nhan_noi_bo():             # S07
    res = {"status": "ok", "sources": [SRC], "data": {"credit_rules": [
        {"rule_id": "hptc2627-chuan-700", "group_text": "Chương trình chuẩn - nhóm 700", "amount_min": 700,
         "unit": "nghìn đồng/tín chỉ", "program_codes": ["IT1", "ME1"], "year": 2026}]}}
    names = {"IT1": ("Khoa học Máy tính", "Computer Science"), "ME1": ("Kỹ thuật Cơ điện tử", None)}
    ev = build_evidence("Học phí tín chỉ?", "ADMISSION_QUERY", "vi", None, [{"tool": "tuition_fees", "args": {}}],
                        [res], names)
    rule = ev["payload"]["evidence"][0]["data"]["credit_rules"][0]
    assert rule["group_text"] == "Chương trình chuẩn" and "rule_id" not in rule and "program_codes" not in rule
    assert rule["ap_dung_cho"] == ["Khoa học Máy tính (IT1)", "Kỹ thuật Cơ điện tử (ME1)"]
    en = build_evidence("q", "X", "en", None, [{"tool": "tuition_fees", "args": {}}],
                        [{**res, "data": {"credit_rules": [{**res["data"]["credit_rules"][0]}]}}], names)
    assert en["payload"]["evidence"][0]["data"]["credit_rules"][0]["ap_dung_cho"][0] == "Computer Science (IT1)"


def test_buoc5_doan_van_ban_co_thu_hang():
    ch2 = {**RAG_CHUNK, "dieu_no": "19", "citation": {**RAG_CHUNK["citation"], "title": "khác"}}
    ev = build_evidence("q", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result(RAG_CHUNK, ch2)])
    assert [c["rank"] for c in ev["payload"]["evidence"][0]["chunks"]] == [1, 2]


# ---------------------------------------------------------------- N1-N11 (Bao cao sua loi Synthesizer, muc 5)
PI_CALL = {"tool": "program_info", "args": {}}


def test_n1_chi_tieu_tong_nganh_ghi_ro_loai():               # S06, S32
    res = {"status": "ok", "sources": [SRC], "data": {"programs": [{
        "program_code": "EE1", "program_name": "Kỹ thuật điện",
        "quotas": [{"year": 2026, "quota": 240, "quota_type": "tong_nganh", "source": SRC}]}]}}
    ev = build_evidence("EE1 bao nhiêu chỉ tiêu cho THPT?", "ADMISSION_QUERY", "vi", None, [PI_CALL], [res])
    q = ev["payload"]["evidence"][0]["data"]["programs"][0]["quotas"][0]
    assert q == {"year": 2026, "tong_chi_tieu_nganh": 240,
                 "ghi_chu": "Đây là TỔNG chỉ tiêu của ngành cho mọi phương thức; dữ liệu chưa có chỉ tiêu theo "
                            "từng phương thức."}
    assert 240 in ev["allowed"]


def test_n8_synthesizer_biet_hom_nay():                       # S04: LLM tu hieu "nam ngoai" = 2024
    from datetime import date
    ev = build_evidence("Năm ngoái điểm IT1?", "ADMISSION_QUERY", "vi", None, [CALL], [t1_result()],
                        today=date(2026, 10, 21))
    assert ev["payload"]["hom_nay"] == {"ngay": "2026-10-21", "nam_nay": 2026, "nam_ngoai": 2025}
    assert {2026, 2025} <= set(ev["allowed"])          # LLM ghi "năm ngoái (2025)" khong bi bao so la


def list_result():
    """Giong S04 that: THPT 1 nganh hang 1; XTTN_1.2 co 8 nganh cung 55 diem hang 1."""
    def row(code, method, value, scale, rank=1):
        return {"rank": rank, "program_code": code, "program_name": f"Ngành {code}", "faculty_code": "F",
                "faculty_name": "Trường F", "program_group_code": None, "year": 2025, "method_code": method,
                "combination_group": "all", "combination_group_label": "mọi tổ hợp", "value": value, "scale": scale,
                "is_rule_derived": False, "source": SRC}
    rows = [row("TROY-BA", "THPT", 19.0, 30)] + [row(f"P{i}", "XTTN_1.2", 55.0, 100) for i in range(8)]
    stats = [{"year": 2025, "method_code": "THPT", "count": 77, "min": 19.0, "max": 29.39},
             {"year": 2025, "method_code": "XTTN_1.2", "count": 65, "min": 55.0, "max": 93.18}]
    return {"status": "ok", "sources": [SRC], "data": {"rows": rows, "stats": stats, "deltas": [], "total_rows": 9,
                                                       "truncated": False}}


LIST_CALL = {"tool": "list_programs", "args": {"metric": "score", "order": "asc", "limit": 1}}


def test_n9_nhieu_nganh_cung_hang_gop_mot_dong():               # S04
    ev = build_evidence("Ngành nào điểm thấp nhất năm ngoái?", "ADMISSION_QUERY", "vi", None, [LIST_CALL],
                        [list_result()])
    rows = ev["payload"]["evidence"][0]["data"]["rows"]
    assert len(rows) == 2 and rows[0]["program_code"] == "TROY-BA"
    tie = rows[1]
    assert tie["so_nganh_cung_hang"] == 8 and tie["value"] == 55.0 and tie["method_code"] == "XTTN_1.2"
    assert tie["vi_du"] == [f"Ngành P{i} (P{i})" for i in range(5)] and tie["con_lai"] == 3
    assert "program_code" not in tie


def test_n9_ban_dung_tu_du_lieu_gon_khong_bang_thong_ke():
    ev = build_evidence("q", "ADMISSION_QUERY", "vi", None, [LIST_CALL], [list_result()])
    text = template_answer(ev, [list_result()], "vi")
    assert "count" not in text and "| min |" not in text
    assert text.count("\n| ") <= 3                       # tieu de + 2 dong, khong phai 9 dong
    assert "8 ngành" in text


def group_tuition_result(n=20):
    progs = [{"program_code": f"P{i}", "program_name": f"Ngành {i}", "program_group_code": "chuan", "year": 2026,
              "amount_min": 28.0, "amount_max": 40.0 if i else 22.0, "unit": "triệu đồng/năm", "per": "năm",
              "amount_text": "28 - 40 triệu đồng/năm",
              "source": {"title": f"Trang ngành (P{i})", "url": f"https://ts.hust.edu.vn/nganh/p{i}"}}
             for i in range(n)]
    stats = [{"unit": "triệu đồng/năm", "count": n, "min": 22.0, "max": 40.0, "program_codes": [f"P{i}" for i in range(n)]}]
    return {"status": "ok", "data": {"programs": progs, "stats": stats},
            "sources": [p["source"] for p in progs]}


GROUP_CALL = {"tool": "tuition_fees", "args": {"program_group": "hệ chuẩn", "programs": []}}


def test_n10_hoi_ca_nhom_chi_gui_tom_tat_mot_nguon():            # S09
    ev = build_evidence("Học phí IT-E6 có cao hơn hệ chuẩn không?", "ADMISSION_QUERY", "vi", None, [GROUP_CALL],
                        [group_tuition_result()])
    data = ev["payload"]["evidence"][0]["data"]
    assert "programs" not in data and ev["tables"] == []
    assert data["stats"] == [{"unit": "triệu đồng/năm", "count": 20, "min": 22.0, "max": 40.0}]
    assert len(ev["sources"]) == 1 and ev["sources"][0]["url"] == "https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc"
    assert "20 ngành" in ev["sources"][0]["title"]


def test_n10_cau_co_y_liet_ke_van_in_du_bang():
    ev = build_evidence("Liệt kê học phí từng ngành hệ chuẩn", "ADMISSION_QUERY", "vi", None, [GROUP_CALL],
                        [group_tuition_result()])
    assert len(ev["tables"]) == 1 and len(ev["sources"]) == 20


def test_n6_bang_dai_khong_cot_tho_va_nguon_gop():                # S09 khi nguoi dung muon xem tung nganh
    ev = build_evidence("Liệt kê học phí từng ngành hệ chuẩn", "ADMISSION_QUERY", "vi", None, [GROUP_CALL],
                        [group_tuition_result()])
    head = ev["tables"][0].splitlines()[0]
    assert "per" not in head.split(" | ") and "amount_text" not in head
    answer, cites = finalize("Học phí hệ chuẩn như bảng sau.", ev, set(), "vi")
    src = answer[answer.index("Nguồn:"):].splitlines()
    assert len(src) == 2                                   # "Nguồn:" + 1 dong gop
    assert src[1].startswith("[1]–[20] Trang ngành") and "20 trang" in src[1]
    assert len(cites) == 20                                # metadata API van du 20 trich dan (PRD 12)


# ---------------------------------------------------------------- N15: so phai co trong dung doan duoc trich
def two_chunks_evidence():
    d19 = {**RAG_CHUNK, "dieu_no": "19", "heading": "Điều 19. Cảnh báo học tập", "page_no": "18",
           "text": "Nâng một mức cảnh báo khi số TC không đạt lớn hơn 8; mức 3 khi nợ đọng lớn hơn 24 TC.",
           "citation": {"title": "Quy chế đào tạo — Điều 19", "url": "https://x/qcdt"}}
    d12 = {**RAG_CHUNK, "dieu_no": "12", "heading": "Điều 12. Xếp loại học lực", "page_no": "14",
           "text": "Xếp loại yếu khi CPA dưới 2,5; trung bình khi CPA từ 2,5 đến dưới 3,2.",
           "citation": {"title": "Quy chế đào tạo — Điều 12", "url": "https://x/qcdt"}}
    return build_evidence("Cảnh báo học tập?", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result(d19, d12)])


def test_n15_so_cua_doan_khong_duoc_trich_bi_bat():                                  # S12
    ev = two_chunks_evidence()
    ch = {c["heading"]: c["id"] for c in ev["payload"]["evidence"][0]["chunks"]}
    a, b = ch["Điều 19. Cảnh báo học tập"], ch["Điều 12. Xếp loại học lực"]
    assert a != b
    # Chi trich Dieu 19 nhung dung 2,5 va 3,2 cua Dieu 12 (cac so CO trong du lieu, nhung sai doan)
    _, issues, _ = verify(f"Nợ đọng lớn hơn 24 TC thì cảnh báo mức 3. CPA dưới 2,5 là yếu, từ 3,2 là khá [{a}].", ev)
    assert any("2,5" in i and "3,2" in i for i in issues)


def test_n15_so_dung_doan_duoc_trich_thi_dat():
    ev = two_chunks_evidence()
    ch = {c["heading"]: c["id"] for c in ev["payload"]["evidence"][0]["chunks"]}
    a, b = ch["Điều 19. Cảnh báo học tập"], ch["Điều 12. Xếp loại học lực"]
    assert verify(f"Nợ đọng lớn hơn 24 TC thì cảnh báo mức 3 [{a}]. CPA dưới 2,5 là yếu [{b}].", ev)[1] == []


def test_n15_so_cua_cau_hoi_va_so_nho_van_duoc_phep():
    ev = build_evidence("Năm 2025 cảnh báo thế nào?", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result()])
    cid = ev["payload"]["evidence"][0]["chunks"][0]["id"]
    assert verify(f"Năm 2025 có 2 mức cảnh báo [{cid}].", ev)[1] == []


def test_n15_van_kiem_so_la_toan_cuc_nhu_cu():
    ev = two_chunks_evidence()
    cid = ev["payload"]["evidence"][0]["chunks"][0]["id"]
    _, issues, _ = verify(f"Nợ đọng lớn hơn 99 TC [{cid}].", ev)
    assert any("KHÔNG có trong dữ liệu" in i for i in issues)


# ---------------------------------------------------------------- loi code-review 2026-11-26
def test_review1_hai_doan_chung_id_khong_mat_so_cua_doan_dau():
    """Hai doan cung url + vi tri -> cung [n]; so cua ca hai doan deu duoc phep (truoc: doan sau ghi de)."""
    a = {**RAG_CHUNK, "text": "Mức 1 khi nợ hơn 24 tín chỉ."}
    b = {**RAG_CHUNK, "text": "Mức 3 khi nợ hơn 36 tín chỉ."}
    ev = build_evidence("q", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result(a, b)])
    ids = {c["id"] for c in ev["payload"]["evidence"][0]["chunks"]}
    assert len(ids) == 1
    cid = ids.pop()
    assert verify(f"Nợ hơn 24 tín chỉ thì cảnh báo mức 1 [{cid}].", ev)[1] == []


def test_review2_nam_va_khoa_cua_doan_duoc_phep():
    """`year` cua doan gui cho LLM nen LLM duoc phep ghi nam do (truoc: bi bao so la)."""
    ch = {**RAG_CHUNK, "year": 2023, "text": "Quy định về cảnh báo học tập."}
    ev = build_evidence("q", "REGULATION_QUERY", "vi", None, [RAG_CALL], [rag_result(ch)])
    cid = ev["payload"]["evidence"][0]["chunks"][0]["id"]
    assert verify(f"Theo quy chế năm 2023, sinh viên bị cảnh báo [{cid}].", ev)[1] == []


def test_review7_so_la_va_so_sai_doan_bao_cung_mot_lan():
    ev = two_chunks_evidence()
    ch = {c["heading"]: c["id"] for c in ev["payload"]["evidence"][0]["chunks"]}
    a = ch["Điều 19. Cảnh báo học tập"]
    _, issues, _ = verify(f"Nợ hơn 99 TC thì cảnh báo. CPA dưới 2,5 là yếu [{a}].", ev)
    assert any("99" in i and "KHÔNG có trong dữ liệu" in i for i in issues)
    assert any("2,5" in i and "đã trích dẫn" in i for i in issues)
