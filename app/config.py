"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://web"
    data_processed_path: str = "/data/processed"
    kedb_db_path: str = "/data/kedb/kedb.db"
    kedb_docs_path: str = "/data/kedb/articles"
    chroma_collection_tickets: str = "tickets"
    chroma_collection_kedb: str = "kedb_articles"
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "openai"  # openai | local
    local_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    llm_model: str = "gpt-4o-mini"
    batch_size: int = 100
    random_seed: int = 42
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
