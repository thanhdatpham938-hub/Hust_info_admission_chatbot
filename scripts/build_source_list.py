"""Sinh docs/nguon_du_lieu.md: tong hop moi link nguon DANG DUOC DUNG trong du lieu.

Doc truong source_url cua moi chunk goc (data/rag/raw_chunks/), moi CSV (data/processed/),
data/faculty/*/info.json -> chi liet ke link that su co trong du lieu, kem so chunk/ban ghi dung no.
Cuoi file co dong tu kiem: so link dang dung ma chua duoc liet ke phai bang 0.

Dung: python scripts/build_source_list.py
"""
import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)   # cac duong dan ben duoi tinh tu goc du an

import json, glob, csv, collections
R = lambda f: list(csv.DictReader(open(f, encoding='utf-8-sig')))

# dem so ban ghi / chunk dung moi link
use = collections.defaultdict(collections.Counter)
for f in glob.glob('data/rag/raw_chunks/*.chunks.jsonl'):
    for l in open(f, encoding='utf-8'):
        use[json.loads(l).get('source_url', '')]['RAG ' + os.path.basename(f).replace('.chunks.jsonl', '')] += 1
for f in glob.glob('data/processed/*.csv'):
    for row in R(f):
        u = row.get('source_url')
        if u:
            use[u][os.path.basename(f)] += 1


def used(u):
    c = use.get(u)
    if not c:
        return '—'
    return '; '.join(f'{k} ({v})' for k, v in sorted(c.items()))


out = []
w = out.append
w('# Tổng hợp link nguồn dữ liệu — HUST Info & Admission Assistant')
w('')
w('Cập nhật 2026-09-26 · `dataset_version = 2026.1`. Sinh tự động từ trường `source_url` của mọi chunk RAG (`data/rag/raw_chunks/`), '
  'mọi CSV (`data/processed/`), `data/programs/*.json` và `data/faculty/*/info.json`, nên chỉ liệt kê link **đang thực sự được dùng** '
  '(trừ mục 5). Cột "Dùng ở" ghi tên file và số chunk/bản ghi trong ngoặc.')
w('')


def table(rows):
    w('| # | Nguồn | Link | Dùng ở |')
    w('| --: | --- | --- | --- |')
    for i, (name, u) in enumerate(rows, 1):
        w(f'| {i} | {name} | {u} | {used(u)} |')
    w('')


w('## 1. Trang tuyển sinh (ts.hust.edu.vn)')
w('')
table([
    ('Phương án tuyển sinh 2025', 'https://ts.hust.edu.vn/tin-tuc/dhbk-ha-noi-cong-bo-phuong-an-tuyen-sinh-dai-hoc-chinh-quy-nam-2025'),
    ('Thông tin tuyển sinh 2026', 'https://ts.hust.edu.vn/tin-tuc/thong-tin-tuyen-sinh-dai-hoc-chinh-quy-nam-2026'),
    ('Điểm chuẩn 2024', 'https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-2024-diem-thi-dgtd-cao-nhat-83-82-diem-thi-tot-nghiep-thpt-cao-nhat-28-53'),
    ('Điểm chuẩn 2025', 'https://ts.hust.edu.vn/tin-tuc/diem-chuan-cao-nhat-dh-bach-khoa-ha-noi-2025-29-39-diem-thpt-tuong-duong-93-96-diem-xttn-va-86-97-diem-tsa'),
    ('Điểm chuẩn 2026', 'https://ts.hust.edu.vn/tin-tuc/diem-chuan-dai-hoc-bach-khoa-ha-noi-nam-2026'),
    ('Quy định xét tuyển tài năng 2026', 'https://ts.hust.edu.vn/tin-tuc/quy-dinh-ve-phuong-thuc-xet-tuyen-tai-nang-nam-2026'),
    ('Giới thiệu kỳ thi ĐGTD (TSA)', 'https://ts.hust.edu.vn/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa'),
    ('Giới thiệu kỳ thi ĐGTD (TSA) — đường dẫn /en', 'https://ts.hust.edu.vn/index.php/en/tin-tuc/gioi-thieu-ve-ky-thi-danh-gia-tu-duy-tsa'),
    ('Cẩm nang thi ĐGTD 2026', 'https://ts.hust.edu.vn/tin-tuc/cam-nang-thi-danh-gia-tu-duy-tsa-2026-xuat-ban-lan-thu-2'),
    ('Danh mục 68 ngành (trang index)', 'https://ts.hust.edu.vn/training-cate/nganh-dao-tao-dai-hoc'),
])
w('> Các bài điểm chuẩn / đề án trên cũng là nguồn của những bảng đọc từ **ảnh** trong bài: `programs_2024.csv`, `programs_2025.csv`, '
  '`cert_cefr_equivalence.csv`, `cert_bonus_conversion.csv` (cột `source` ghi tên ảnh, ví dụ `bka1/bka2`, `image_2b.png`, `quydoi-cccnn-2026.png`).')
w('')

w('## 2. Văn bản quy chế, quy định, sổ tay')
w('')
table([
    ('Quy chế đào tạo 2025 (5445/QĐ-ĐHBK)', 'https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf'),
    ('Quy chế thi ĐGTD (10461/QĐ-ĐHBK, 23/10/2024) — Google Drive dẫn từ trang TSA', 'https://drive.google.com/file/d/1SJ1VnlXIXQHshZvqmu6KC6iN66l_RCxA/view'),
    ('Quy định chuẩn ngoại ngữ K71 (10828/QĐ-ĐHBK, 07/9/2026)', 'https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=51634'),
    ('Quy định chuẩn ngoại ngữ K70 (10728/QĐ-ĐHBK, 26/9/2025)', 'https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=44574'),
    ('Sổ tay sinh viên 2026 (bản web)', 'https://ctsv.hust.edu.vn/so-tay-sv'),
    ('Đề án tuyển sinh 2024 (trang đăng; PDF nhúng Google Drive trùng từng byte với file trong máy)', 'https://ts.hust.edu.vn/tin-tuc/de-an-tuyen-sinh-dai-hoc-nam-2024'),
    ('Quyết định học phí 2024–2025', 'https://ctt.hust.edu.vn/Upload/Nguyen%20Quoc%20Dat/files/DTDH_QDQC/Hocphi/2024-2025/2024_2_%20Q%C4%90%20h%E1%BB%8Dc%20ph%C3%AD%20-%202024-2025.pdf'),
    ('Quyết định học phí 2025–2026 (10232/QĐ-ĐHBK, 12/9/2025)', 'https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2025-2026/QD%20HOC%20PHI%20-%202025-2026-final.pdf'),
    ('Quyết định học phí 2026–2027 (12006/QĐ-ĐHBK, 05/10/2026)', 'https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hocphi/2026-2027/12006_Q%C4%90-%C4%90HBK.pdf'),
    ('Quy định học bổng KKHT 2022', 'https://ctt.hust.edu.vn/Upload/Nguyen%20Viet%20Tien/files/Quy%20%C4%91%E1%BB%8Bnh%20HB%20KKHT%20n%C4%83m%202022.pdf'),
])
w('Các file `Quy_dinh_ngoai_ngu_K71_2026.pdf`, `Quy_dinh_ngoai_ngu_K70.pdf`, `QCDT_2025_5445_QD-DHBK.pdf`, `10461-QD-DHBK_Quy_che_thi_TSA_2024.pdf`, '
  '`qui-dinh-ve-xttn-nam-2026-ky.pdf`, `So tay sinh vien_2026.pdf` là bản tải về của các link ở bảng trên.')
w('')

w('## 3. Trường / Khoa (10 đơn vị)')
w('')
extra_staff = {
    'FAMI': ['https://fami.hust.edu.vn/danh-sach-giang-vien/n-3/', 'https://fami.hust.edu.vn/danh-sach-giang-vien/bo-mon-toan-ung-dung/'],
    'SOFL': ['https://sofl.hust.edu.vn/danh-muc-can-bo7', 'https://sofl.hust.edu.vn/danh-muc-can-bo6', 'https://sofl.hust.edu.vn/danh-muc-can-bo5'],
}
w('Trang giới thiệu là nguồn của `RAG gioi_thieu_truong_khoa` (số chunk trong ngoặc); các trang còn lại là nguồn của `data/faculty/<mã>/info.json`.')
w('')
w('| Mã | Tên | Website chính thức | Giới thiệu | Cán bộ | Danh sách ngành |')
w('| --- | --- | --- | --- | --- | --- |')
for f in sorted(glob.glob('data/faculty/*/info.json')):
    d = json.load(open(f, encoding='utf-8'))
    s = d['sources']
    staff = '<br>'.join([s['can_bo']] + extra_staff.get(d['faculty_code'], []))
    n = use.get(s['gioi_thieu'], {}).get('RAG gioi_thieu_truong_khoa', 0)
    w(f"| {d['faculty_code']} | {d['faculty_name']} | {d['official_channel_url']} | {s['gioi_thieu']} ({n}) | {staff} | {s['nganh']} |")
w('')

w('## 4. 68 ngành đào tạo 2026')
w('')
w('Cột **Trang giới thiệu** là nguồn của `RAG nganh_dao_tao` (151 chunk), `program_overview_2026.csv`, `tuition_2026.csv` và `data/programs/<mã>.json`. '
  'Cột **CTĐT** là link chương trình đào tạo trên web Trường/Khoa (`curriculum_url`).')
w('')
names = {r['program_code']: (r['program_name'], r['faculty_name']) for r in R('data/processed/programs_2026.csv')}
ov = R('data/processed/program_overview_2026.csv')
w('| # | Mã | Tên ngành | Trường/Khoa | Trang giới thiệu (ts.hust.edu.vn) | CTĐT |')
w('| --: | --- | --- | --- | --- | --- |')
for i, r in enumerate(sorted(ov, key=lambda r: (names.get(r['program_code'], ('', ''))[1], r['program_code'])), 1):
    n, fac = names.get(r['program_code'], (r['program_name'], ''))
    w(f"| {i} | {r['program_code']} | {n} | {fac} | {r['source_url']} | {r['curriculum_url'] or '*(chưa có)*'} |")
missing = [r['program_code'] for r in ov if not r['curriculum_url']]
w('')
w(f'Chưa có link CTĐT: {", ".join(missing)}.' if missing else 'Đủ link CTĐT cho cả 68 ngành. Riêng ED5: trang ts.hust.edu.vn trỏ tới một bài báo nên dùng trang CTĐT trên web Khoa (fed.hust.edu.vn).')
w('')

w('## 5. Link đã ghi trong `data/link.md` nhưng chưa dùng làm nguồn')
w('')
w('| Link | Lý do |')
w('| --- | --- |')
w('| https://ts.hust.edu.vn/en/p/faqs | FAQ tuyển sinh — chưa crawl |')
w('| https://ts.hust.edu.vn/tin-tuc/hoc-phi-dai-hoc-chinh-quy | Trang học phí — đã tải (`data/raw/tuition/hoc_phi_page.html`) để đối chiếu; học phí 2026 lấy từ 68 trang ngành |')
w('| `03102023-quy-che-thi-tu-duy-dhbkhn.pdf` (818/QĐ-ĐHBK, 2023) | Quy chế thi ĐGTD cũ, đã thay bằng 10461/QĐ-ĐHBK |')
w('')

text = '\n'.join(out)
left = sorted(u for u in use if u.startswith('http') and u not in text)
w('## Kiểm tra')
w('')
w(f'- Số link đang được dữ liệu dùng nhưng chưa có trong file này: **{len(left)}**' + ('' if not left else ' → ' + ', '.join(left)))
open('docs/nguon_du_lieu.md', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(len(out), 'dong; left =', left, '; missing ctdt =', missing)
