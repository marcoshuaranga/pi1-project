"""RAG retrieval seam tests."""

from pi_core.agents.rag.agent import RAGAgent
from pi_core.schemas import SolucionSugerida
from pi_core.storage.vector_db.search import search_validated_kedb


def _results(*ids: str, estado: str = "validado") -> dict:
    return {
        "ids": [list(ids)],
        "distances": [[0.1] * len(ids)],
        "metadatas": [
            [
                {"titulo": f"Título {item}", "solucion": "Solución", "estado": estado}
                for item in ids
            ]
        ],
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
    assert kedb.calls == [
        {"query_embeddings": [[1.0, 0.0]], "n_results": 10, "where": {"estado": "validado"}},
        {"query_embeddings": [[1.0, 0.0]], "n_results": 20},
    ]


def test_retrieve_uses_validated_kedb_search_limit():
    tickets = FakeCollection()
    kedb = FakeCollection()
    agent = _agent(tickets, kedb, top_k=5)

    agent.retrieve("printer")

    # Sobre-pide vecinos (top_k * 40) porque se deduplica por texto de solución.
    assert tickets.calls == [{"query_embeddings": [[1.0, 0.0]], "n_results": 200}]
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


def test_search_kedb_applies_validation_filter():
    kedb = FakeCollection()
    agent = _agent(FakeCollection(), kedb)

    agent.search_kedb("printer", top_k=3)

    assert len(kedb.calls) == 2
    assert kedb.calls[0]["where"] == {"estado": "validado"}
    assert "where" not in kedb.calls[1]


def test_search_validated_kedb_filters_drafts_on_fallback():
    class MixedFallbackCollection(FakeCollection):
        def query(self, **kwargs):
            self.calls.append(kwargs)
            if "where" in kwargs:
                raise ValueError("where unsupported")
            return {
                "ids": [["draft", "validated"]],
                "distances": [[0.1, 0.2]],
                "metadatas": [[
                    {"estado": "borrador"},
                    {"estado": "validado"},
                ]],
            }

    kedb = MixedFallbackCollection()
    result = search_validated_kedb(kedb, [1.0, 0.0], n_results=3)

    assert result["ids"] == [["validated"]]
    assert result["metadatas"] == [[{"estado": "validado"}]]


def _empty_results() -> dict:
    return {"ids": [[]], "distances": [[]], "metadatas": [[]]}


class EmptyCollection(FakeCollection):
    def query(self, **kwargs):
        self.calls.append(kwargs)
        return _empty_results()


def test_retrieve_returns_empty_list_when_nothing_matches():
    agent = _agent(EmptyCollection(), EmptyCollection(), top_k=5)

    assert agent.retrieve("consulta sin antecedentes") == []


def test_retrieve_hides_total_vector_store_failure_as_empty_result():
    """Known limitation (spec: Known Limitations): when both collections fail, the
    agent logs and returns [], which callers cannot tell apart from a no-hit.
    Update this test when failures are surfaced to the caller."""
    agent = _agent(
        FakeCollection(raises=RuntimeError("chroma down")),
        FakeCollection(raises=RuntimeError("chroma down")),
        top_k=5,
    )

    assert agent.retrieve("printer") == []


def _tickets_con(*items: tuple[str, float, str]) -> "FakeCollection":
    """items: (id, distancia, solucion)."""

    class _Tickets(FakeCollection):
        def query(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "ids": [[i for i, _, _ in items]],
                "distances": [[d for _, d, _ in items]],
                "metadatas": [[{"titulo": f"T {i}", "solucion": s, "categoria": "C"} for i, _, s in items]],
            }

    return _Tickets()


def test_retrieve_deduplica_por_texto_de_solucion_y_conserva_el_mejor_score():
    tickets = _tickets_con(
        ("t1", 0.10, "Reiniciar el servicio"),
        ("t2", 0.12, "  reiniciar   EL servicio "),  # mismo texto normalizado -> duplicado de t1
        ("t3", 0.20, "Reinstalar el driver"),
    )
    agent = _agent(tickets, FakeCollection(raises=ValueError("sin kedb")), top_k=5)

    ids = [s.articulo_o_ticket_id for s in agent.retrieve("impresora")]

    assert ids == ["t1", "t3"]


def test_retrieve_no_deduplica_soluciones_vacias_entre_si():
    tickets = _tickets_con(("t1", 0.1, ""), ("t2", 0.2, ""))
    agent = _agent(tickets, FakeCollection(raises=ValueError("sin kedb")), top_k=5)

    assert [s.articulo_o_ticket_id for s in agent.retrieve("x")] == ["t1", "t2"]


def test_retrieve_excluir_ids_actua_antes_de_deduplicar():
    # t1 (el propio ticket) tiene la misma solución que t2: al excluir a t1, t2 debe sobrevivir.
    tickets = _tickets_con(("t1", 0.0, "Misma solución"), ("t2", 0.1, "Misma solución"), ("t3", 0.3, "Otra"))
    agent = _agent(tickets, FakeCollection(raises=ValueError("sin kedb")), top_k=5)

    ids = [s.articulo_o_ticket_id for s in agent.retrieve("x", excluir_ids={"t1"})]

    assert ids == ["t2", "t3"]
    assert agent.top_k == 5


def test_retrieve_respeta_top_k_con_soluciones_distintas():
    tickets = _tickets_con(*[(f"t{i}", 0.01 * i, f"solución {i}") for i in range(10)])
    agent = _agent(tickets, FakeCollection(raises=ValueError("sin kedb")), top_k=3)

    assert [s.articulo_o_ticket_id for s in agent.retrieve("x")] == ["t0", "t1", "t2"]
