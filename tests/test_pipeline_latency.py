"""PRD §7.7 DoD: ticket pipeline (C3+C4+C5+C7) responds in <=30s end-to-end.

Two tiers:
- test_orchestrator_overhead_is_within_budget: always runs, mocks the 3
  agents, and is a regression guard on the orchestration layer itself (graph
  construction, event emission, state threading) — it does NOT validate real
  embedding/LLM latency, since that depends on live services and API keys.
- test_ticket_pipeline_meets_30s_dod_live: exercises the real agents against
  a live Chroma + embedding provider and asserts the actual PRD budget. It
  skips itself if Chroma isn't reachable, since CI/dev environments without
  `docker compose up` can't satisfy it — this is the test that actually
  proves the DoD criterion when run against the real stack.
"""

import time

import pytest


def test_orchestrator_overhead_is_within_budget(monkeypatch):
    """Regression guard: the graph's own overhead should be near-instant.

    Not a substitute for the live DoD test below — this only catches
    accidental blocking work added to the orchestration layer itself."""
    from app.agents.orchestrator.graph import Orchestrator
    from app.pipeline.anonymize.anonymizer import AnonymizationResult

    class MockAnonymizer:
        def anonymize(self, text):
            return AnonymizationResult(text=text)

    class MockClassifier:
        def classify(self, texto):
            return {"categoria": "Impresora Multifuncional", "confianza": 0.9, "top3": []}

    class MockPrioritizer:
        def prioritize(self, texto, categoria, context=None):
            return {"prioridad": "Media", "score": 0.4, "justificacion": {}}

    class MockRAG:
        def retrieve(self, texto, categoria=None):
            return []

    monkeypatch.setattr("app.agents.orchestrator.graph.get_anonymizer", lambda: MockAnonymizer())
    monkeypatch.setattr("app.agents.orchestrator.graph.ClassifierAgent", lambda: MockClassifier())
    monkeypatch.setattr("app.agents.orchestrator.graph.PrioritizerAgent", lambda: MockPrioritizer())
    monkeypatch.setattr("app.agents.orchestrator.graph.RAGAgent", lambda: MockRAG())

    orchestrator = Orchestrator()
    start = time.monotonic()
    orchestrator.process_ticket("Impresora Kyocera 7003 no imprime")
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"Orchestration overhead alone took {elapsed:.2f}s (budget: 30s total, mocked agents)"


@pytest.mark.integration
def test_ticket_pipeline_meets_30s_dod_live():
    """Live DoD check: PRD §7.7 — tiempo de respuesta <=30s end-to-end.

    Requires a reachable Chroma with an ingested/embedded ticket corpus
    (`docker compose up` + `pipeline full`) and a working embedding
    provider. Skips rather than fails when that stack isn't available, so
    the unit test suite stays green without live services."""
    from app.agents.orchestrator.graph import Orchestrator
    from app.storage.vector_db.client import get_tickets_collection

    try:
        get_tickets_collection().count()
    except Exception as e:
        pytest.skip(f"Chroma no disponible para el DoD en vivo ({e}); requiere `docker compose up`")

    orchestrator = Orchestrator()
    start = time.monotonic()
    orchestrator.process_ticket("Impresora Kyocera 7003 no imprime, necesito que la configuren de nuevo")
    elapsed = time.monotonic() - start

    assert elapsed <= 30.0, f"Pipeline end-to-end tardó {elapsed:.2f}s (criterio PRD §7.7: <=30s)"
