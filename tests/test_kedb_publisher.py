"""KEDB publication policy tests."""

from app.fixtures.kyocera_demo import build_demo_articulo
from app.schemas import KedbEstado
from app.services.kedb_publisher import KedbPublisher


class FakeStore:
    def __init__(self):
        self.published = []

    def publish_markdown(self, articulo):
        self.published.append(articulo)


class FakeRag:
    def __init__(self):
        self.indexed = []

    def index_articulo(self, articulo_id, texto, metadata):
        self.indexed.append((articulo_id, texto, metadata))


def test_publish_validated_article_updates_both_projections():
    store = FakeStore()
    rag = FakeRag()
    articulo = build_demo_articulo(ticket_ids=["1"], articulo_id="KEDB-TEST")
    articulo = articulo.model_copy(update={"estado": KedbEstado.VALIDADO})

    KedbPublisher(store, rag).publish(articulo)

    assert store.published == [articulo]
    assert rag.indexed == [
        (
            "KEDB-TEST",
            f"{articulo.titulo}\n{articulo.sintoma}\n{articulo.solucion}",
            {
                "titulo": articulo.titulo,
                "solucion": articulo.solucion,
                "categoria": articulo.categoria,
                "estado": "validado",
                "tipo": "kedb",
            },
        )
    ]


def test_publish_draft_article_does_not_update_projections():
    store = FakeStore()
    rag = FakeRag()
    articulo = build_demo_articulo(ticket_ids=["1"], articulo_id="KEDB-TEST")

    KedbPublisher(store, rag).publish(articulo)

    assert store.published == []
    assert rag.indexed == []