"""Contract coverage for the operator ticket-assistance journey."""

from pi_core.schemas import SolucionSugerida, TicketResponse


class DeterministicOrchestrator:
    def process_ticket(self, texto: str) -> TicketResponse:
        assert texto
        return TicketResponse(
            ticket_id="TICKET-CONTRACT-001",
            categoria="Impresora Multifuncional",
            confianza=0.91,
            prioridad="Media",
            justificacion_prioridad={"score": 0.4},
            soluciones=[
                SolucionSugerida(
                    articulo_o_ticket_id="TICKET-SOURCE-001",
                    score=0.88,
                    tipo="ticket",
                    titulo="Configuración de impresora",
                    solucion="Configurar la impresora predeterminada",
                )
            ],
        )


def test_create_ticket_returns_traceable_assistance_result(api_client, monkeypatch):
    monkeypatch.setattr("pi_api.routers.tickets.get_orchestrator", DeterministicOrchestrator)

    response = api_client.post("/tickets", json={"texto": "La impresora no imprime"})

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "TICKET-CONTRACT-001"
    assert body["categoria"] == "Impresora Multifuncional"
    assert body["confianza"] == 0.91
    assert body["prioridad"] == "Media"
    assert body["soluciones"][0]["articulo_o_ticket_id"] == "TICKET-SOURCE-001"
    assert body["soluciones"][0]["score"] == 0.88


def test_ticket_status_returns_not_found_for_unknown_ticket(api_client):
    response = api_client.get("/tickets/TICKET-UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket no encontrado"


def test_create_ticket_rejects_text_shorter_than_minimum(api_client):
    response = api_client.post("/tickets", json={"texto": "abc"})

    assert response.status_code == 422
