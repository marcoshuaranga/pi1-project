"""RAG retrieval seam tests."""

from app.agents.rag.agent import RAGAgent
from app.schemas import SolucionSugerida
from app.storage.vector_db.search import VectorSearchAdapter


def _results(*ids: str) -> dict:
    return {
        "ids": [list(ids)],
        "distances": [[0.1] * len(ids)],
        "metadatas": [[{"titulo": f"Título {item}", "solucion": "Solución"} for item in ids]],
    }


class FakeEmbedder:
    def embed_text(self, text: str, cache_key: str) -> list[float]:
        return [1.0, 0.0]


class FakeSearch:
    def __init__(self):
        self.calls = []

    def search_tickets(self, vector, n_results):
        self.calls.append(("tickets", n_results))
        return _results("ticket-1")

    def search_kedb(self, vector, n_results):
        self.calls.append(("kedb", n_results))
        return _results("article-1")

    def search_validated_kedb(self, vector, n_results):
        self.calls.append(("validated-kedb", n_results))
        return _results("article-1")

    def index_kedb(self, articulo_id, vector, texto, metadata):
        self.calls.append(("index-kedb", articulo_id, texto, metadata))


def _agent(search: FakeSearch, top_k: int = 5) -> RAGAgent:
    agent = object.__new__(RAGAgent)
    agent.embedder = FakeEmbedder()
    agent.vector_search = search
    agent.top_k = top_k
    return agent


def test_search_kedb_uses_call_limit_without_mutating_agent_limit():
    search = FakeSearch()
    agent = _agent(search, top_k=5)

    results = agent.search_kedb("printer", top_k=10)

    assert isinstance(results[0], SolucionSugerida)
    assert agent.top_k == 5
    assert search.calls == [("kedb", 10)]


def test_retrieve_uses_validated_kedb_search_limit():
    search = FakeSearch()
    agent = _agent(search, top_k=5)

    agent.retrieve("printer")

    assert search.calls == [("tickets", 10), ("validated-kedb", 5)]


class FakeCollection:
    def __init__(self):
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        if "where" in kwargs:
            raise ValueError("where unsupported")
        return _results("article-1")


def test_vector_search_adapter_falls_back_when_kedb_filter_is_unsupported():
    tickets = FakeCollection()
    kedb = FakeCollection()
    adapter = VectorSearchAdapter(tickets, kedb)

    result = adapter.search_validated_kedb([1.0, 0.0], n_results=3)

    assert result == _results("article-1")
    assert len(kedb.calls) == 2
    assert kedb.calls[0]["where"] == {"estado": "validado"}
    assert "where" not in kedb.calls[1]


def test_vector_search_adapter_search_kedb_does_not_apply_validation_filter():
    kedb = FakeCollection()
    adapter = VectorSearchAdapter(FakeCollection(), kedb)

    adapter.search_kedb([1.0, 0.0], n_results=3)

    assert len(kedb.calls) == 1
    assert "where" not in kedb.calls[0]