"""Smoke del flujo del Operador (Sprint 3): ticket → confianza baja → corrección → factores →
calificación doble → nueva solución con y sin duplicado."""

from pi_core.constants import TOP9_CATEGORIES
from pi_core.schemas import SolucionSugerida, TicketResponse


class _Orq:
    def process_ticket(self, texto: str) -> TicketResponse:
        return TicketResponse(
            ticket_id="T-FLUJO",
            categoria=TOP9_CATEGORIES[3],
            confianza=0.4,
            prioridad="Media",
            justificacion_prioridad={},
        )


class _Rag:
    similares: list[SolucionSugerida] = []

    def search_kedb(self, query, top_k=10):
        return self.similares


def test_flujo_completo_del_operador(api_client, store_aislado, monkeypatch):
    rag = _Rag()
    monkeypatch.setattr("pi_api.routers.tickets.get_orchestrator", _Orq)
    monkeypatch.setattr("pi_api.routers.kedb.get_rag", lambda: rag)

    t = api_client.post("/tickets", json={"texto": "No puedo conectarme a la VPN"}).json()
    assert t["confianza_baja"] is True  # HU02
    assert t["justificacion_prioridad"] == {}  # HU05 CA2

    url = f"/tickets/{t['ticket_id']}"
    assert api_client.patch(f"{url}/categoria", json={"categoria": TOP9_CATEGORIES[4]}).json()["cambio"]
    assert api_client.patch(f"{url}/categoria", json={"categoria": "inventada"}).status_code == 422  # HU03

    for util in (True, False):  # HU11
        assert api_client.post(f"{url}/feedback", json={"articulo_id": "KEDB-X", "util": util}).status_code == 200
    with store_aislado._conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ticket_feedback").fetchone()[0] == 1

    solucion = {"nueva_solucion": "Renovar el certificado del cliente VPN y reiniciar el servicio."}
    rag.similares = [SolucionSugerida(articulo_o_ticket_id="KEDB-V", score=0.95, tipo="kedb")]
    assert api_client.post(f"{url}/feedback", json=solucion).status_code == 409  # HU12 duplicado
    rag.similares = []
    assert api_client.post(f"{url}/feedback", json=solucion).status_code == 200  # HU12 sin duplicado
    assert len(store_aislado.pendientes()) == 1
