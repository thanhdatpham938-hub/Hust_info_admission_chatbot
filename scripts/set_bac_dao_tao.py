"""Gan truong bac_dao_tao cho chunk da chuan hoa va cap nhat payload Qdrant (PLAN - Sua loi sau chay thu
Synthesizer (v1), buoc 6). KHONG nhung lai, KHONG goi OpenAI: vector giu nguyen, chi them mot truong payload.

Lan dung lai tu dau (normalize_chunks.py -> embed_chunks.py) da tu co truong nay; script nay chi de cap nhat du lieu
dang chay ma khong phai dung lai.

Dung: python scripts/set_bac_dao_tao.py            (can Qdrant dang chay: docker compose up -d)
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts")]
from app.core.config import get_settings
from embed_chunks import make_point_id
from normalize_chunks import FIELD_ORDER, OUT, SOURCES, bac_dao_tao
from qdrant_client import QdrantClient, models


def update_files() -> dict[str, list[str]]:
    """Them truong vao file normalized (giu thu tu FIELD_ORDER). Tra {nhan: [chunk_id]}."""
    by_label: dict[str, list[str]] = defaultdict(list)
    for name in SOURCES:
        f = OUT / f"{name}.chunks.jsonl"
        rows = [json.loads(line) for line in f.open(encoding="utf-8")]
        out = []
        for c in rows:
            c["bac_dao_tao"] = bac_dao_tao(name, c)
            out.append({k: c.get(k, "") for k in FIELD_ORDER})
            by_label[c["bac_dao_tao"]].append(c["chunk_id"])
        with f.open("w", encoding="utf-8") as w:
            for c in out:
                w.write(json.dumps(c, ensure_ascii=False) + "\n")
    return by_label


def main() -> None:
    by_label = update_files()
    print("File normalized:", {k or '""': len(v) for k, v in sorted(by_label.items())})
    s = get_settings()
    client = QdrantClient(url=s.qdrant_url.replace("localhost", "127.0.0.1"), timeout=30)
    coll = s.qdrant_collection
    for label, ids in by_label.items():
        client.set_payload(coll, payload={"bac_dao_tao": label}, points=[make_point_id(i) for i in ids], wait=True)
    client.create_payload_index(coll, field_name="bac_dao_tao", field_schema=models.PayloadSchemaType.KEYWORD)
    # Kiem lai tren Qdrant
    counts: Counter = Counter()
    offset = None
    while True:
        pts, offset = client.scroll(coll, limit=256, offset=offset, with_payload=["bac_dao_tao"], with_vectors=False)
        counts.update((p.payload or {}).get("bac_dao_tao", "<thiếu>") for p in pts)
        if offset is None:
            break
    print("Qdrant:", {k or '""': v for k, v in sorted(counts.items())})
    if counts.get("<thiếu>"):
        sys.exit("Còn điểm thiếu bac_dao_tao")


if __name__ == "__main__":
    main()
