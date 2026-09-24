"""Validated-KEDB vector search — the one query with real fallback behavior."""

from chromadb.api.models.Collection import Collection


def _keep_validated(results: dict, n_results: int) -> dict:
    """Filter fallback results locally when the vector store lacks metadata filters."""
    metadatas = results.get("metadatas", [[]])[0]
    keep = [
        index
        for index, metadata in enumerate(metadatas)
        if isinstance(metadata, dict) and metadata.get("estado") == "validado"
    ][:n_results]
    filtered = dict(results)
    for key, values in results.items():
        if isinstance(values, list) and values and isinstance(values[0], list):
            filtered[key] = [[values[0][index] for index in keep]]
    return filtered


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
        fallback = kedb.query(query_embeddings=[vector], n_results=max(n_results * 2, n_results))
        return _keep_validated(fallback, n_results)
