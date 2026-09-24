"""HTTP contract coverage for validated KEDB search."""

from pi_core.schemas import SolucionSugerida


class FakeRag:
    def search_kedb(self, query: str):
        assert query == "vpn"
        return [
            SolucionSugerida(
                articulo_o_ticket_id="KEDB-SEARCH-001",
                score=0.94,
                tipo="kedb",
                titulo="Acceso VPN",
                solucion="Validar la configuración del cliente",
            )
        ]


def test_kedb_search_returns_relevance_and_source_context(api_client, monkeypatch):
    monkeypatch.setattr("pi_api.routers.kedb.get_rag", lambda: FakeRag())

    response = api_client.get("/kedb/buscar", params={"q": "vpn"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "vpn",
        "results": [
            {
                "articulo_o_ticket_id": "KEDB-SEARCH-001",
                "score": 0.94,
                "tipo": "kedb",
                "titulo": "Acceso VPN",
                "solucion": "Validar la configuración del cliente",
            }
        ],
    }


def test_kedb_search_requires_meaningful_query(api_client):
    response = api_client.get("/kedb/buscar", params={"q": "x"})

    assert response.status_code == 422
