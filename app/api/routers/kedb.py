"""KEDB endpoints (HU08a/b, HU10, HU14, HU16, HU17)."""

import asyncio
import contextlib
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.agents.rag.agent import RAGAgent
from app.api.deps import get_kedb_store as get_store
from app.jobs.redis import get_redis_pool
from app.schemas import JobEnqueueResponse, KedbArticulo, KedbArticuloUpdate, KedbEstado
from app.services.kedb_publisher import KedbPublisher
from app.storage.kedb_store.store import InvalidEstadoTransition

router = APIRouter(prefix="/kedb", tags=["kedb"])


@lru_cache
def get_rag() -> RAGAgent:
    return RAGAgent()


def get_publisher() -> KedbPublisher:
    return KedbPublisher(get_store(), get_rag())


@router.post("/generate", response_model=JobEnqueueResponse, status_code=202)
async def generate_kedb(max_articles: int = 50, keyword: str | None = None):
    """HU08a + HU08b — enqueue clustering + LLM synthesis on the ARQ worker."""
    redis = await get_redis_pool()
    job = await redis.enqueue_job(
        "generate_kedb",
        max_articles=max_articles,
        keyword=keyword,
    )
    if job is None:
        raise HTTPException(status_code=409, detail="No se pudo encolar el job (id duplicado)")
    return JSONResponse(
        status_code=202,
        content=JobEnqueueResponse(
            job_id=job.job_id,
            status="queued",
            task="generate_kedb",
        ).model_dump(),
    )


@router.get("/articulos", response_model=list[KedbArticulo])
async def list_articulos(
    estado: KedbEstado | None = None,
    categoria: str | None = None,
):
    """HU17 — list articles with optional filters."""
    return get_store().list_all(estado=estado, categoria=categoria)


@router.get("/articulos/{articulo_id}", response_model=KedbArticulo)
async def get_articulo(articulo_id: str):
    """HU09 — article detail with source tickets."""
    articulo = get_store().get(articulo_id)
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return articulo


@router.patch("/articulos/{articulo_id}", response_model=KedbArticulo)
async def update_articulo(articulo_id: str, body: KedbArticuloUpdate):
    """HU10 — approve / edit / reject article."""
    try:
        articulo = get_store().update(articulo_id, body)
    except InvalidEstadoTransition as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    await asyncio.to_thread(get_publisher().publish, articulo)
    return articulo


@router.patch("/articulos/{articulo_id}/ciclo-vida", response_model=KedbArticulo)
async def ciclo_vida(articulo_id: str, estado: KedbEstado = KedbEstado.ARCHIVADO):
    """HU17 — lifecycle state change."""
    return await update_articulo(articulo_id, KedbArticuloUpdate(estado=estado))


@router.get("/pendientes", response_model=list[KedbArticulo])
async def pendientes():
    """HU14 — pending validation articles."""
    return get_store().pendientes()


@router.post("/seed-demo", response_model=KedbArticulo)
async def seed_demo():
    """Idempotent Kyocera demo article (DEMO.md Escena 2): one clean borrador.

    Also reindexes the Kyocera ticket cluster with enriched resolutions so
    Escena 1 Top-5 is demo-ready without re-running the full embed pipeline.
    """
    from app.fixtures.kyocera_demo import ensure_clean_demo_articulo
    from app.pipeline.enrich.reindex import reindex_kyocera_cluster

    articulo, _removed = ensure_clean_demo_articulo(get_store(), refresh_fixture=True)
    # Seed must still return the KEDB borrador if Chroma/embeddings are down.
    with contextlib.suppress(Exception):
        await asyncio.to_thread(reindex_kyocera_cluster, ticket_ids=list(articulo.tickets_fuente))
    return articulo


@router.post("/export-docs")
async def export_docs(solo_validados: bool = True):
    """Publish Markdown live-docs from SQLite (default: only validated)."""
    count = get_store().export_all_markdown(solo_validados=solo_validados)
    return {
        "exported": count,
        "solo_validados": solo_validados,
        "path": "/data/kedb/articles",
    }


@router.get("/docs")
async def list_docs(estado: str | None = "validado"):
    """List Markdown live-docs (default: validated only)."""
    from app.storage.kedb_store.markdown import list_markdown_docs

    docs = list_markdown_docs()
    if estado and estado != "todos":
        docs = [d for d in docs if d.get("estado") == estado]
    return docs


@router.get("/docs/{articulo_id}")
async def get_doc(articulo_id: str):
    """Return Markdown content for a published KEDB article."""
    from app.storage.kedb_store.markdown import read_markdown

    store = get_store()
    content = read_markdown(articulo_id, store.settings)
    if content is None:
        articulo = store.get(articulo_id)
        if not articulo or articulo.estado != KedbEstado.VALIDADO:
            raise HTTPException(status_code=404, detail="Documento no publicado")
        # publish_markdown re-checks estado itself — kept here only to 404
        # instead of silently returning nothing for a non-validated article.
        store.publish_markdown(articulo)
        content = read_markdown(articulo_id, store.settings)
    return {"articulo_id": articulo_id, "markdown": content}


@router.get("/buscar")
async def buscar_kedb(q: str = Query(..., min_length=2)):
    """HU16 — semantic search on KEDB."""
    results = await asyncio.to_thread(get_rag().search_kedb, q)
    return {"query": q, "results": [r.model_dump() for r in results]}


@router.get("/integridad")
async def integridad(incluir_archivados: bool = False):
    """Audita tickets_fuente (SQLite) contra la colección de tickets en Chroma.

    Diagnóstico de solo lectura — no bloquea generación ni validación."""
    from app.services.kedb_integrity import check_all

    reportes = await asyncio.to_thread(
        check_all, get_store(), incluir_archivados=incluir_archivados
    )
    con_problemas = [r for r in reportes if not r.ok]
    return {
        "total_articulos": len(reportes),
        "con_tickets_faltantes": len(con_problemas),
        "detalle": [
            {
                "articulo_id": r.articulo_id,
                "titulo": r.titulo,
                "estado": r.estado,
                "tickets_fuente_total": r.tickets_fuente_total,
                "tickets_faltantes": r.tickets_faltantes,
            }
            for r in con_problemas
        ],
    }
