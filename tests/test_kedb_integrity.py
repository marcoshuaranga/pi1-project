"""tickets_fuente (SQLite) vs. tickets collection (Chroma) integrity audit."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app
from pi_core.config import Settings
from pi_core.fixtures.kyocera_demo import build_demo_articulo
from pi_core.schemas import KedbEstado
from pi_core.services.kedb_integrity import check_all, check_articulo
from pi_core.storage.kedb_store.store import KedbStore


class FakeCollection:
    """Only ids in `existing` are found — everything else is "missing"."""

    def __init__(self, existing: set[str]):
        self.existing = existing

    def get(self, ids=None, include=None):
        found = [tid for tid in (ids or []) if tid in self.existing]
        return {"ids": found}


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        kedb_db_path=str(tmp_path / "integrity.db"),
        kedb_docs_path=str(tmp_path / "articles"),
    )
    (tmp_path / "articles").mkdir()
    return KedbStore(settings)


def test_check_articulo_reports_no_gaps_when_all_tickets_exist():
    articulo = build_demo_articulo(ticket_ids=["1", "2", "3"], articulo_id="KEDB-OK")
    collection = FakeCollection(existing={"1", "2", "3"})

    report = check_articulo(articulo, collection=collection)

    assert report.ok
    assert report.tickets_faltantes == []
    assert report.tickets_fuente_total == 3


def test_check_articulo_reports_missing_tickets():
    articulo = build_demo_articulo(ticket_ids=["1", "2", "3"], articulo_id="KEDB-DRIFT")
    collection = FakeCollection(existing={"1"})  # 2 and 3 no longer in Chroma

    report = check_articulo(articulo, collection=collection)

    assert not report.ok
    assert set(report.tickets_faltantes) == {"2", "3"}


def test_check_all_skips_archivado_by_default(store):
    validado = build_demo_articulo(ticket_ids=["1", "2"], articulo_id="KEDB-V").model_copy(
        update={"estado": KedbEstado.VALIDADO}
    )
    archivado = build_demo_articulo(ticket_ids=["9", "8"], articulo_id="KEDB-A").model_copy(
        update={"estado": KedbEstado.ARCHIVADO}
    )
    store.create(validado)
    store.create(archivado)
    collection = FakeCollection(existing=set())  # nothing exists — everything would fail

    reportes = check_all(store, collection=collection)
    ids_checked = {r.articulo_id for r in reportes}

    assert "KEDB-V" in ids_checked
    assert "KEDB-A" not in ids_checked

    reportes_con_archivados = check_all(store, collection=collection, incluir_archivados=True)
    assert {r.articulo_id for r in reportes_con_archivados} == {"KEDB-V", "KEDB-A"}


def test_integridad_endpoint_reports_articles_with_gaps(monkeypatch, tmp_path):
    from pi_api.routers import kedb as kedb_router

    settings = Settings(
        kedb_db_path=str(tmp_path / "http_integrity.db"),
        kedb_docs_path=str(tmp_path / "http_articles"),
    )
    (tmp_path / "http_articles").mkdir()
    store = KedbStore(settings)
    ok = build_demo_articulo(ticket_ids=["1", "2"], articulo_id="KEDB-OK").model_copy(
        update={"estado": KedbEstado.VALIDADO}
    )
    drifted = build_demo_articulo(ticket_ids=["1", "99"], articulo_id="KEDB-DRIFT").model_copy(
        update={"estado": KedbEstado.VALIDADO}
    )
    store.create(ok)
    store.create(drifted)

    kedb_router.get_store.cache_clear()
    monkeypatch.setattr(kedb_router, "get_store", lambda: store)
    monkeypatch.setattr(
        "pi_core.services.kedb_integrity.get_tickets_collection",
        lambda settings=None: FakeCollection(existing={"1", "2"}),
    )

    client = TestClient(create_app())
    resp = client.get("/kedb/integridad")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_articulos"] == 2
    assert body["con_tickets_faltantes"] == 1
    assert body["detalle"][0]["articulo_id"] == "KEDB-DRIFT"
    assert body["detalle"][0]["tickets_faltantes"] == ["99"]
