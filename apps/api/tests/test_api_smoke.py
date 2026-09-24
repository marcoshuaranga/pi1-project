"""API smoke tests."""

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_kedb_pendientes_empty(client):
    response = client.get("/kedb/pendientes")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_metrics_dashboard(client):
    response = client.get("/metrics/dashboard")
    assert response.status_code == 200


def test_create_ticket_no_chroma(client, monkeypatch):
    """Ticket creation uses keyword fallback when ChromaDB unavailable."""

    class MockClassifier:
        def classify(self, texto):
            return {"categoria": "test", "confianza": 0.9, "top3": []}

    class MockPrioritizer:
        def prioritize(self, texto, categoria, context=None):
            return {"prioridad": "Media", "score": 0.4, "justificacion": {}}

    class MockRAG:
        def retrieve(self, texto, categoria=None):
            return []

    class MockAnonymizer:
        def anonymize(self, text):
            from pi_core.anonymize.anonymizer import AnonymizationResult

            return AnonymizationResult(text=text)

    monkeypatch.setattr("pi_core.agents.orchestrator.graph.get_anonymizer", lambda: MockAnonymizer())
    monkeypatch.setattr("pi_core.agents.orchestrator.graph.ClassifierAgent", lambda: MockClassifier())
    monkeypatch.setattr("pi_core.agents.orchestrator.graph.PrioritizerAgent", lambda: MockPrioritizer())
    monkeypatch.setattr("pi_core.agents.orchestrator.graph.RAGAgent", lambda: MockRAG())

    from pi_api.deps import get_kedb_store, get_orchestrator

    get_orchestrator.cache_clear()
    get_kedb_store.cache_clear()

    response = client.post("/tickets", json={"texto": "Impresora no imprime"})
    assert response.status_code == 200
    data = response.json()
    assert "ticket_id" in data
    assert data["prioridad"] == "Media"
