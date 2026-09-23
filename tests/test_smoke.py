"""Smoke and unit tests."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from pi_api.main import create_app
from pi_core.anonymize.anonymizer import Anonymizer
from pi_pipeline.ingest.normalize import assign_split, clean_html, normalize_category


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_anonymizer_email():
    anon = Anonymizer()
    result = anon.anonymize("Contactar a juan.perez@mtc.gob.pe por el ticket")
    assert "[CORREO]" in result.text
    assert "juan.perez" not in result.text


def test_anonymizer_dni():
    anon = Anonymizer()
    result = anon.anonymize("DNI del solicitante: 12345678")
    assert "[DNI]" in result.text


def test_normalize_category_impresora():
    cat = normalize_category("Equipos Informáticos > Impresora Multifuncional")
    assert cat is not None
    assert "Impresora" in cat


def test_clean_html():
    assert clean_html("<p>Hola <b>mundo</b></p>") == "Hola mundo"


def test_assign_split_train():
    assert assign_split(datetime(2024, 6, 1)) == "train"


def test_assign_split_eval():
    assert assign_split(datetime(2025, 7, 1)) == "eval"


def test_assign_split_holdout():
    assert assign_split(datetime(2025, 10, 15)) == "holdout"


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
