"""Markdown live-docs projection: one 'validated only' rule, exercised from
every writer that used to reimplement it independently."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app
from pi_core.config import Settings
from pi_core.fixtures.kyocera_demo import build_demo_articulo
from pi_core.schemas import KedbEstado
from pi_core.storage.kedb_store.markdown import list_markdown_docs, read_markdown, write_markdown
from pi_core.storage.kedb_store.store import KedbStore


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        kedb_db_path=str(tmp_path / "md.db"),
        kedb_docs_path=str(tmp_path / "articles"),
    )
    (tmp_path / "articles").mkdir()
    return KedbStore(settings)


def _seed(store: KedbStore, estado: KedbEstado, articulo_id: str, titulo: str = "Título de prueba"):
    articulo = build_demo_articulo(ticket_ids=["1"], articulo_id=articulo_id)
    articulo = articulo.model_copy(update={"estado": estado, "titulo": titulo})
    return store.create(articulo)


def test_list_markdown_docs_reads_titulo_from_frontmatter(store):
    articulo = _seed(store, KedbEstado.VALIDADO, "KEDB-TITLE", titulo="Impresora no responde")
    write_markdown(articulo, store.settings)

    docs = list_markdown_docs(store.settings)

    assert docs[0]["titulo"] == "Impresora no responde"


def test_list_markdown_docs_falls_back_to_heading_for_files_without_frontmatter_titulo(
    store,
):
    from pathlib import Path

    # Simulate a file written before frontmatter carried titulo.
    legacy_text = """---
articulo_id: KEDB-LEGACY
estado: validado
categoria: impresoras
version: 1
fecha_generacion: 2026-01-01T00:00:00
---

# Título desde el encabezado

## Síntoma
n/a
"""
    md_path = Path(store.settings.kedb_docs_path) / "KEDB-LEGACY.md"
    md_path.write_text(legacy_text, encoding="utf-8")

    docs = list_markdown_docs(store.settings)

    assert docs[0]["titulo"] == "Título desde el encabezado"


def test_export_all_markdown_writes_only_validated_articles_by_default(store):
    _seed(store, KedbEstado.VALIDADO, "KEDB-V")
    _seed(store, KedbEstado.BORRADOR, "KEDB-B")

    count = store.export_all_markdown()

    assert count == 1
    assert read_markdown("KEDB-V", store.settings) is not None
    assert read_markdown("KEDB-B", store.settings) is None


def test_export_all_markdown_with_solo_validados_false_writes_every_estado(store):
    _seed(store, KedbEstado.VALIDADO, "KEDB-V2")
    _seed(store, KedbEstado.BORRADOR, "KEDB-B2")

    count = store.export_all_markdown(solo_validados=False)

    assert count == 2
    assert read_markdown("KEDB-V2", store.settings) is not None
    assert read_markdown("KEDB-B2", store.settings) is not None


def test_publish_markdown_is_a_noop_for_non_validated_articles(store):
    articulo = _seed(store, KedbEstado.BORRADOR, "KEDB-DRAFT")

    store.publish_markdown(articulo)

    assert read_markdown("KEDB-DRAFT", store.settings) is None


def test_get_doc_lazily_materializes_through_store_publish_markdown(monkeypatch, store):
    from pi_api.routers import kedb as kedb_router

    articulo = _seed(store, KedbEstado.VALIDADO, "KEDB-LAZY", titulo="Materializado al vuelo")
    assert read_markdown("KEDB-LAZY", store.settings) is None  # nothing on disk yet

    kedb_router.get_store.cache_clear()
    monkeypatch.setattr(kedb_router, "get_store", lambda: store)

    client = TestClient(create_app())
    resp = client.get(f"/kedb/docs/{articulo.articulo_id}")

    assert resp.status_code == 200
    assert "Materializado al vuelo" in resp.json()["markdown"]
    assert read_markdown("KEDB-LAZY", store.settings) is not None


def test_get_doc_404s_for_non_validated_article_without_writing_it(monkeypatch, store):
    from pi_api.routers import kedb as kedb_router

    articulo = _seed(store, KedbEstado.BORRADOR, "KEDB-DRAFT2")

    kedb_router.get_store.cache_clear()
    monkeypatch.setattr(kedb_router, "get_store", lambda: store)

    client = TestClient(create_app())
    resp = client.get(f"/kedb/docs/{articulo.articulo_id}")

    assert resp.status_code == 404
    assert read_markdown("KEDB-DRAFT2", store.settings) is None
