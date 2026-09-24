"""WebSocket contract coverage for pipeline progress and failures."""

from pi_core.schemas import PipelineEvento, TicketResponse


class EventingOrchestrator:
    def process_ticket(self, texto, *, ticket_id, on_event):
        on_event(
            PipelineEvento(
                evento_id="EVENT-WS-001",
                timestamp="2026-09-23T00:00:00Z",
                agente="Orquestador",
                ticket_id=ticket_id,
                tipo="fin",
            )
        )
        return TicketResponse(
            ticket_id=ticket_id,
            categoria="VPN",
            confianza=0.8,
            prioridad="Media",
            soluciones=[],
        )


class FailingOrchestrator:
    def process_ticket(self, texto, *, ticket_id, on_event):
        raise RuntimeError("pipeline unavailable")


def test_pipeline_websocket_emits_event_and_result(api_client, monkeypatch):
    monkeypatch.setattr("pi_api.ws.pipeline.get_orchestrator", EventingOrchestrator)

    with api_client.websocket_connect("/ws/pipeline/TICKET-WS-001") as websocket:
        websocket.send_json({"action": "process", "texto": "VPN no conecta"})
        event = websocket.receive_json()
        result = websocket.receive_json()

    assert event["evento_id"] == "EVENT-WS-001"
    assert event["ticket_id"] == "TICKET-WS-001"
    assert event["tipo"] == "fin"
    assert result["type"] == "result"
    assert result["data"]["ticket_id"] == "TICKET-WS-001"


def test_pipeline_websocket_reports_terminal_error(api_client, monkeypatch):
    monkeypatch.setattr("pi_api.ws.pipeline.get_orchestrator", FailingOrchestrator)

    with api_client.websocket_connect("/ws/pipeline/TICKET-WS-ERROR") as websocket:
        websocket.send_json({"action": "process", "texto": "VPN no conecta"})
        error = websocket.receive_json()

    assert error == {"type": "error", "message": "pipeline unavailable"}
