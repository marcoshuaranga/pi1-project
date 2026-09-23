"""C7 — LangGraph orchestrator (sequential pipeline)."""

import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from pi_core.agents.classifier.agent import ClassifierAgent
from pi_core.agents.prioritizer.agent import PrioritizerAgent
from pi_core.agents.rag.agent import RAGAgent
from pi_core.anonymize.anonymizer import get_anonymizer
from pi_core.schemas import (
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
            timestamp=datetime.now(UTC),
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

    def _instrumented_node(
        self,
        agente: AgenteTipo,
        step: Callable[[PipelineState], tuple[dict, dict]],
        entrada: Callable[[PipelineState], dict] | None = None,
    ) -> Callable[[PipelineState], dict]:
        """Wrap a step (state -> (state_updates, evento_salida)) with the
        emit(INICIO) -> call -> emit(FIN) ritual every graph node needs."""

        def node(state: PipelineState) -> dict:
            tid = state["ticket_id"]
            self._emit(agente, tid, EventoTipo.INICIO, entrada(state) if entrada else None)
            updates, salida = step(state)
            self._emit(agente, tid, EventoTipo.FIN, salida=salida)
            return updates

        return node

    def _step_anonymize(self, state: PipelineState) -> tuple[dict, dict]:
        result = self.anonymizer.anonymize(state["texto"])
        updates = {"texto_anon": result.text}
        return updates, updates

    def _step_classify(self, state: PipelineState) -> tuple[dict, dict]:
        out = self.classifier.classify(state["texto_anon"])
        return {"categoria": out["categoria"], "confianza": out["confianza"]}, out

    def _step_prioritize(self, state: PipelineState) -> tuple[dict, dict]:
        out = self.prioritizer.prioritize(state["texto_anon"], state["categoria"])
        updates = {
            "prioridad": out["prioridad"],
            "justificacion_prioridad": out["justificacion"],
        }
        return updates, out

    def _step_rag(self, state: PipelineState) -> tuple[dict, dict]:
        soluciones = self.rag.retrieve(state["texto_anon"], state.get("categoria"))
        out = [s.model_dump() for s in soluciones]
        # salida carries only the count, not the full solution list — keeps
        # the WS pipeline event payload small.
        return {"soluciones": out}, {"count": len(out)}

    def _build_graph(self):
        graph = StateGraph(PipelineState)

        # Anonymization has no dedicated AgenteTipo (it's C1/data-layer, not
        # one of the 5 domain agents) so it's attributed to ORQUESTADOR here.
        # Its FIN pairs with this node's INICIO; process_ticket emits a
        # separate ORQUESTADOR FIN for the whole pipeline's completion after
        # the rag node runs.
        graph.add_node(
            "anonymize",
            self._instrumented_node(
                AgenteTipo.ORQUESTADOR,
                self._step_anonymize,
                entrada=lambda state: {"texto": state["texto"]},
            ),
        )
        graph.add_node(
            "classify", self._instrumented_node(AgenteTipo.CLASIFICADOR, self._step_classify)
        )
        graph.add_node(
            "prioritize", self._instrumented_node(AgenteTipo.PRIORIZADOR, self._step_prioritize)
        )
        graph.add_node("rag", self._instrumented_node(AgenteTipo.RAG, self._step_rag))

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
