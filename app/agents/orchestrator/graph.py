"""C7 — LangGraph orchestrator (sequential pipeline)."""

import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Callable

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.classifier.agent import ClassifierAgent
from app.agents.prioritizer.agent import PrioritizerAgent
from app.agents.rag.agent import RAGAgent
from app.pipeline.anonymize.anonymizer import get_anonymizer
from app.schemas import (
    AgenteTipo,
    EventoTipo,
    PipelineEvento,
    SolucionSugerida,
    TicketResponse,
)

_on_event_ctx: ContextVar[Callable[[PipelineEvento], None] | None] = ContextVar(
    "orchestrator_on_event", default=None
)


class PipelineState(TypedDict, total=False):
    ticket_id: str
    texto: str
    texto_anon: str
    categoria: str
    confianza: float
    prioridad: str
    justificacion_prioridad: dict
    soluciones: list
    eventos: list
    error: str


class Orchestrator:
    def __init__(self, on_event: Callable[[PipelineEvento], None] | None = None):
        self.anonymizer = get_anonymizer()
        self.classifier = ClassifierAgent()
        self.prioritizer = PrioritizerAgent()
        self.rag = RAGAgent()
        self.on_event = on_event
        self.graph = self._build_graph()

    def _emit(
        self,
        agente: AgenteTipo,
        ticket_id: str,
        tipo: EventoTipo,
        entrada: dict | None = None,
        salida: dict | None = None,
    ) -> PipelineEvento:
        evento = PipelineEvento(
            evento_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            agente=agente,
            ticket_id=ticket_id,
            tipo=tipo,
            entrada=entrada,
            salida=salida,
        )
        callback = _on_event_ctx.get() or self.on_event
        if callback:
            callback(evento)
        return evento

    def _build_graph(self):
        graph = StateGraph(PipelineState)

        def anonymize_node(state: PipelineState) -> dict:
            tid = state["ticket_id"]
            self._emit(AgenteTipo.ORQUESTADOR, tid, EventoTipo.INICIO, {"texto": state["texto"]})
            result = self.anonymizer.anonymize(state["texto"])
            return {"texto_anon": result.text}

        def classify_node(state: PipelineState) -> dict:
            tid = state["ticket_id"]
            self._emit(AgenteTipo.CLASIFICADOR, tid, EventoTipo.INICIO)
            out = self.classifier.classify(state["texto_anon"])
            self._emit(AgenteTipo.CLASIFICADOR, tid, EventoTipo.FIN, salida=out)
            return {"categoria": out["categoria"], "confianza": out["confianza"]}

        def prioritize_node(state: PipelineState) -> dict:
            tid = state["ticket_id"]
            self._emit(AgenteTipo.PRIORIZADOR, tid, EventoTipo.INICIO)
            out = self.prioritizer.prioritize(state["texto_anon"], state["categoria"])
            self._emit(AgenteTipo.PRIORIZADOR, tid, EventoTipo.FIN, salida=out)
            return {
                "prioridad": out["prioridad"],
                "justificacion_prioridad": out["justificacion"],
            }

        def rag_node(state: PipelineState) -> dict:
            tid = state["ticket_id"]
            self._emit(AgenteTipo.RAG, tid, EventoTipo.INICIO)
            soluciones = self.rag.retrieve(state["texto_anon"], state.get("categoria"))
            out = [s.model_dump() for s in soluciones]
            self._emit(AgenteTipo.RAG, tid, EventoTipo.FIN, salida={"count": len(out)})
            return {"soluciones": out}

        graph.add_node("anonymize", anonymize_node)
        graph.add_node("classify", classify_node)
        graph.add_node("prioritize", prioritize_node)
        graph.add_node("rag", rag_node)

        graph.set_entry_point("anonymize")
        graph.add_edge("anonymize", "classify")
        graph.add_edge("classify", "prioritize")
        graph.add_edge("prioritize", "rag")
        graph.add_edge("rag", END)

        return graph.compile()

    def process_ticket(
        self,
        texto: str,
        ticket_id: str | None = None,
        on_event: Callable[[PipelineEvento], None] | None = None,
    ) -> TicketResponse:
        tid = ticket_id or f"T-{uuid.uuid4().hex[:8].upper()}"
        token = _on_event_ctx.set(on_event)
        try:
            initial: PipelineState = {"ticket_id": tid, "texto": texto, "eventos": []}
            result = self.graph.invoke(initial)
            soluciones = [
                SolucionSugerida(**s) if isinstance(s, dict) else s
                for s in result.get("soluciones", [])
            ]
            self._emit(AgenteTipo.ORQUESTADOR, tid, EventoTipo.FIN)
            return TicketResponse(
                ticket_id=tid,
                categoria=result.get("categoria", ""),
                confianza=result.get("confianza", 0.0),
                prioridad=result.get("prioridad", "Media"),
                justificacion_prioridad=result.get("justificacion_prioridad"),
                soluciones=soluciones,
            )
        finally:
            _on_event_ctx.reset(token)
