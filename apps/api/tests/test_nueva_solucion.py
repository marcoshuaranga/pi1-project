"""HU12 — nueva solución del Operador como candidata a artículo KEDB."""

import pytest

from pi_core.constants import TOP9_CATEGORIES
from pi_core.schemas import KedbEstado, SolucionSugerida, TicketResponse

CATEGORIA = TOP9_CATEGORIES[0]
SOLUCION = "Reiniciar el servicio de cola de impresión y reinstalar el driver de la Kyocera."


class RagFalso:
    """Mismo contrato que RAGAgent.search_kedb; devuelve los similares configurados."""

    def __init__(self, similares=()):
        self.similares = list(similares)
        self.consultas: list[str] = []

    def search_kedb(self, query, top_k=10):
        self.consultas.append(query)
        return self.similares


def _similar(score):
    return SolucionSugerida(
        articulo_o_ticket_id="KEDB-EXISTENTE", score=score, tipo="kedb", titulo="Impresora Kyocera"
    )


@pytest.fixture
def ticket(store_aislado):
    store_aislado.save_ticket_session(
        TicketResponse(ticket_id="T-HU12", categoria=CATEGORIA, confianza=0.9, prioridad="Media")
    )
    return "T-HU12"


@pytest.fixture
def rag(monkeypatch):
    rag = RagFalso()
    monkeypatch.setattr("pi_api.routers.kedb.get_rag", lambda: rag)
    return rag


def _feedback_rows(store):
    with store._conn() as conn:
        return conn.execute("SELECT * FROM ticket_feedback WHERE nueva_solucion IS NOT NULL").fetchall()


def test_registro_valido_crea_borrador_trazable_al_ticket(api_client, store_aislado, ticket, rag):  # CA1
    r = api_client.post(f"/tickets/{ticket}/feedback", json={"nueva_solucion": SOLUCION})

    assert r.status_code == 200
    articulo = store_aislado.get(r.json()["articulo_id"])
    assert articulo.estado == KedbEstado.BORRADOR
    assert articulo.tickets_fuente == [ticket]
    assert articulo.solucion == SOLUCION
    assert articulo.categoria == CATEGORIA
    assert [a.articulo_id for a in store_aislado.pendientes()] == [articulo.articulo_id]
    assert len(_feedback_rows(store_aislado)) == 1


@pytest.mark.parametrize("texto", ["", "   ", "corta"])
def test_solucion_vacia_o_muy_corta_se_rechaza_con_422(api_client, store_aislado, ticket, rag, texto):  # CA2
    r = api_client.post(f"/tickets/{ticket}/feedback", json={"nueva_solucion": texto})

    assert r.status_code == 422
    assert "solución" in r.json()["detail"].lower()
    assert store_aislado.pendientes() == []
    assert _feedback_rows(store_aislado) == []


def test_feedback_sin_utilidad_ni_solucion_se_rechaza_con_422(api_client, ticket, rag):  # CA2
    r = api_client.post(f"/tickets/{ticket}/feedback", json={})

    assert r.status_code == 422


def test_ticket_inexistente_devuelve_404(api_client, store_aislado, rag):
    r = api_client.post("/tickets/NO-EXISTE/feedback", json={"nueva_solucion": SOLUCION})

    assert r.status_code == 404


def test_alta_similitud_advierte_duplicado_y_no_guarda(api_client, store_aislado, ticket, rag):  # CA3
    rag.similares = [_similar(0.91)]

    r = api_client.post(f"/tickets/{ticket}/feedback", json={"nueva_solucion": SOLUCION})

    assert r.status_code == 409
    detalle = r.json()["detail"]
    assert detalle["codigo"] == "posible_duplicado"
    assert detalle["similares"][0]["articulo_o_ticket_id"] == "KEDB-EXISTENTE"
    assert store_aislado.pendientes() == []
    assert rag.consultas == [SOLUCION]


def test_duplicado_confirmado_explicitamente_se_guarda(api_client, store_aislado, ticket, rag):  # CA3
    rag.similares = [_similar(0.91)]

    r = api_client.post(
        f"/tickets/{ticket}/feedback", json={"nueva_solucion": SOLUCION, "confirmar_duplicado": True}
    )

    assert r.status_code == 200
    assert len(store_aislado.pendientes()) == 1


def test_similitud_bajo_el_umbral_no_advierte(api_client, store_aislado, ticket, rag):
    rag.similares = [_similar(0.84)]  # umbral por defecto 0.85

    r = api_client.post(f"/tickets/{ticket}/feedback", json={"nueva_solucion": SOLUCION})

    assert r.status_code == 200


def test_similitud_igual_al_umbral_advierte(api_client, store_aislado, ticket, rag):
    rag.similares = [_similar(0.85)]

    r = api_client.post(f"/tickets/{ticket}/feedback", json={"nueva_solucion": SOLUCION})

    assert r.status_code == 409


def test_resolucion_deprecada_comparte_la_misma_logica(api_client, store_aislado, ticket, rag):
    ok = api_client.post(f"/tickets/{ticket}/resolucion", json={"solucion": SOLUCION})
    corta = api_client.post(f"/tickets/{ticket}/resolucion", json={"solucion": "x"})
    sin_campo = api_client.post(f"/tickets/{ticket}/resolucion", json={})

    assert ok.status_code == 200
    assert len(store_aislado.pendientes()) == 1
    assert corta.status_code == 422
    assert sin_campo.status_code == 422
