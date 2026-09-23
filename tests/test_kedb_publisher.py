"""KEDB publication policy tests."""

from app.fixtures.kyocera_demo import build_demo_articulo
from app.schemas import KedbEstado
from app.services.kedb_publisher import (
    KedbPublication,
    KedbPublicationError,
    KedbPublisher,
)


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


def test_publication_builds_one_projection_payload_for_validated_article():
    articulo = build_demo_articulo(ticket_ids=["1"], articulo_id="KEDB-TEST")
    articulo = articulo.model_copy(update={"estado": KedbEstado.VALIDADO})

    publication = KedbPublication.from_article(articulo)

    publication.article.titulo = "Mutated after publication payload creation"
    assert publication.article.titulo != "Mutated after publication payload creation"
    assert publication.text == (
        f"{publication.article.titulo}\n"
        f"{publication.article.sintoma}\n"
        f"{publication.article.solucion}"
    )
    assert publication.metadata == {
        "titulo": publication.article.titulo,
        "solucion": publication.article.solucion,
        "categoria": publication.article.categoria,
        "estado": KedbEstado.VALIDADO.value,
        "tipo": "kedb",
    }


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


def test_publish_reports_completed_and_failed_projections():
    store = FakeStore()

    class FailingRag(FakeRag):
        def index_articulo(self, articulo_id, texto, metadata):
            raise RuntimeError("vector unavailable")

    articulo = build_demo_articulo(ticket_ids=["1"], articulo_id="KEDB-TEST")
    articulo = articulo.model_copy(update={"estado": KedbEstado.VALIDADO})

    try:
        KedbPublisher(store, FailingRag()).publish(articulo)
    except KedbPublicationError as exc:
        assert exc.failed_projection == "vector"
        assert exc.completed_projections == ("markdown",)
    else:
        raise AssertionError("Expected publication failure")

    assert store.published == [articulo]
