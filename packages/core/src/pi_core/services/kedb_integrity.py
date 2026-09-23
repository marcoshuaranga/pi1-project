"""Traceability integrity check between KEDB articles (SQLite) and their
source tickets (Chroma).

`tickets_fuente` in SQLite is a plain list of ticket IDs with no foreign-key
enforcement against Chroma's `tickets` collection — if that collection is
rebuilt (e.g. re-running `pipeline full`) or a ticket is otherwise removed,
an article's N:1 traceability can silently point at nothing. This is an
on-demand audit, not a write-path guard: it doesn't block generation or
validation, it just reports drift (2026-09 architecture audit finding)."""

from __future__ import annotations

from dataclasses import dataclass, field

from pi_core.config import Settings, get_settings
from pi_core.schemas import KedbArticulo, KedbEstado
from pi_core.storage.kedb_store.store import KedbStore
from pi_core.storage.vector_db.client import get_tickets_collection

_CHECK_BATCH = 200


@dataclass
class ArticuloIntegrity:
    articulo_id: str
    titulo: str
    estado: str
    tickets_fuente_total: int
    tickets_faltantes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.tickets_faltantes


def _existing_ticket_ids(collection, ids: list[str]) -> set[str]:
    found: set[str] = set()
    for i in range(0, len(ids), _CHECK_BATCH):
        batch = ids[i : i + _CHECK_BATCH]
        if not batch:
            continue
        chunk = collection.get(ids=batch, include=[])
        found.update(str(x) for x in (chunk.get("ids") or []))
    return found


def check_articulo(articulo: KedbArticulo, collection=None, settings: Settings | None = None) -> ArticuloIntegrity:
    """Check one article's tickets_fuente against the Chroma tickets collection."""
    collection = collection if collection is not None else get_tickets_collection(settings or get_settings())
    existing = _existing_ticket_ids(collection, articulo.tickets_fuente)
    faltantes = [tid for tid in articulo.tickets_fuente if tid not in existing]
    return ArticuloIntegrity(
        articulo_id=articulo.articulo_id,
        titulo=articulo.titulo,
        estado=articulo.estado.value,
        tickets_fuente_total=len(articulo.tickets_fuente),
        tickets_faltantes=faltantes,
    )


def check_all(
    store: KedbStore,
    collection=None,
    settings: Settings | None = None,
    incluir_archivados: bool = False,
) -> list[ArticuloIntegrity]:
    """Check every KEDB article's traceability (skips archivado by default —
    it's a terminal/retired state where drift is expected and not actionable)."""
    settings = settings or get_settings()
    collection = collection if collection is not None else get_tickets_collection(settings)
    articulos = store.list_all()
    if not incluir_archivados:
        articulos = [a for a in articulos if a.estado != KedbEstado.ARCHIVADO]
    return [check_articulo(a, collection=collection, settings=settings) for a in articulos]
