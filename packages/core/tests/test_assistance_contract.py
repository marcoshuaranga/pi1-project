"""Core result-shape coverage for the operator assistance journey."""

from pi_core.schemas import SolucionSugerida, TicketResponse


def test_ticket_response_preserves_assistance_contract():
    response = TicketResponse(
        ticket_id="TICKET-CORE-001",
        categoria="VPN",
        confianza=0.74,
        prioridad="Alta",
        justificacion_prioridad={"impacto_servicio_ciudadano": 1.0},
        soluciones=[
            SolucionSugerida(
                articulo_o_ticket_id="KEDB-CORE-001",
                score=0.93,
                tipo="kedb",
                titulo="Acceso VPN",
                solucion="Validar las credenciales y la configuración del cliente",
            )
        ],
    )

    assert response.ticket_id
    assert 0 <= response.confianza <= 1
    assert response.prioridad
    assert response.soluciones[0].articulo_o_ticket_id == "KEDB-CORE-001"
    assert 0 <= response.soluciones[0].score <= 1
