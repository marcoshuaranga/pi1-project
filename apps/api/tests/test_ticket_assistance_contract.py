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


class NoHitOrchestrator:
    def process_ticket(self, texto: str) -> TicketResponse:
        return TicketResponse(
            ticket_id="TICKET-NOHIT-001",
            categoria="Otros",
            confianza=0.31,
            prioridad="Baja",
            soluciones=[],
        )


def test_create_ticket_returns_explicit_empty_result_when_nothing_matches(api_client, monkeypatch):
    """US1.4: a no-hit ticket is a 200 with an empty suggestion list, not an error."""
    monkeypatch.setattr("pi_api.routers.tickets.get_orchestrator", NoHitOrchestrator)

    response = api_client.post("/tickets", json={"texto": "Consulta sin antecedentes"})

    assert response.status_code == 200
    body = response.json()
    assert body["soluciones"] == []
    assert body["confianza"] < 0.5


def test_create_ticket_exposes_confianza_baja_flag(api_client, monkeypatch):
    """HU02 — la UI recibe el flag y el umbral; no duplica la regla."""
    monkeypatch.setattr("pi_api.routers.tickets.get_orchestrator", NoHitOrchestrator)

    body = api_client.post("/tickets", json={"texto": "Algo muy ambiguo"}).json()

    assert body["confianza"] == 0.31
    assert body["confianza_baja"] is True
    assert body["umbral_confianza"] == 0.6
