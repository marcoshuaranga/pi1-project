"""Publish validated KEDB articles to their read projections."""

from app.agents.rag.agent import RAGAgent
from app.schemas import KedbArticulo, KedbEstado
from app.storage.kedb_store.store import KedbStore


class KedbPublisher:
    """Coordinate Markdown and vector-db publication for one KEDB article."""

    def __init__(self, store: KedbStore, rag: RAGAgent):
        self.store = store
        self.rag = rag

    def publish(self, articulo: KedbArticulo) -> None:
        if articulo.estado != KedbEstado.VALIDADO:
            return

        self.store.publish_markdown(articulo)
        texto = f"{articulo.titulo}\n{articulo.sintoma}\n{articulo.solucion}"
        self.rag.index_articulo(
            articulo.articulo_id,
            texto,
            {
                "titulo": articulo.titulo,
                "solucion": articulo.solucion,
                "categoria": articulo.categoria,
                "estado": KedbEstado.VALIDADO.value,
                "tipo": "kedb",
            },
        )