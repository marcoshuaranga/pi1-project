"""KEDB endpoints (HU08a/b, HU10, HU14, HU16, HU17)."""

import asyncio
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.agents.rag.agent import RAGAgent
from app.jobs.redis import get_redis_pool
from app.schemas import JobEnqueueResponse, KedbArticulo, KedbArticuloUpdate, KedbEstado
from app.storage.kedb_store.store import KedbStore

router = APIRouter(prefix="/kedb", tags=["kedb"])


@lru_cache
def get_store() -> KedbStore:
    return KedbStore()


@lru_cache
def get_rag() -> RAGAgent:
    return RAGAgent()


def _publish_and_index(articulo: KedbArticulo) -> None:
    """Markdown export + Chroma upsert — keep off the API event loop."""
    get_store().publish_markdown(articulo)
    texto = f"{articulo.titulo}\n{articulo.sintoma}\n{articulo.solucion}"
    get_rag().index_articulo(
        articulo.articulo_id,
        texto,
        {
            "titulo": articulo.titulo,
            "solucion": articulo.solucion,
            "categoria": articulo.categoria,
            "estado": "validado",
            "tipo": "kedb",
        },
    )


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
    articulo = get_store().update(articulo_id, body)
    if not articulo:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    if articulo.estado == KedbEstado.VALIDADO:
        await asyncio.to_thread(_publish_and_index, articulo)
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
    """Idempotent Kyocera demo article (DEMO.md Escena 2): one clean borrador."""
    from app.fixtures.kyocera_demo import ensure_clean_demo_articulo

    articulo, _removed = ensure_clean_demo_articulo(get_store(), refresh_fixture=True)
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
    from app.storage.kedb_store.markdown import read_markdown, write_markdown

    content = read_markdown(articulo_id)
    if content is None:
        articulo = get_store().get(articulo_id)
        if not articulo or articulo.estado != KedbEstado.VALIDADO:
            raise HTTPException(status_code=404, detail="Documento no publicado")
        path = write_markdown(articulo)
        content = path.read_text(encoding="utf-8")
    return {"articulo_id": articulo_id, "markdown": content}


@router.get("/buscar")
async def buscar_kedb(q: str = Query(..., min_length=2)):
    """HU16 — semantic search on KEDB."""
    results = await asyncio.to_thread(get_rag().search_kedb, q)
    return {"query": q, "results": [r.model_dump() for r in results]}
