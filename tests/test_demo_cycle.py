"""Demo cycle: seed → approve → RAG surfaces KEDB (mocked)."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import SolucionSugerida
from app.storage.kedb_store.store import KedbStore


@pytest.fixture
def client():
    return TestClient(create_app())


def test_load_kyocera_fixture_has_cluster_size():
    from app.fixtures.kyocera_demo import load_kyocera_ticket_ids

    ids = load_kyocera_ticket_ids()
    assert len(ids) >= 100
    assert "96044" in ids


def test_demo_cycle_seed_approve_rag(client, monkeypatch, tmp_path):
    """Escena 2→3: seed fixture, approve indexes KEDB, ticket retrieve includes it."""
    from app.api.routers import kedb as kedb_router
    from app.api.deps import get_orchestrator

    db_path = tmp_path / "demo_kedb.db"
    docs_path = tmp_path / "articles"
    docs_path.mkdir()
    settings = Settings(kedb_db_path=str(db_path), kedb_docs_path=str(docs_path))
    store = KedbStore(settings)

    indexed: dict[str, dict] = {}

    class MockRAG:
        def index_articulo(self, articulo_id: str, texto: str, metadata: dict) -> None:
            indexed[articulo_id] = metadata

        def retrieve(self, texto: str, categoria: str | None = None):
            if not indexed:
                return []
            aid = next(iter(indexed))
            return [
                SolucionSugerida(
                    articulo_o_ticket_id=aid,
                    score=0.97,
                    tipo="kedb",
                    titulo=indexed[aid].get("titulo"),
                    solucion=indexed[aid].get("solucion"),
                )
            ]

    mock_rag = MockRAG()
    kedb_router.get_store.cache_clear()
    kedb_router.get_rag.cache_clear()
    monkeypatch.setattr(kedb_router, "get_store", lambda: store)
    monkeypatch.setattr(kedb_router, "get_rag", lambda: mock_rag)
    monkeypatch.setattr(
        "app.fixtures.kyocera_demo.load_kyocera_ticket_ids",
        lambda **kwargs: ["96044", "95984", "95645", "95439", "94922"] * 28 + ["96044", "95984"],
    )
    monkeypatch.setattr(
        "app.pipeline.enrich.reindex.reindex_kyocera_cluster",
        lambda **kwargs: 142,
    )

    # First seed
    seed = client.post("/kedb/seed-demo")
    assert seed.status_code == 200
    articulo = seed.json()
    assert articulo["estado"] == "borrador"
    assert len(articulo["tickets_fuente"]) == 142
    assert "Kyocera" in articulo["titulo"]
    first_id = articulo["articulo_id"]

    # Idempotent: second seed removes previous Kyocera borrador(es) and creates one fresh
    seed2 = client.post("/kedb/seed-demo")
    assert seed2.status_code == 200
    articulo2 = seed2.json()
    assert articulo2["articulo_id"] != first_id
    pendientes = client.get("/kedb/pendientes")
    assert pendientes.status_code == 200
    kyocera = [a for a in pendientes.json() if "kyocera" in a["titulo"].lower()]
    assert len(kyocera) == 1
    articulo = articulo2

    approve = client.patch(
        f"/kedb/articulos/{articulo['articulo_id']}",
        json={"estado": "validado"},
    )
    assert approve.status_code == 200
    assert approve.json()["estado"] == "validado"
    assert articulo["articulo_id"] in indexed
    assert indexed[articulo["articulo_id"]].get("tipo") == "kedb"

    class MockClassifier:
        def classify(self, texto):
            return {"categoria": "Impresora Multifuncional", "confianza": 0.9, "top3": []}

    class MockPrioritizer:
        def prioritize(self, texto, categoria, context=None):
            return {"prioridad": "Media", "score": 0.4, "justificacion": {}}

    class MockAnonymizer:
        def anonymize(self, text):
            from app.pipeline.anonymize.anonymizer import AnonymizationResult

            return AnonymizationResult(text=text)

    monkeypatch.setattr("app.agents.orchestrator.graph.get_anonymizer", lambda: MockAnonymizer())
    monkeypatch.setattr("app.agents.orchestrator.graph.ClassifierAgent", lambda: MockClassifier())
    monkeypatch.setattr("app.agents.orchestrator.graph.PrioritizerAgent", lambda: MockPrioritizer())
    monkeypatch.setattr("app.agents.orchestrator.graph.RAGAgent", lambda: mock_rag)
    get_orchestrator.cache_clear()

    ticket = client.post(
        "/tickets",
        json={"texto": "Impresora Kyocera 7003 no imprime, necesito que la configuren"},
    )
    assert ticket.status_code == 200
    data = ticket.json()
    assert data["prioridad"] == "Media"
    assert any(s["tipo"] == "kedb" and s["articulo_o_ticket_id"] == articulo["articulo_id"] for s in data["soluciones"])


def test_build_demo_articulo_uses_ids():
    from app.fixtures.kyocera_demo import build_demo_articulo

    art = build_demo_articulo(ticket_ids=["1", "2", "3"], articulo_id="KEDB-TEST")
    assert art.articulo_id == "KEDB-TEST"
    assert art.tickets_fuente == ["1", "2", "3"]
    assert art.estado.value == "borrador"
