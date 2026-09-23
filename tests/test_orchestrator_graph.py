"""Orquestador node-wrapper seam tests.

_instrumented_node owns the emit(INICIO) -> call -> emit(FIN) ritual for every
graph node; the _step_* methods own only the agent-call + state-mapping. Both
are testable here without building or invoking the compiled LangGraph.
"""

from app.agents.orchestrator.graph import Orchestrator
from app.schemas import AgenteTipo, EventoTipo, SolucionSugerida


def _orchestrator(**attrs) -> Orchestrator:
    orch = object.__new__(Orchestrator)
    orch.on_event = None
    for name, value in attrs.items():
        setattr(orch, name, value)
    return orch


class RecordingEmit:
    def __init__(self):
        self.calls = []

    def __call__(self, agente, ticket_id, tipo, entrada=None, salida=None):
        self.calls.append(
            {"agente": agente, "ticket_id": ticket_id, "tipo": tipo, "entrada": entrada, "salida": salida}
        )


def test_instrumented_node_emits_inicio_then_fin_around_the_step():
    orch = _orchestrator()
    orch._emit = RecordingEmit()

    def step(state):
        return {"categoria": "Hardware"}, {"categoria": "Hardware", "confianza": 0.9}

    node = orch._instrumented_node(AgenteTipo.CLASIFICADOR, step)
    updates = node({"ticket_id": "T-1"})

    assert updates == {"categoria": "Hardware"}
    assert [c["tipo"] for c in orch._emit.calls] == [EventoTipo.INICIO, EventoTipo.FIN]
    assert orch._emit.calls[0] == {
        "agente": AgenteTipo.CLASIFICADOR,
        "ticket_id": "T-1",
        "tipo": EventoTipo.INICIO,
        "entrada": None,
        "salida": None,
    }
    assert orch._emit.calls[1]["salida"] == {"categoria": "Hardware", "confianza": 0.9}


def test_instrumented_node_forwards_entrada_from_state():
    orch = _orchestrator()
    orch._emit = RecordingEmit()

    node = orch._instrumented_node(
        AgenteTipo.ORQUESTADOR,
        lambda state: ({"texto_anon": "x"}, {"texto_anon": "x"}),
        entrada=lambda state: {"texto": state["texto"]},
    )
    node({"ticket_id": "T-1", "texto": "Impresora no imprime"})

    assert orch._emit.calls[0]["entrada"] == {"texto": "Impresora no imprime"}


class FakeAnonymizer:
    def anonymize(self, texto):
        class Result:
            text = texto.replace("Juan", "[NOMBRE]")

        return Result()


def test_step_anonymize_uses_same_dict_for_updates_and_salida():
    orch = _orchestrator(anonymizer=FakeAnonymizer())

    updates, salida = orch._step_anonymize({"texto": "Reporta Juan"})

    assert updates == {"texto_anon": "Reporta [NOMBRE]"}
    assert salida == updates


class FakeClassifier:
    def classify(self, texto):
        return {"categoria": "Hardware", "confianza": 0.87, "vecinos": ["T-1", "T-2"]}


def test_step_classify_projects_only_categoria_and_confianza_into_state():
    orch = _orchestrator(classifier=FakeClassifier())

    updates, salida = orch._step_classify({"texto_anon": "..."})

    assert updates == {"categoria": "Hardware", "confianza": 0.87}
    # salida keeps the full agent output (e.g. vecinos) for the pipeline event
    assert salida == {"categoria": "Hardware", "confianza": 0.87, "vecinos": ["T-1", "T-2"]}


class FakePrioritizer:
    def prioritize(self, texto, categoria):
        return {"prioridad": "Alta", "score": 0.71, "justificacion": {"impacto_servicio_ciudadano": 0.3}}


def test_step_prioritize_renames_justificacion_key_for_state():
    orch = _orchestrator(prioritizer=FakePrioritizer())

    updates, salida = orch._step_prioritize({"texto_anon": "...", "categoria": "Hardware"})

    assert updates == {
        "prioridad": "Alta",
        "justificacion_prioridad": {"impacto_servicio_ciudadano": 0.3},
    }
    assert salida["score"] == 0.71


class FakeRAG:
    def retrieve(self, texto, categoria):
        return [
            SolucionSugerida(articulo_o_ticket_id="T-9", score=0.9, tipo="ticket"),
            SolucionSugerida(articulo_o_ticket_id="KEDB-1", score=0.8, tipo="kedb"),
        ]


def test_step_rag_salida_is_count_not_full_solution_list():
    orch = _orchestrator(rag=FakeRAG())

    updates, salida = orch._step_rag({"texto_anon": "...", "categoria": "Hardware"})

    assert len(updates["soluciones"]) == 2
    assert salida == {"count": 2}
