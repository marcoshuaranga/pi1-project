"""KEDB endpoints (HU08a/b, HU10, HU14, HU16, HU17)."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from app.agents.kedb_generator.agent import KedbGeneratorAgent
from app.agents.rag.agent import RAGAgent
from app.schemas import KedbArticulo, KedbArticuloUpdate, KedbEstado
from app.storage.kedb_store.store import KedbStore

router = APIRouter(prefix="/kedb", tags=["kedb"])


@lru_cache
def get_store() -> KedbStore:
    return KedbStore()


@lru_cache
def get_generator() -> KedbGeneratorAgent:
    return KedbGeneratorAgent()


@lru_cache
def get_rag() -> RAGAgent:
    return RAGAgent()


@router.post("/generate")
async def generate_kedb(max_articles: int = 50, keyword: str | None = None):
    """HU08a + HU08b — clustering + LLM synthesis."""
    generator = get_generator()
    if keyword:
        articulo = generator.generate_from_cluster_keyword(keyword)
        if not articulo:
            articulo = generator.generate_demo_fixture()
        return {"generated": 1, "articulos": [articulo.model_dump(mode="json")]}
    articles = generator.generate_all(max_articles=max_articles)
    if not articles:
        demo = generator.generate_demo_fixture()
        articles = [demo]
    return {
        "generated": len(articles),
        "articulos": [a.model_dump(mode="json") for a in articles],
    }


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
        texto = f"{articulo.titulo}\n{articulo.sintoma}\n{articulo.solucion}"
        get_rag().index_articulo(
            articulo_id,
            texto,
            {
                "titulo": articulo.titulo,
                "solucion": articulo.solucion,
                "categoria": articulo.categoria,
                "estado": "validado",
                "tipo": "kedb",
            },
        )
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
    """Create Kyocera demo article without LLM/Chroma (DEMO.md Escena 2)."""
    from datetime import datetime, timezone

    from app.storage.kedb_store.store import new_articulo_id

    articulo = KedbArticulo(
        articulo_id=new_articulo_id(),
        titulo="Configuración de impresora Kyocera TaskAlfa 7003i",
        categoria=(
            "Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional"
        ),
        sintoma=(
            "El usuario no puede imprimir o requiere configurar la impresora "
            "multifuncional Kyocera 7003 en su equipo."
        ),
        causa=(
            "Impresora predeterminada no configurada correctamente, "
            "o driver de la Kyocera 7003 no instalado."
        ),
        solucion=(
            "1. Instalar/verificar el driver de la impresora Kyocera 7003.\n"
            "2. Configurar la impresora como predeterminada.\n"
            "3. Validar con hoja de prueba."
        ),
        tickets_fuente=["96044", "95984", "95645", "95439", "94922"],
        fecha_generacion=datetime.now(timezone.utc),
        estado=KedbEstado.BORRADOR,
        aplicable_a="Impresoras Kyocera TaskAlfa 7003i en sedes MTC",
    )
    return get_store().create(articulo)


@router.post("/export-docs")
async def export_docs():
    """Sync all SQLite articles to Markdown under data/kedb/articles/."""
    count = get_store().export_all_markdown()
    return {"exported": count, "path": "/data/kedb/articles"}


@router.get("/docs")
async def list_docs(estado: str | None = None):
    """List Markdown live-docs files (and optional estado filter from frontmatter)."""
    from app.storage.kedb_store.markdown import list_markdown_docs

    docs = list_markdown_docs()
    if estado:
        docs = [d for d in docs if d.get("estado") == estado]
    return docs


@router.get("/docs/{articulo_id}")
async def get_doc(articulo_id: str):
    """Return Markdown content for a KEDB article."""
    from app.storage.kedb_store.markdown import read_markdown

    content = read_markdown(articulo_id)
    if content is None:
        # Fallback: export from SQLite if article exists but MD missing
        articulo = get_store().get(articulo_id)
        if not articulo:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        from app.storage.kedb_store.markdown import write_markdown

        path = write_markdown(articulo)
        content = path.read_text(encoding="utf-8")
    return {"articulo_id": articulo_id, "markdown": content}


@router.get("/buscar")
async def buscar_kedb(q: str = Query(..., min_length=2)):
    """HU16 — semantic search on KEDB."""
    results = get_rag().search_kedb(q)
    return {"query": q, "results": [r.model_dump() for r in results]}
