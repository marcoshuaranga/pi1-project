"""RAG retrieval seam tests."""

from app.agents.rag.agent import RAGAgent
from app.schemas import SolucionSugerida
from app.storage.vector_db.search import search_validated_kedb


def _results(*ids: str) -> dict:
    return {
        "ids": [list(ids)],
        "distances": [[0.1] * len(ids)],
        "metadatas": [[{"titulo": f"Título {item}", "solucion": "Solución"} for item in ids]],
    }


class FakeEmbedder:
    def embed_text(self, text: str, cache_key: str) -> list[float]:
        return [1.0, 0.0]


class FakeCollection:
    def __init__(self, raises: Exception | None = None):
        self.calls = []
        self._raises = raises

    def query(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        if "where" in kwargs:
            raise ValueError("where unsupported")
        return _results("article-1")

    def upsert(self, **kwargs):
        self.calls.append(kwargs)


def _agent(tickets: FakeCollection, kedb: FakeCollection, top_k: int = 5) -> RAGAgent:
    agent = object.__new__(RAGAgent)
    agent.embedder = FakeEmbedder()
    agent.tickets = tickets
    agent.kedb = kedb
    agent.top_k = top_k
    return agent


def test_search_kedb_uses_call_limit_without_mutating_agent_limit():
    kedb = FakeCollection()
    agent = _agent(FakeCollection(), kedb, top_k=5)

    results = agent.search_kedb("printer", top_k=10)

    assert isinstance(results[0], SolucionSugerida)
    assert agent.top_k == 5
    assert kedb.calls == [{"query_embeddings": [[1.0, 0.0]], "n_results": 10}]


def test_retrieve_uses_validated_kedb_search_limit():
    tickets = FakeCollection()
    kedb = FakeCollection()
    agent = _agent(tickets, kedb, top_k=5)

    agent.retrieve("printer")

    assert tickets.calls == [{"query_embeddings": [[1.0, 0.0]], "n_results": 10}]
    # search_validated_kedb always probes with the filter first, then retries
    # unfiltered once Chroma rejects it (FakeCollection.query raises on "where").
    assert len(kedb.calls) == 2
    assert kedb.calls[0]["where"] == {"estado": "validado"}
    assert "where" not in kedb.calls[1]


def test_retrieve_degrades_when_tickets_collection_fails():
    """The except-and-log path in RAGAgent.retrieve — previously unreachable
    because the old FakeSearch double could never raise."""
    tickets = FakeCollection(raises=RuntimeError("chroma down"))
    kedb = FakeCollection()
    agent = _agent(tickets, kedb, top_k=5)

    soluciones = agent.retrieve("printer")

    assert all(s.tipo == "kedb" for s in soluciones)


def test_retrieve_degrades_when_kedb_collection_fails():
    tickets = FakeCollection()
    kedb = FakeCollection(raises=RuntimeError("chroma down"))
    agent = _agent(tickets, kedb, top_k=5)

    soluciones = agent.retrieve("printer")

    assert all(s.tipo == "ticket" for s in soluciones)


def test_search_validated_kedb_falls_back_when_filter_is_unsupported():
    kedb = FakeCollection()

    result = search_validated_kedb(kedb, [1.0, 0.0], n_results=3)

    assert result == _results("article-1")
    assert len(kedb.calls) == 2
    assert kedb.calls[0]["where"] == {"estado": "validado"}
    assert "where" not in kedb.calls[1]


def test_search_kedb_does_not_apply_validation_filter():
    kedb = FakeCollection()
    agent = _agent(FakeCollection(), kedb)

    agent.search_kedb("printer", top_k=3)

    assert len(kedb.calls) == 1
    assert "where" not in kedb.calls[0]
