"""C5 — RAG agent: Top-K similar solutions from tickets + KEDB."""

import logging

from app.config import Settings, get_settings
from app.schemas import SolucionSugerida
from app.services.embeddings import get_embedding_service
from app.storage.vector_db.client import get_kedb_collection, get_tickets_collection

logger = logging.getLogger(__name__)


class RAGAgent:
    def __init__(self, settings: Settings | None = None, top_k: int = 5):
        self.settings = settings or get_settings()
        self.embedder = get_embedding_service()
        self.tickets_col = get_tickets_collection(self.settings)
        self.kedb_col = get_kedb_collection(self.settings)
        self.top_k = top_k

    def retrieve(self, texto: str, categoria: str | None = None) -> list[SolucionSugerida]:
        vector = self.embedder.embed_text(texto, cache_key=f"rag:{texto[:100]}")
        soluciones: list[SolucionSugerida] = []

        # Search tickets
        try:
            ticket_results = self.tickets_col.query(
                query_embeddings=[vector],
                n_results=self.top_k * 2,
            )
            soluciones.extend(self._parse_results(ticket_results, "ticket"))
        except Exception:
            logger.exception("Chroma query falló en colección de tickets")

        # Search validated KEDB articles
        try:
            kedb_results = self.kedb_col.query(
                query_embeddings=[vector],
                n_results=self.top_k,
                where={"estado": "validado"},
            )
            soluciones.extend(self._parse_results(kedb_results, "kedb"))
        except Exception:
            logger.debug("Filtro estado=validado no disponible; reintento sin where", exc_info=True)
            try:
                kedb_results = self.kedb_col.query(
                    query_embeddings=[vector],
                    n_results=self.top_k,
                )
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
        for doc_id, dist, meta in zip(ids, distances, metadatas):
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
        old_k = self.top_k
        self.top_k = top_k
        vector = self.embedder.embed_text(query, cache_key=f"search:{query[:100]}")
        try:
            results = self.kedb_col.query(query_embeddings=[vector], n_results=top_k)
            parsed = self._parse_results(results, "kedb")
        except Exception:
            logger.exception("Búsqueda KEDB falló")
            parsed = []
        self.top_k = old_k
        return parsed

    def index_articulo(self, articulo_id: str, texto: str, metadata: dict) -> None:
        vector = self.embedder.embed_text(texto, cache_key=articulo_id)
        self.kedb_col.upsert(
            ids=[articulo_id],
            embeddings=[vector],
            documents=[texto],
            metadatas=[metadata],
        )
