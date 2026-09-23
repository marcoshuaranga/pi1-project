"""ChromaDB client wrapper."""

from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from pi_core.config import Settings, get_settings


@lru_cache
def _chroma_client(host: str, port: int) -> chromadb.HttpClient:
    return chromadb.HttpClient(host=host, port=port)


@lru_cache
def _tickets_collection(host: str, port: int, name: str) -> Collection:
    return _chroma_client(host, port).get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


@lru_cache
def _kedb_collection(host: str, port: int, name: str) -> Collection:
    return _chroma_client(host, port).get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def get_chroma_client(settings: Settings | None = None) -> chromadb.HttpClient:
    settings = settings or get_settings()
    return _chroma_client(settings.chroma_host, settings.chroma_port)


def get_tickets_collection(settings: Settings | None = None) -> Collection:
    settings = settings or get_settings()
    return _tickets_collection(
        settings.chroma_host, settings.chroma_port, settings.chroma_collection_tickets
    )


def get_kedb_collection(settings: Settings | None = None) -> Collection:
    settings = settings or get_settings()
    return _kedb_collection(
        settings.chroma_host, settings.chroma_port, settings.chroma_collection_kedb
    )
