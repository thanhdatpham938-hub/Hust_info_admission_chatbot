"""Cau hinh backend doc tu bien moi truong / file .env o goc du an (PRD muc 23).

Dung get_settings() thay vi bien toan cuc: import module khong doi DATABASE_URL phai co san, nen test
khong can DB (chuan hoa chuoi o Entity Resolution) van chay duoc khi chua co .env.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]       # backend/app/core/config.py -> goc du an


class Settings(BaseSettings):
    # extra="ignore": .env con bien cua docker-compose (POSTGRES_PASSWORD, POSTGRES_PORT) khong thuoc backend
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # 127.0.0.1, khong phai localhost — xem .env.example (localhost thu IPv6 truoc, treo ket noi)
    database_url: str
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "hust_rag_2026_1"
    embedding_model: str = "text-embedding-3-large"
    # SecretStr: in Settings ra log khong lo key
    openai_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
