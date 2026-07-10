"""ChromaDB client wrapper."""

import chromadb
from chromadb.api.models.Collection import Collection

from app.config import Settings, get_settings


def get_chroma_client(settings: Settings | None = None) -> chromadb.HttpClient:
    settings = settings or get_settings()
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_tickets_collection(settings: Settings | None = None) -> Collection:
    settings = settings or get_settings()
    client = get_chroma_client(settings)
    return client.get_or_create_collection(
        name=settings.chroma_collection_tickets,
        metadata={"hnsw:space": "cosine"},
    )


def get_kedb_collection(settings: Settings | None = None) -> Collection:
    settings = settings or get_settings()
    client = get_chroma_client(settings)
    return client.get_or_create_collection(
        name=settings.chroma_collection_kedb,
        metadata={"hnsw:space": "cosine"},
    )
