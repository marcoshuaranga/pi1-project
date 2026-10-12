"""HU02 — la confianza baja se calcula en el backend (umbral configurable), no en la UI."""

import pytest

from pi_core.config import get_settings
from pi_core.schemas import TicketResponse


def _resp(confianza: float) -> TicketResponse:
    return TicketResponse(ticket_id="T-1", categoria="VPN > No accede al servicio", confianza=confianza, prioridad="Media")


def test_umbral_por_defecto_es_configurable_en_settings():
    assert get_settings().umbral_confianza_baja == 0.6


def test_confianza_por_debajo_del_umbral_es_baja():
    r = _resp(get_settings().umbral_confianza_baja - 0.01)
    assert r.confianza_baja is True


def test_confianza_igual_al_umbral_no_es_baja():
    assert _resp(get_settings().umbral_confianza_baja).confianza_baja is False


def test_confianza_por_encima_del_umbral_no_es_baja():
    assert _resp(0.9).confianza_baja is False


def test_confianza_maxima_no_es_baja():
    assert _resp(1.0).confianza_baja is False


def test_respuesta_serializa_flag_y_umbral_y_sobrevive_roundtrip():
    dumped = _resp(0.3).model_dump()
    assert dumped["confianza_baja"] is True
    assert dumped["umbral_confianza"] == get_settings().umbral_confianza_baja
    # Las sesiones persistidas (JSON) se releen sin que el flag guardado estorbe.
    again = TicketResponse.model_validate_json(_resp(0.3).model_dump_json())
    assert again.confianza_baja is True


def test_umbral_sobreescribible_por_entorno(monkeypatch):
    monkeypatch.setenv("UMBRAL_CONFIANZA_BAJA", "0.95")
    get_settings.cache_clear()
    try:
        assert _resp(0.9).confianza_baja is True
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("confianza", [0.0, 0.5, 1.0])
def test_confianza_acepta_extremos(confianza):
    assert _resp(confianza).confianza == confianza
