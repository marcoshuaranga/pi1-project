"""Validated-KEDB vector search — the one query with real fallback behavior."""

from chromadb.api.models.Collection import Collection


def search_validated_kedb(kedb: Collection, vector: list[float], n_results: int) -> dict:
    """Query validated KEDB articles; falls back to an unfiltered query if the
    backing store doesn't support the estado filter."""
    try:
        return kedb.query(
            query_embeddings=[vector],
            n_results=n_results,
            where={"estado": "validado"},
        )
    except Exception:
        return kedb.query(query_embeddings=[vector], n_results=n_results)
