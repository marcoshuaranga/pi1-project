"""HU10's human validation gate enforced server-side (KedbStore.update FSM)."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app
from pi_core.config import Settings
from pi_core.fixtures.kyocera_demo import build_demo_articulo
from pi_core.schemas import KedbArticuloUpdate, KedbEstado
from pi_core.storage.kedb_store.store import InvalidEstadoTransition, KedbStore


@pytest.fixture
def store(tmp_path):
    settings = Settings(
        kedb_db_path=str(tmp_path / "fsm.db"),
        kedb_docs_path=str(tmp_path / "articles"),
    )
    (tmp_path / "articles").mkdir()
    return KedbStore(settings)


def _seed(store: KedbStore, estado: KedbEstado, articulo_id: str) -> None:
    articulo = build_demo_articulo(ticket_ids=["1", "2", "3", "4", "5"], articulo_id=articulo_id)
    articulo = articulo.model_copy(update={"estado": estado})
    store.create(articulo)


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (KedbEstado.BORRADOR, KedbEstado.VALIDADO),
        (KedbEstado.BORRADOR, KedbEstado.OBSOLETO),
        (KedbEstado.VALIDADO, KedbEstado.OBSOLETO),
        (KedbEstado.VALIDADO, KedbEstado.ARCHIVADO),
        (KedbEstado.OBSOLETO, KedbEstado.ARCHIVADO),
        (KedbEstado.BORRADOR, KedbEstado.BORRADOR),
        (KedbEstado.VALIDADO, KedbEstado.VALIDADO),
    ],
)
def test_allowed_transitions_succeed(store, origen, destino):
    _seed(store, origen, "KEDB-OK")
    updated = store.update("KEDB-OK", KedbArticuloUpdate(estado=destino))
    assert updated.estado == destino


@pytest.mark.parametrize(
    ("origen", "destino"),
    [
        (KedbEstado.VALIDADO, KedbEstado.BORRADOR),
        (KedbEstado.OBSOLETO, KedbEstado.BORRADOR),
        (KedbEstado.OBSOLETO, KedbEstado.VALIDADO),
        (KedbEstado.ARCHIVADO, KedbEstado.VALIDADO),
        (KedbEstado.ARCHIVADO, KedbEstado.BORRADOR),
        (KedbEstado.ARCHIVADO, KedbEstado.OBSOLETO),
        (KedbEstado.BORRADOR, KedbEstado.ARCHIVADO),
    ],
)
def test_disallowed_transitions_raise(store, origen, destino):
    _seed(store, origen, "KEDB-BAD")
    with pytest.raises(InvalidEstadoTransition):
        store.update("KEDB-BAD", KedbArticuloUpdate(estado=destino))
    # rejected transition must not have mutated the stored state
    assert store.get("KEDB-BAD").estado == origen


def test_editing_content_without_estado_is_unaffected_by_fsm(store):
    _seed(store, KedbEstado.VALIDADO, "KEDB-EDIT")
    updated = store.update("KEDB-EDIT", KedbArticuloUpdate(titulo="Nuevo título"))
    assert updated.titulo == "Nuevo título"
    assert updated.estado == KedbEstado.VALIDADO


def test_patch_endpoint_returns_409_on_invalid_transition(monkeypatch, tmp_path):
    from pi_api.routers import kedb as kedb_router

    settings = Settings(
        kedb_db_path=str(tmp_path / "http_fsm.db"),
        kedb_docs_path=str(tmp_path / "http_articles"),
    )
    (tmp_path / "http_articles").mkdir()
    store = KedbStore(settings)
    _seed(store, KedbEstado.ARCHIVADO, "KEDB-HTTP")

    kedb_router.get_store.cache_clear()
    monkeypatch.setattr(kedb_router, "get_store", lambda: store)

    client = TestClient(create_app())
    resp = client.patch("/kedb/articulos/KEDB-HTTP", json={"estado": "validado"})

    assert resp.status_code == 409
    assert "archivado" in resp.json()["detail"]
    assert "validado" in resp.json()["detail"]
