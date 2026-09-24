"""Shared domain fixtures for core contract and lifecycle tests."""

from datetime import UTC, datetime

import pytest

from pi_core.schemas import (
    AgenteTipo,
    EventoTipo,
    KedbArticulo,
    MetricasEvaluacion,
    PipelineEvento,
    TicketInput,
)


@pytest.fixture
def ticket_input() -> TicketInput:
    return TicketInput(texto="La impresora no imprime y requiere configuración")


@pytest.fixture
def kedb_articulo() -> KedbArticulo:
    return KedbArticulo(
        articulo_id="KEDB-TEST-001",
        titulo="Configuración de impresora",
        categoria="Impresora Multifuncional",
        sintoma="La impresora no imprime",
        causa="Configuración predeterminada incorrecta",
        solucion="Configurar la impresora predeterminada y validar una impresión",
        tickets_fuente=["TICKET-TEST-001"],
        fecha_generacion=datetime.now(UTC),
    )


@pytest.fixture
def pipeline_event() -> PipelineEvento:
    return PipelineEvento(
        evento_id="EVENT-TEST-001",
        timestamp=datetime.now(UTC),
        agente=AgenteTipo.ORQUESTADOR,
        ticket_id="TICKET-TEST-001",
        tipo=EventoTipo.FIN,
    )


@pytest.fixture
def metricas_evaluacion() -> MetricasEvaluacion:
    return MetricasEvaluacion(
        f1_macro=0.8,
        recall_at_5=0.85,
        kappa=None,
        fecha_calculo=datetime.now(UTC),
        muestra_tickets=200,
    )
