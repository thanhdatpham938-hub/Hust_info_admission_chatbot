"""Kiem tra moi truong truoc khi embed: file .env, Qdrant (Docker), OpenAI API.

Dung:
    python scripts/check_setup.py            # kiem tra .env + Qdrant (khong ton tien)
    python scripts/check_setup.py --openai   # them 1 lan goi embedding thu (~0,00001 USD)

Khong bao gio in key ra man hinh — chi in do dai va 4 ky tu cuoi de anh doi chieu.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def fail(msg: str, fix: str) -> None:
    print(f"  [LỖI]  {msg}\n         -> {fix}")


def main() -> int:
    errors = 0
    print("1. File .env")
    env = ROOT / ".env"
    if not env.exists():
        fail(".env chưa có", "copy .env.example thành .env rồi điền OPENAI_API_KEY")
        return 1
    load_dotenv(env)
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        fail("OPENAI_API_KEY trống", "điền key vào .env (dòng OPENAI_API_KEY=sk-...)")
        errors += 1
    elif not key.startswith("sk-"):
        fail("OPENAI_API_KEY không bắt đầu bằng 'sk-'", "kiểm tra lại key đã copy đủ chưa")
        errors += 1
    else:
        ok(f"OPENAI_API_KEY có ({len(key)} ký tự, kết thúc ...{key[-4:]})")
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection = os.getenv("QDRANT_COLLECTION", "hust_rag_2026_1")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    ok(f"QDRANT_URL={url}  QDRANT_COLLECTION={collection}  EMBEDDING_MODEL={model}")

    print("2. Qdrant")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=url, timeout=5)
        names = [c.name for c in client.get_collections().collections]
        ok(f"kết nối được {url}; collection hiện có: {names or '(chưa có)'}")
        import httpx  # di kem qdrant-client
        version = httpx.get(url, timeout=5).json().get("version", "?")
        ok(f"phiên bản server Qdrant: {version}")
    except Exception as e:  # noqa: BLE001 — muon in moi loai loi ket noi cho nguoi dung
        fail(f"không kết nối được Qdrant ({type(e).__name__}: {e})",
             "mở Docker Desktop, chạy `docker compose up -d` trong thư mục dự án, "
             "đợi ~10 giây rồi chạy lại")
        errors += 1

    if "--openai" in sys.argv and key:
        print("3. OpenAI embedding (1 lần gọi thử)")
        try:
            from openai import OpenAI
            vec = OpenAI(api_key=key).embeddings.create(model=model, input="Học phí ngành IT1").data[0].embedding
            ok(f"embedding trả về vector {len(vec)} chiều")
        except Exception as e:  # noqa: BLE001
            fail(f"gọi OpenAI lỗi ({type(e).__name__}: {e})",
                 "kiểm tra key còn hạn / tài khoản còn credit / mạng")
            errors += 1

    print("\nSẴN SÀNG" if errors == 0 else f"\nCòn {errors} lỗi cần sửa")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
