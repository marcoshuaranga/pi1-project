"""HU09 — trazabilidad N:1 del artículo hacia sus tickets fuente."""

import pytest

from pi_core.config import Settings
from pi_core.fixtures.kyocera_demo import build_demo_articulo
from pi_core.storage.kedb_store.store import KedbStore


@pytest.fixture
def store(monkeypatch, tmp_path):
    (tmp_path / "articles").mkdir()
    s = KedbStore(
        Settings(kedb_db_path=str(tmp_path / "k.db"), kedb_docs_path=str(tmp_path / "articles"))
    )
    monkeypatch.setattr("pi_api.routers.kedb.get_store", lambda: s)
    return s


def test_articulo_con_n_tickets_fuente_los_lista_todos(api_client, store):  # CA1
    fuentes = [f"SRC-{i:03d}" for i in range(7)]
    store.create(build_demo_articulo(ticket_ids=fuentes, articulo_id="KEDB-N"))

    r = api_client.get("/kedb/articulos/KEDB-N")

    assert r.status_code == 200
    assert r.json()["tickets_fuente"] == fuentes


def test_articulo_con_un_solo_ticket_fuente_no_falla(api_client, store):  # CA2
    store.create(build_demo_articulo(ticket_ids=["SRC-UNICO"], articulo_id="KEDB-1"))

    detalle = api_client.get("/kedb/articulos/KEDB-1")
    listado = api_client.get("/kedb/articulos")

    assert detalle.status_code == 200
    assert detalle.json()["tickets_fuente"] == ["SRC-UNICO"]
    assert listado.status_code == 200
    assert [a["tickets_fuente"] for a in listado.json()] == [["SRC-UNICO"]]
