"""Upsert enriched ticket resolutions into the tickets Chroma collection."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from app.config import Settings, get_settings
from app.pipeline.enrich.resolutions import SOLUCION_META_MAX, enrich_resolution
from app.services.embeddings import get_embedding_service
from app.storage.vector_db.client import get_tickets_collection

logger = logging.getLogger(__name__)

CACHE_SUFFIX = "enrich-v1"


def reindex_ticket_resolutions(
    tickets: Iterable[dict],
    *,
    settings: Settings | None = None,
    force: bool = True,
) -> int:
    """Embed + upsert tickets with enriched `solucion` metadata/documents.

    Each item: ticket_id, titulo, solucion (optional), categoria (optional).
    """
    settings = settings or get_settings()
    col = get_tickets_collection(settings)
    embedder = get_embedding_service()

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    cache_keys: list[str] = []

    for t in tickets:
        tid = str(t.get("ticket_id") or "").strip()
        if not tid:
            continue
        titulo = str(t.get("titulo") or t.get("titulo_anon") or "")
        categoria = str(t.get("categoria") or t.get("categoria_top9") or "")
        original = t.get("solucion") or t.get("solucion_anon") or ""
        result = enrich_resolution(
            titulo=titulo,
            solucion=str(original) if original is not None else "",
            categoria=categoria,
            ticket_id=tid,
            force=force,
        )
        solucion = result.solucion[:SOLUCION_META_MAX]
        doc = f"{titulo}\n{solucion}".strip()
        ids.append(tid)
        documents.append(doc)
        cache_keys.append(f"{tid}:{CACHE_SUFFIX}" if result.enriched else tid)
        metadatas.append(
            {
                "categoria": categoria[:500],
                "split": str(t.get("split") or "train"),
                "titulo": titulo[:500],
                "solucion": solucion,
                "tipo": "ticket",
                "enriched": "true" if result.enriched else "false",
                "enrich_domain": result.domain or "",
            }
        )

    if not ids:
        return 0

    total = 0
    batch_size = settings.batch_size
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        batch_keys = cache_keys[i : i + batch_size]
        vectors = embedder.embed_batch(batch_docs, cache_keys=batch_keys)
        col.upsert(
            ids=batch_ids,
            embeddings=vectors,
            documents=batch_docs,
            metadatas=batch_meta,
        )
        total += len(batch_ids)

    logger.info("Reindexadas %s resoluciones enriquecidas en Chroma tickets", total)
    return total


def reindex_kyocera_cluster(
    *,
    settings: Settings | None = None,
    ticket_ids: list[str] | None = None,
) -> int:
    """Ensure the Kyocera demo cluster has rich indexed resolutions (Escena 1)."""
    from app.fixtures.kyocera_demo import CLUSTER_TITLE, load_kyocera_ticket_ids

    settings = settings or get_settings()
    ids = ticket_ids if ticket_ids is not None else load_kyocera_ticket_ids()
    col = get_tickets_collection(settings)

    existing_meta: dict[str, dict] = {}
    try:
        # Chroma get in chunks to avoid huge payloads
        chunk = 100
        for i in range(0, len(ids), chunk):
            part = ids[i : i + chunk]
            got = col.get(ids=part, include=["metadatas"])
            for tid, meta in zip(got.get("ids") or [], got.get("metadatas") or [], strict=False):
                if meta:
                    existing_meta[str(tid)] = meta
    except Exception:
        logger.exception("No se pudo leer metadatos Kyocera previos; se indexa desde fixture")

    tickets = []
    for tid in ids:
        meta = existing_meta.get(str(tid), {})
        tickets.append(
            {
                "ticket_id": str(tid),
                "titulo": meta.get("titulo") or CLUSTER_TITLE,
                "solucion": meta.get("solucion") or "",
                "categoria": meta.get("categoria")
                or (
                    "Equipos Informáticos > Equipo de impresión y escaneo > "
                    "Impresora Multifuncional"
                ),
                "split": meta.get("split") or "train",
            }
        )

    return reindex_ticket_resolutions(tickets, settings=settings, force=True)
