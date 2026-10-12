"""C5 — RAG agent: Top-K similar solutions from tickets + KEDB."""

import logging

from chromadb.api.models.Collection import Collection

from pi_core.config import Settings, get_settings
from pi_core.schemas import SolucionSugerida
from pi_core.services.embeddings import get_embedding_service
from pi_core.storage.vector_db.client import get_kedb_collection, get_tickets_collection
from pi_core.storage.vector_db.search import search_validated_kedb

logger = logging.getLogger(__name__)

# Se piden más vecinos que top_k porque muchos tickets repiten la misma resolución y se descartan
# al deduplicar por texto; con pocos candidatos el top-K quedaría con menos de K soluciones distintas.
_OVERFETCH = 40


def _clave_solucion(s: SolucionSugerida) -> str | None:
    """Texto de la solución normalizado; None si no tiene (entonces solo se deduplica por id)."""
    return " ".join((s.solucion or "").lower().split()) or None


class RAGAgent:
    def __init__(
        self,
        settings: Settings | None = None,
        top_k: int = 5,
        tickets: Collection | None = None,
        kedb: Collection | None = None,
    ):
        self.settings = settings or get_settings()
        self.embedder = get_embedding_service()
        self.tickets = tickets if tickets is not None else get_tickets_collection(self.settings)
        self.kedb = kedb if kedb is not None else get_kedb_collection(self.settings)
        self.top_k = top_k

    def retrieve(
        self, texto: str, categoria: str | None = None, excluir_ids: set[str] | None = None
    ) -> list[SolucionSugerida]:
        """Top-K soluciones distintas (por id y por texto de solución), de mayor a menor score.

        `excluir_ids` se descarta antes de deduplicar: sirve para evaluar sin contar el propio ticket.
        """
        vector = self.embedder.embed_text(texto, cache_key=f"rag:{texto[:100]}")
        soluciones: list[SolucionSugerida] = []

        # Search tickets
        try:
            ticket_results = self.tickets.query(
                query_embeddings=[vector], n_results=self.top_k * _OVERFETCH
            )
            soluciones.extend(self._parse_results(ticket_results, "ticket"))
        except Exception:
            logger.exception("Chroma query falló en colección de tickets")

        # Search validated KEDB articles
        try:
            kedb_results = search_validated_kedb(self.kedb, vector, self.top_k)
            soluciones.extend(self._parse_results(kedb_results, "kedb"))
        except Exception:
            logger.exception("Chroma query falló en colección KEDB")

        soluciones.sort(key=lambda s: s.score, reverse=True)
        seen_ids: set[str] = set(excluir_ids or ())
        seen_texts: set[str] = set()
        unique: list[SolucionSugerida] = []
        for s in soluciones:
            clave = _clave_solucion(s)
            if s.articulo_o_ticket_id in seen_ids or (clave is not None and clave in seen_texts):
                continue
            seen_ids.add(s.articulo_o_ticket_id)
            if clave is not None:
                seen_texts.add(clave)
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
                    categoria=meta.get("categoria"),
                )
            )
        return out

    def search_kedb(self, query: str, top_k: int = 10) -> list[SolucionSugerida]:
        vector = self.embedder.embed_text(query, cache_key=f"search:{query[:100]}")
        try:
            results = search_validated_kedb(self.kedb, vector, top_k)
            parsed = self._parse_results(results, "kedb")
        except Exception:
            logger.exception("Búsqueda KEDB falló")
            parsed = []
        return parsed

    def remove_articulo(self, articulo_id: str) -> None:
        self.kedb.delete(ids=[articulo_id])

    def index_articulo(self, articulo_id: str, texto: str, metadata: dict) -> None:
        vector = self.embedder.embed_text(texto, cache_key=articulo_id)
        self.kedb.upsert(
            ids=[articulo_id],
            embeddings=[vector],
            documents=[texto],
            metadatas=[metadata],
        )
