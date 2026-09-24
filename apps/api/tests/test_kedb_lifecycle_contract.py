"""HTTP contract coverage for expert KEDB lifecycle operations."""

from pi_core.config import Settings
from pi_core.fixtures.kyocera_demo import build_demo_articulo
from pi_core.schemas import KedbEstado
from pi_core.services.kedb_publisher import KedbPublisher
from pi_core.storage.kedb_store.store import KedbStore


class NoopPublisher:
    def __init__(self):
        self.published = []
        self.unpublished = []

    def publish(self, articulo):
        self.published.append(articulo)

    def unpublish(self, articulo_id):
        self.unpublished.append(articulo_id)


def _seed_store(tmp_path):
    settings = Settings(
        kedb_db_path=str(tmp_path / "lifecycle.db"),
        kedb_docs_path=str(tmp_path / "articles"),
    )
    (tmp_path / "articles").mkdir()
    store = KedbStore(settings)
    article = build_demo_articulo(
        ticket_ids=["SOURCE-001", "SOURCE-002"],
        articulo_id="KEDB-CONTRACT-001",
    )
    store.create(article)
    return store


def test_kedb_article_list_detail_edit_and_approve(api_client, monkeypatch, tmp_path):
    store = _seed_store(tmp_path)
    publisher = NoopPublisher()
    monkeypatch.setattr("pi_api.routers.kedb.get_store", lambda: store)
    monkeypatch.setattr("pi_api.routers.kedb.get_publisher", lambda: publisher)

    listed = api_client.get("/kedb/articulos", params={"estado": "borrador"})
    detail = api_client.get("/kedb/articulos/KEDB-CONTRACT-001")
    edited = api_client.patch(
        "/kedb/articulos/KEDB-CONTRACT-001",
        json={"titulo": "Título revisado"},
    )
    approved = api_client.patch(
        "/kedb/articulos/KEDB-CONTRACT-001",
        json={"estado": "validado"},
    )

    assert listed.status_code == 200
    assert listed.json()[0]["tickets_fuente"] == ["SOURCE-001", "SOURCE-002"]
    assert detail.status_code == 200
    assert detail.json()["articulo_id"] == "KEDB-CONTRACT-001"
    assert edited.status_code == 200
    assert edited.json()["titulo"] == "Título revisado"
    assert approved.status_code == 200
    assert approved.json()["estado"] == KedbEstado.VALIDADO.value
    assert publisher.published[-1].estado == KedbEstado.VALIDADO

class RecordingRag:
    """Stands in for the write side of the Chroma-backed RAG agent."""

    def __init__(self):
        self.indexed: dict[str, dict] = {}

    def index_articulo(self, articulo_id, texto, metadata):
        self.indexed[articulo_id] = metadata

    def remove_articulo(self, articulo_id):
        self.indexed.pop(articulo_id, None)


def test_archiving_a_validated_article_withdraws_it_from_reuse_and_live_docs(
    api_client, monkeypatch, tmp_path
):
    """FR-006: an article that leaves `validado` must stop being reusable knowledge."""
    store = _seed_store(tmp_path)
    rag = RecordingRag()
    monkeypatch.setattr("pi_api.routers.kedb.get_store", lambda: store)
    monkeypatch.setattr("pi_api.routers.kedb.get_publisher", lambda: KedbPublisher(store, rag))
    monkeypatch.setattr("pi_core.storage.kedb_store.markdown.get_settings", lambda: store.settings)

    api_client.patch("/kedb/articulos/KEDB-CONTRACT-001", json={"estado": "validado"})
    assert "KEDB-CONTRACT-001" in rag.indexed
    assert (tmp_path / "articles" / "KEDB-CONTRACT-001.md").exists()
    assert [d["articulo_id"] for d in api_client.get("/kedb/docs").json()] == ["KEDB-CONTRACT-001"]

    archived = api_client.patch(
        "/kedb/articulos/KEDB-CONTRACT-001/ciclo-vida", params={"estado": "archivado"}
    )

    assert archived.status_code == 200
    assert archived.json()["estado"] == KedbEstado.ARCHIVADO.value
    assert "KEDB-CONTRACT-001" not in rag.indexed
    assert not (tmp_path / "articles" / "KEDB-CONTRACT-001.md").exists()
    assert api_client.get("/kedb/docs").json() == []


def test_rejecting_a_draft_does_not_touch_published_projections(api_client, monkeypatch, tmp_path):
    store = _seed_store(tmp_path)
    publisher = NoopPublisher()
    monkeypatch.setattr("pi_api.routers.kedb.get_store", lambda: store)
    monkeypatch.setattr("pi_api.routers.kedb.get_publisher", lambda: publisher)

    rejected = api_client.patch("/kedb/articulos/KEDB-CONTRACT-001", json={"estado": "obsoleto"})

    assert rejected.status_code == 200
    assert rejected.json()["estado"] == KedbEstado.OBSOLETO.value
    assert publisher.published == []
    assert publisher.unpublished == []
