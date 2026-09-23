"""Publish validated KEDB articles to their read projections."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from pi_core.agents.rag.agent import RAGAgent
from pi_core.schemas import KedbArticulo, KedbEstado
from pi_core.storage.kedb_store.store import KedbStore


@dataclass(frozen=True)
class KedbPublication:
    """Validated article payload shared by all read projections."""

    _article: KedbArticulo
    text: str
    metadata: Mapping[str, str]

    @property
    def article(self) -> KedbArticulo:
        return self._article.model_copy(deep=True)

    @classmethod
    def from_article(cls, articulo: KedbArticulo) -> "KedbPublication":
        if articulo.estado != KedbEstado.VALIDADO:
            raise ValueError("Only validated articles can be published")
        article = articulo.model_copy(deep=True)
        return cls(
            _article=article,
            text=f"{article.titulo}\n{article.sintoma}\n{article.solucion}",
            metadata=MappingProxyType(
                {
                    "titulo": article.titulo,
                    "solucion": article.solucion,
                    "categoria": article.categoria,
                    "estado": KedbEstado.VALIDADO.value,
                    "tipo": "kedb",
                }
            ),
        )


class KedbPublicationError(RuntimeError):
    """Report which projections completed before publication failed."""

    def __init__(self, failed_projection: str, completed_projections: tuple[str, ...]):
        self.failed_projection = failed_projection
        self.completed_projections = completed_projections
        completed = ", ".join(completed_projections) or "none"
        super().__init__(f"KEDB publication failed in {failed_projection}; completed: {completed}")


class _Projection(Protocol):
    def publish(self, publication: KedbPublication) -> None: ...


class _MarkdownProjection:
    def __init__(self, store: KedbStore):
        self.store = store

    def publish(self, publication: KedbPublication) -> None:
        self.store.publish_markdown(publication.article)


class _VectorProjection:
    def __init__(self, rag: RAGAgent):
        self.rag = rag

    def publish(self, publication: KedbPublication) -> None:
        self.rag.index_articulo(
            publication.article.articulo_id,
            publication.text,
            dict(publication.metadata),
        )


class KedbPublisher:
    """Coordinate validated KEDB publication across its read projections."""

    def __init__(self, store: KedbStore, rag: RAGAgent):
        self.projections: tuple[tuple[str, _Projection], ...] = (
            ("markdown", _MarkdownProjection(store)),
            ("vector", _VectorProjection(rag)),
        )

    def publish(self, articulo: KedbArticulo) -> None:
        if articulo.estado != KedbEstado.VALIDADO:
            return

        publication = KedbPublication.from_article(articulo)
        completed: list[str] = []
        for name, projection in self.projections:
            try:
                projection.publish(publication)
            except Exception as exc:
                raise KedbPublicationError(name, tuple(completed)) from exc
            completed.append(name)
