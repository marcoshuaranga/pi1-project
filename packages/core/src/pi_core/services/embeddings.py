"""Embedding backends: OpenAI or local (sin cuota API)."""

import contextlib
import json
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from openai import AzureOpenAI, OpenAI, RateLimitError

from pi_core.config import Settings, get_settings

# Do not load multi-GB pipeline caches into the API process.
_MAX_CACHE_LOAD_BYTES = 32 * 1024 * 1024  # 32 MB
_MAX_MEMORY_ENTRIES = 2048


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
        self.client = self._build_client()

    def _build_client(self):
        return OpenAI(api_key=self.settings.openai_api_key)

    def _model_name(self) -> str:
        return self.settings.embedding_model

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
                        model=self._model_name(),
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


class AzureOpenAIBackend(OpenAIBackend):
    """Same text-embedding-3-small model, served through Azure OpenAI instead of openai.com."""

    def _build_client(self):
        return AzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_version=self.settings.azure_openai_api_version,
        )

    def _model_name(self) -> str:
        # Azure addresses models by deployment name, not the raw model id.
        return self.settings.azure_openai_embedding_deployment or self.settings.embedding_model


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
    if settings.embedding_provider == "azure":
        return AzureOpenAIBackend(settings)
    return OpenAIBackend(settings)


class EmbeddingService:
    """Online embeddings with a small in-memory LRU. Does NOT load pipeline JSON caches."""

    def __init__(self, settings: Settings | None = None, load_disk_cache: bool = False):
        self.settings = settings or get_settings()
        self.backend = get_embedding_backend(self.settings)
        self.cache_path = Path(self.settings.data_processed_path) / "embedding_cache.json"
        self._cache: dict[str, list[float]] = {}
        self._load_disk_cache = load_disk_cache
        if load_disk_cache:
            self._load_cache()

    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        size = self.cache_path.stat().st_size
        if size > _MAX_CACHE_LOAD_BYTES:
            # Pipeline cache can be multi-GB; loading it OOMs the API (seen ~10GB RSS).
            print(
                f"Skipping embedding disk cache ({size / 1e9:.2f} GB > "
                f"{_MAX_CACHE_LOAD_BYTES / 1e6:.0f} MB limit). Using Chroma + live embeds."
            )
            return
        self._cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _save_cache(self) -> None:
        if not self._load_disk_cache:
            return
        if self.cache_path.exists() and self.cache_path.stat().st_size > _MAX_CACHE_LOAD_BYTES:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self._cache), encoding="utf-8")

    def _remember(self, key: str, vector: list[float]) -> None:
        if len(self._cache) >= _MAX_MEMORY_ENTRIES and key not in self._cache:
            # Drop an arbitrary old entry (FIFO-ish via iterator)
            with contextlib.suppress(StopIteration):
                del self._cache[next(iter(self._cache))]
        self._cache[key] = vector

    def embed_text(self, text: str, cache_key: str | None = None) -> list[float]:
        key = cache_key or text[:200]
        if key in self._cache:
            return self._cache[key]
        vector = self.backend.embed_batch([text])[0]
        self._remember(key, vector)
        return vector

    def embed_batch(
        self, texts: list[str], cache_keys: list[str] | None = None
    ) -> list[list[float]]:
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
                for idx, vector in zip(chunk_indices, vectors, strict=False):
                    results[idx] = vector
                    self._remember(keys[idx], vector)
                if self._load_disk_cache:
                    self._save_cache()

        if any(r is None for r in results):
            raise RuntimeError("Error interno: embeddings incompletos tras embed_batch")
        return results  # type: ignore[return-value]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Process-wide singleton for API agents (no multi-GB disk cache)."""
    return EmbeddingService(load_disk_cache=False)
