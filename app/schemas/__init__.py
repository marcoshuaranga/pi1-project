"""Canonical data schemas (PRD §5)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TicketEstado(str, Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"
    EN_PROCESO = "en_proceso"


class KedbEstado(str, Enum):
    BORRADOR = "borrador"
    VALIDADO = "validado"
    OBSOLETO = "obsoleto"
    ARCHIVADO = "archivado"


class Ticket(BaseModel):
    ticket_id: str
    fecha_apertura: datetime | None = None
    fecha_cierre: datetime | None = None
    canal_origen: str | None = None
    categoria: str | None = None
    categoria_top9: str | None = None
    prioridad_original: str | None = None
    titulo_anon: str
    solucion_anon: str | None = None
    sede_id: str | None = None
    tiene_solucion: bool = False
    longitud_solucion: int = 0
    estado: str | None = None
    tipo: str | None = None
    grupo_tecnico: str | None = None
    split: str | None = None


class TicketInput(BaseModel):
    texto: str = Field(..., min_length=5, description="Texto libre del ticket")


class SolucionSugerida(BaseModel):
    articulo_o_ticket_id: str
    score: float
    tipo: str  # "ticket" | "kedb"
    titulo: str | None = None
    solucion: str | None = None


class TicketResponse(BaseModel):
    ticket_id: str
    categoria: str
    confianza: float
    prioridad: str
    justificacion_prioridad: dict[str, float] | None = None
    soluciones: list[SolucionSugerida] = Field(default_factory=list)


class KedbArticulo(BaseModel):
    articulo_id: str
    titulo: str
    categoria: str
    sintoma: str
    causa: str
    solucion: str
    tickets_fuente: list[str] = Field(default_factory=list)
    fecha_generacion: datetime
    version: int = 1
    estado: KedbEstado = KedbEstado.BORRADOR
    calidad_experta: float | None = None
    aplicable_a: str | None = None


class KedbArticuloUpdate(BaseModel):
    titulo: str | None = None
    sintoma: str | None = None
    causa: str | None = None
    solucion: str | None = None
    estado: KedbEstado | None = None
    calidad_experta: float | None = None


class GoldenSetEntry(BaseModel):
    golden_id: str
    ticket_id: str
    categoria_experto1: str | None = None
    categoria_experto2: str | None = None
    categoria_sistema: str | None = None
    split: str  # train | eval | holdout


class AgenteTipo(str, Enum):
    CLASIFICADOR = "Clasificador"
    PRIORIZADOR = "Priorizador"
    RAG = "RAG"
    GENERADOR_KEDB = "GeneradorKEDB"
    ORQUESTADOR = "Orquestador"


class EventoTipo(str, Enum):
    INICIO = "inicio"
    FIN = "fin"
    ERROR = "error"


class PipelineEvento(BaseModel):
    evento_id: str
    timestamp: datetime
    agente: AgenteTipo
    ticket_id: str
    tipo: EventoTipo
    entrada: dict[str, Any] | None = None
    salida: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class FeedbackRequest(BaseModel):
    articulo_id: str | None = None
    util: bool | None = None
    nueva_solucion: str | None = None


class CategoriaCorreccion(BaseModel):
    categoria: str


class MetricasEvaluacion(BaseModel):
    f1_macro: float
    recall_at_5: float
    kappa: float | None = None
    fecha_calculo: datetime
    muestra_tickets: int
