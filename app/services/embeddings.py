"""Embedding backends: OpenAI or local (sin cuota API)."""

import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

from openai import OpenAI, RateLimitError

from app.config import Settings, get_settings


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class OpenAIBackend(EmbeddingBackend):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)

    @property
    def dimension(self) -> int:
        return 1536

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        batch_size = self.settings.batch_size
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            chunk = texts[start : start + batch_size]
            for attempt in range(5):
                try:
                    response = self.client.embeddings.create(
                        model=self.settings.embedding_model,
                        input=chunk,
                    )
                    vectors.extend(item.embedding for item in response.data)
                    break
                except RateLimitError as e:
                    if "insufficient_quota" in str(e).lower():
                        raise RuntimeError(
                            "Cuota OpenAI agotada. Opciones: (1) recargar créditos en "
                            "platform.openai.com, o (2) usar EMBEDDING_PROVIDER=local en .env "
                            "y volver a ejecutar embed."
                        ) from e
                    wait = 2**attempt
                    time.sleep(wait)
        return vectors


class LocalBackend(EmbeddingBackend):
    """Modelo multilingüe local — no requiere API key."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
        return self._model

    @property
    def dimension(self) -> int:
        return 384

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        return [vec.tolist() for vec in model.embed(texts)]


def get_embedding_backend(settings: Settings | None = None) -> EmbeddingBackend:
    settings = settings or get_settings()
    if settings.embedding_provider == "local":
        return LocalBackend(settings)
    return OpenAIBackend(settings)


class EmbeddingService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.backend = get_embedding_backend(self.settings)
        self.cache_path = Path(self.settings.data_processed_path) / "embedding_cache.json"
        self._cache: dict[str, list[float]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache), encoding="utf-8")

    def embed_text(self, text: str, cache_key: str | None = None) -> list[float]:
        key = cache_key or text[:200]
        if key in self._cache:
            return self._cache[key]
        vector = self.backend.embed_batch([text])[0]
        self._cache[key] = vector
        self._save_cache()
        return vector

    def embed_batch(self, texts: list[str], cache_keys: list[str] | None = None) -> list[list[float]]:
        keys = cache_keys or [t[:200] for t in texts]
        results: list[list[float] | None] = [None] * len(texts)
        to_fetch_indices: list[int] = []
        to_fetch_texts: list[str] = []

        for i, key in enumerate(keys):
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                to_fetch_indices.append(i)
                to_fetch_texts.append(texts[i])

        if to_fetch_texts:
            batch_size = self.settings.batch_size
            for start in range(0, len(to_fetch_texts), batch_size):
                chunk_indices = to_fetch_indices[start : start + batch_size]
                chunk_texts = to_fetch_texts[start : start + batch_size]
                vectors = self.backend.embed_batch(chunk_texts)
                for idx, vector in zip(chunk_indices, vectors):
                    results[idx] = vector
                    self._cache[keys[idx]] = vector
                self._save_cache()

        if any(r is None for r in results):
            raise RuntimeError("Error interno: embeddings incompletos tras embed_batch")
        return results  # type: ignore[return-value]
