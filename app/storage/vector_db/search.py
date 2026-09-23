"""Vector search adapter used by RAG retrieval."""

from chromadb.api.models.Collection import Collection


class VectorSearchAdapter:
    """Own collection queries and KEDB filter fallback behavior."""

    def __init__(self, tickets: Collection, kedb: Collection):
        self.tickets = tickets
        self.kedb = kedb

    def search_tickets(self, vector: list[float], n_results: int) -> dict:
        return self.tickets.query(query_embeddings=[vector], n_results=n_results)

    def search_kedb(self, vector: list[float], n_results: int) -> dict:
        return self.kedb.query(query_embeddings=[vector], n_results=n_results)

    def search_validated_kedb(self, vector: list[float], n_results: int) -> dict:
        try:
            return self.kedb.query(
                query_embeddings=[vector],
                n_results=n_results,
                where={"estado": "validado"},
            )
        except Exception:
            return self.kedb.query(query_embeddings=[vector], n_results=n_results)

    def index_kedb(self, articulo_id: str, vector: list[float], texto: str, metadata: dict) -> None:
        self.kedb.upsert(
            ids=[articulo_id],
            embeddings=[vector],
            documents=[texto],
            metadatas=[metadata],
        )
