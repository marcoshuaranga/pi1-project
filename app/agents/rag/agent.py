"""C5 — RAG agent: Top-K similar solutions from tickets + KEDB."""

import logging

from app.config import Settings, get_settings
from app.schemas import SolucionSugerida
from app.services.embeddings import get_embedding_service
from app.storage.vector_db.client import get_kedb_collection, get_tickets_collection
from app.storage.vector_db.search import VectorSearchAdapter

logger = logging.getLogger(__name__)


class RAGAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        top_k: int = 5,
        vector_search: VectorSearchAdapter | None = None,
    ):
        self.settings = settings or get_settings()
        self.embedder = get_embedding_service()
        if vector_search is None:
            tickets_col = get_tickets_collection(self.settings)
            kedb_col = get_kedb_collection(self.settings)
            vector_search = VectorSearchAdapter(tickets_col, kedb_col)
        self.vector_search = vector_search
        self.top_k = top_k

    def retrieve(self, texto: str, categoria: str | None = None) -> list[SolucionSugerida]:
        vector = self.embedder.embed_text(texto, cache_key=f"rag:{texto[:100]}")
        soluciones: list[SolucionSugerida] = []

        # Search tickets
        try:
            ticket_results = self.vector_search.search_tickets(vector, self.top_k * 2)
            soluciones.extend(self._parse_results(ticket_results, "ticket"))
        except Exception:
            logger.exception("Chroma query falló en colección de tickets")

        # Search validated KEDB articles
        try:
            kedb_results = self.vector_search.search_validated_kedb(vector, self.top_k)
            soluciones.extend(self._parse_results(kedb_results, "kedb"))
        except Exception:
            logger.exception("Chroma query falló en colección KEDB")

        soluciones.sort(key=lambda s: s.score, reverse=True)
        seen = set()
        unique: list[SolucionSugerida] = []
        for s in soluciones:
            if s.articulo_o_ticket_id not in seen:
                seen.add(s.articulo_o_ticket_id)
                unique.append(s)
            if len(unique) >= self.top_k:
                break
        return unique

    def _parse_results(self, results: dict, tipo: str) -> list[SolucionSugerida]:
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        out = []
        for doc_id, dist, meta in zip(ids, distances, metadatas, strict=False):
            score = round(1.0 - dist, 3)
            out.append(
                SolucionSugerida(
                    articulo_o_ticket_id=doc_id,
                    score=score,
                    tipo=tipo,
                    titulo=meta.get("titulo"),
                    solucion=meta.get("solucion"),
                )
            )
        return out

    def search_kedb(self, query: str, top_k: int = 10) -> list[SolucionSugerida]:
        vector = self.embedder.embed_text(query, cache_key=f"search:{query[:100]}")
        try:
            results = self.vector_search.search_kedb(vector, top_k)
            parsed = self._parse_results(results, "kedb")
        except Exception:
            logger.exception("Búsqueda KEDB falló")
            parsed = []
        return parsed

    def index_articulo(self, articulo_id: str, texto: str, metadata: dict) -> None:
        vector = self.embedder.embed_text(texto, cache_key=articulo_id)
        self.vector_search.index_kedb(articulo_id, vector, texto, metadata)
