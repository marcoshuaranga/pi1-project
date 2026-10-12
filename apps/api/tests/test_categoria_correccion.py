"""HU03 — corrección de categoría por el Operador."""

import sqlite3

from pi_core.constants import TOP9_CATEGORIES
from pi_core.schemas import TicketResponse

SUGERIDA = TOP9_CATEGORIES[3]
OTRA = TOP9_CATEGORIES[4]


def _ticket(store, ticket_id="T-HU03"):
    store.save_ticket_session(
        TicketResponse(ticket_id=ticket_id, categoria=SUGERIDA, confianza=0.5, prioridad="Media")
    )
    return ticket_id


def _correcciones(store) -> list[sqlite3.Row]:
    with store._conn() as conn:
        return conn.execute("SELECT * FROM categoria_correcciones").fetchall()


def test_correccion_valida_se_registra_y_actualiza_el_ticket(api_client, store_aislado):  # CA1
    tid = _ticket(store_aislado)

    r = api_client.patch(f"/tickets/{tid}/categoria", json={"categoria": OTRA})

    assert r.status_code == 200
    assert r.json() == {"ticket_id": tid, "categoria": OTRA, "cambio": True}
    filas = _correcciones(store_aislado)
    assert len(filas) == 1
    assert (filas[0]["categoria_original"], filas[0]["categoria_corregida"]) == (SUGERIDA, OTRA)
    assert api_client.get(f"/tickets/{tid}").json()["result"]["categoria"] == OTRA


def test_misma_categoria_no_registra_cambio(api_client, store_aislado):  # CA2
    tid = _ticket(store_aislado)

    r = api_client.patch(f"/tickets/{tid}/categoria", json={"categoria": SUGERIDA})

    assert r.status_code == 200
    assert r.json()["cambio"] is False
    assert _correcciones(store_aislado) == []


def test_categoria_fuera_del_top9_se_rechaza(api_client, store_aislado):  # CA3
    tid = _ticket(store_aislado)

    r = api_client.patch(f"/tickets/{tid}/categoria", json={"categoria": "Monitor roto"})

    assert r.status_code == 422
    assert "válida" in r.json()["detail"]
    assert _correcciones(store_aislado) == []
    assert api_client.get(f"/tickets/{tid}").json()["result"]["categoria"] == SUGERIDA


def test_ticket_inexistente_devuelve_404(api_client, store_aislado):
    r = api_client.patch("/tickets/NO-EXISTE/categoria", json={"categoria": OTRA})

    assert r.status_code == 404


def test_catalogo_de_categorias_validas_es_el_top9(api_client):
    r = api_client.get("/tickets/categorias")

    assert r.status_code == 200
    assert r.json() == TOP9_CATEGORIES
