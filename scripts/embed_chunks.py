"""Nhung 637 chunk trong data/rag/normalized/ vao Qdrant (collection hust_rag_2026_1).

Thuc hien PLAN - Embedding (v1), muc 6. Doc file .env qua python-dotenv (QDRANT_URL,
QDRANT_COLLECTION, EMBEDDING_MODEL, OPENAI_API_KEY) - cung quy uoc voi check_setup.py.

Truoc khi nhung:
  1. Goi lai load()/check() cua validate_metadata.py; con loi thi dung (metadata nam cung
     vector trong Qdrant - nhung du lieu loi la phai nhung lai toan bo).
  2. Dung chuoi embed = <document_title>[ <year>] | <heading>\n<text> - chi ghep nam khi
     ten tai lieu CHUA chua nam do (PLAN muc 5).

Vector:
  - "dense": 3072 chieu, cosine, text-embedding-3-large.
  - Khong co vector tu khoa (BM25) - xem PLAN muc 6.1 vi sao bo. Thay vao do tao chi muc
    full-text tren payload "text" (MatchText) de loc cac ma khong co truong rieng (vd K01).

ID diem = uuid5(NAMESPACE, chunk_id) - chay lai la ghi de dung chunk cu, khong sinh ban trung.

Dung:
  python scripts/embed_chunks.py              # bao loi neu collection da ton tai
  python scripts/embed_chunks.py --recreate   # xoa va dung lai tu dau
"""

import json
import sys
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_metadata as vm  # noqa: E402  (dung lai load()/check(), xem PLAN muc 10)

NAMESPACE = uuid.UUID("b9f7b1e0-6b1b-4b0b-8b0b-2b7b7b1b7b1b")  # co dinh - khong duoc doi
BATCH = 100
EMBED_DIM = 3072  # text-embedding-3-large (doi tu -small/1536 ngay 2026-10-04, xem PLAN muc 6.3)

YEAR_RE_CACHE: dict[str, bool] = {}


def has_year(title: str, year: int) -> bool:
    """True neu ten tai lieu da chua dung nam do (vd 'Sổ tay sinh viên 2026', year=2026)."""
    return str(year) in title


def embed_string(c: dict) -> str:
    title = c["document_title"]
    prefix = f"{title} {c['year']}" if not has_year(title, c["year"]) else title
    return f"{prefix} | {c['heading']}\n{c['text']}"


def load_normalized() -> list[dict]:
    chunks = []
    for f in sorted((ROOT / "data" / "rag" / "normalized").glob("*.chunks.jsonl")):
        chunks += [json.loads(l) for l in f.open(encoding="utf-8")]
    return chunks


def compute_version_flags(chunks: list[dict]) -> None:
    """Ganh nhom tai lieu co nhieu nam (de an, cong bo diem chuan): them is_latest/versioned
    vao tung chunk. Tinh luc nhung (khong ghi vao file chuan hoa) - xem PLAN muc 6.2."""
    import re
    def family(c: dict) -> tuple[str, str]:
        bare = re.sub(r"\s*\b(19|20)\d{2}\b", "", c["document_title"]).strip()
        return (c["document_type"], bare)

    years_by_family: dict[tuple[str, str], set[int]] = defaultdict(set)
    for c in chunks:
        years_by_family[family(c)].add(c["year"])
    for c in chunks:
        fam = family(c)
        years = years_by_family[fam]
        c["versioned"] = len(years) > 1
        c["is_latest"] = c["year"] == max(years)


def make_point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, chunk_id))


def ensure_collection(client: QdrantClient, name: str, recreate: bool) -> None:
    exists = client.collection_exists(name)
    if exists and not recreate:
        raise SystemExit(
            f"Collection '{name}' đã tồn tại. Dùng --recreate nếu muốn xoá và dựng lại "
            f"(rẻ: ~0,007 USD, dưới 1 phút)."
        )
    if exists:
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config={"dense": models.VectorParams(size=EMBED_DIM, distance=models.Distance.COSINE)},
    )
    # Chi muc payload (PLAN muc 6, buoc 5)
    for field, schema in [
        ("year", models.PayloadSchemaType.INTEGER),
        ("document_type", models.PayloadSchemaType.KEYWORD),
        ("program_code", models.PayloadSchemaType.KEYWORD),
        ("faculty_code", models.PayloadSchemaType.KEYWORD),
        ("cohort", models.PayloadSchemaType.KEYWORD),
        ("dieu_no", models.PayloadSchemaType.KEYWORD),
        ("chunk_id", models.PayloadSchemaType.KEYWORD),
        ("is_latest", models.PayloadSchemaType.BOOL),
        ("versioned", models.PayloadSchemaType.BOOL),
    ]:
        client.create_payload_index(name, field_name=field, field_schema=schema)
    # Chi muc full-text tren "text" (PLAN muc 6.1) - dung lam BO LOC (MatchText), khong cham diem.
    client.create_payload_index(
        name, field_name="text",
        field_schema=models.TextIndexParams(
            type=models.TextIndexType.TEXT,
            tokenizer=models.TokenizerType.WORD,
            lowercase=True,
            min_token_len=2,
        ),
    )


def embed_batch(oa: OpenAI, model: str, texts: list[str]) -> list[list[float]]:
    resp = oa.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def main() -> None:
    recreate = "--recreate" in sys.argv
    load_dotenv(ROOT / ".env")
    import os
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection = os.getenv("QDRANT_COLLECTION", "hust_rag_2026_1")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        sys.exit("OPENAI_API_KEY trống trong .env — xem scripts/check_setup.py")

    print("1. Kiểm tra metadata (validate_metadata.load/check)")
    chunks_by_file, tables = vm.load()
    issues = vm.check(chunks_by_file, tables)
    errors = [i for i in issues if i[0] == "E"]
    if errors:
        print(f"  Còn {len(errors)} lỗi metadata — sửa trước rồi mới nhúng (xem validate_metadata.py).")
        vm.report(issues)
        sys.exit(1)
    print(f"  0 lỗi ({len(chunks_by_file)} chunk, {len(tables)} bảng CSV)")

    chunks = load_normalized()
    assert len(chunks) == len(chunks_by_file), "load_normalized lệch so với validate_metadata.load"
    compute_version_flags(chunks)
    print(f"  versioned=True: {sum(c['versioned'] for c in chunks)} chunk "
          f"(is_latest=False trong số đó: {sum(c['versioned'] and not c['is_latest'] for c in chunks)})")

    print(f"2. Dựng chuỗi embed cho {len(chunks)} chunk")
    texts = [embed_string(c) for c in chunks]

    print(f"3. Tạo collection '{collection}' ({'recreate' if recreate else 'mới'})")
    client = QdrantClient(url=qdrant_url, timeout=30)
    ensure_collection(client, collection, recreate)

    print(f"4. Gọi OpenAI ({model}), lô {BATCH}")
    oa = OpenAI(api_key=key)
    vectors: list[list[float]] = []
    t0 = time.time()
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        vectors += embed_batch(oa, model, batch)
        print(f"  {min(i + BATCH, len(texts))}/{len(texts)}")
    print(f"  xong trong {time.time() - t0:.1f}s")

    print("5. Ghi điểm vào Qdrant")
    points = []
    for c, vec in zip(chunks, vectors):
        payload = dict(c)
        points.append(models.PointStruct(
            id=make_point_id(c["chunk_id"]),
            vector={"dense": vec},
            payload=payload,
        ))
    for i in range(0, len(points), BATCH):
        client.upsert(collection_name=collection, points=points[i:i + BATCH])
    print(f"  đã ghi {len(points)} điểm")

    print("6. Tự kiểm")
    ok = self_check(client, collection, chunks, vectors, oa, model)
    sys.exit(0 if ok else 1)


def self_check(client, collection, chunks, vectors, oa, model) -> bool:
    import random
    ok = True

    count = client.count(collection, exact=True).count
    expected_ids = {c["chunk_id"] for c in chunks}
    manifest = ROOT / "data" / "rag" / "normalized" / "_chunk_ids.txt"
    manifest_ids = set(manifest.read_text(encoding="utf-8").split()) if manifest.exists() else set()
    print(f"  [{'OK' if count == len(chunks) else 'LỖI'}] số điểm = {count} (kỳ vọng {len(chunks)})")
    ok &= count == len(chunks)
    if manifest_ids:
        same = expected_ids == manifest_ids
        print(f"  [{'OK' if same else 'LỖI'}] chunk_id khớp _chunk_ids.txt")
        ok &= same

    # So lai vector cua 20 chunk ngau nhien. NGUONG 0.98, khong phai 0.999: da do thuc te
    # (2026-10-04) text-embedding-3-large KHONG hoan toan deterministic - nhung lai TUNG CAI
    # MOT (khong qua lo) cho cosine 0.9966-1.0 tren 40 mau, du la nhieu so thuc cua API, khong
    # phai loi gan sai vector (loi that se cho cosine rat thap, vd <0.5, vi noi dung khac han).
    sample = random.sample(range(len(chunks)), min(20, len(chunks)))
    texts_s = [embed_string(chunks[i]) for i in sample]
    fresh = embed_batch(oa, model, texts_s)
    cos_min = 1.0
    for idx, i in enumerate(sample):
        a, b = vectors[i], fresh[idx]
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        cos = dot / (na * nb)
        cos_min = min(cos_min, cos)
    print(f"  [{'OK' if cos_min >= 0.98 else 'LỖI'}] cosine thấp nhất (20 mẫu nhúng lại) = {cos_min:.5f}")
    ok &= cos_min >= 0.999

    # So payload cua 5 diem voi dong jsonl goc
    pick = random.sample(chunks, min(5, len(chunks)))
    ids = [make_point_id(c["chunk_id"]) for c in pick]
    got = {p.id: p.payload for p in client.retrieve(collection, ids=ids, with_payload=True)}
    mismatch = 0
    for c, pid in zip(pick, ids):
        payload = got.get(pid, {})
        for k, v in c.items():
            if payload.get(k) != v:
                mismatch += 1
    print(f"  [{'OK' if mismatch == 0 else 'LỖI'}] payload khớp jsonl gốc (5 điểm, {mismatch} lệch trường)")
    ok &= mismatch == 0

    def top_doc(query: str, flt: models.Filter | None = None) -> str:
        vec = embed_batch(oa, model, [query])[0]
        res = client.query_points(collection, query=vec, using="dense", query_filter=flt, limit=1).points
        return res[0].payload["document_title"] if res else ""

    t1 = top_doc("phương thức tuyển sinh năm nay",
                 models.Filter(must=[models.FieldCondition(key="is_latest", match=models.MatchValue(value=True))]))
    print(f"  [{'OK' if '2026' in t1 else 'LỖI'}] không nêu năm + is_latest -> {t1!r}")
    ok &= "2026" in t1

    t2 = top_doc("phương thức tuyển sinh năm 2024",
                 models.Filter(should=[
                     models.FieldCondition(key="year", match=models.MatchValue(value=2024)),
                     models.FieldCondition(key="versioned", match=models.MatchValue(value=False)),
                 ]))
    print(f"  [{'OK' if '2024' in t2 else 'LỖI'}] nêu năm 2024 -> {t2!r}")
    ok &= "2024" in t2

    t3 = top_doc("chuẩn ngoại ngữ đầu ra",
                 models.Filter(must=[models.FieldCondition(key="cohort", match=models.MatchValue(value="K71+"))]))
    print(f"  [{'OK' if 'K71' in t3 else 'LỖI'}] lọc cohort K71+ -> {t3!r}")
    ok &= "K71" in t3

    flt_k01 = models.Filter(must=[models.FieldCondition(key="text", match=models.MatchText(text="K01"))])
    res_k01 = client.scroll(collection, scroll_filter=flt_k01, limit=1, with_payload=False)[0]
    print(f"  [{'OK' if res_k01 else 'LỖI'}] chỉ mục full-text lọc 'K01' -> {len(res_k01)} điểm")
    ok &= bool(res_k01)

    return ok


if __name__ == "__main__":
    main()
