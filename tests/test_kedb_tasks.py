"""ARQ task boundary tests for KEDB generation outcomes."""

import pytest

from app.jobs import tasks


class FakeArticle:
    def __init__(self, article_id: str):
        self.article_id = article_id

    def model_dump(self, mode: str):
        return {"articulo_id": self.article_id}


class FakeGenerator:
    _default_fallback = object()

    def __init__(
        self,
        articles=None,
        failure: Exception | None = None,
        fallback=_default_fallback,
    ):
        self.articles = articles
        self.failure = failure
        self.fallback = (
            FakeArticle("demo") if fallback is self._default_fallback else fallback
        )

    def generate_all(self, max_articles):
        if self.failure:
            raise self.failure
        return self.articles

    def generate_from_cluster_keyword(self, keyword):
        return self.articles

    def generate_demo_fixture(self):
        if isinstance(self.fallback, Exception):
            raise self.fallback
        return self.fallback


def test_task_marks_generated_result(monkeypatch):
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator([FakeArticle("generated")]),
    )

    result = tasks._generate_kedb_sync(5, None)

    assert result == {
        "generated": 1,
        "articulos": [{"articulo_id": "generated"}],
        "status": "generated",
    }


def test_task_marks_legacy_demo_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator([], failure=RuntimeError("cluster unavailable")),
    )

    result = tasks._generate_kedb_sync(5, None)

    assert result["status"] == "fallback"
    assert result["fallback"] == "demo_fixture"
    assert result["articulos"] == [{"articulo_id": "demo"}]


def test_task_raises_when_generation_and_fallback_fail(monkeypatch):
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator(
            failure=RuntimeError("cluster unavailable"),
            fallback=RuntimeError("fixture unavailable"),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="primary=cluster unavailable; fallback=fixture unavailable",
    ):
        tasks._generate_kedb_sync(5, None)


def test_task_reports_fallback_failure_when_primary_is_empty(monkeypatch):
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator([], fallback=RuntimeError("fixture unavailable")),
    )

    with pytest.raises(RuntimeError, match="KEDB fallback failed: fixture unavailable"):
        tasks._generate_kedb_sync(5, None)


def test_task_reports_primary_failure_when_fallback_is_empty(monkeypatch):
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator(failure=RuntimeError("cluster unavailable"), fallback=None),
    )

    with pytest.raises(
        RuntimeError,
        match="KEDB generation failed; fallback returned no article: primary=cluster unavailable",
    ):
        tasks._generate_kedb_sync(5, None)


def test_task_reports_dual_failure_when_both_paths_raise_same_exception(monkeypatch):
    shared_error = RuntimeError("shared unavailable")
    monkeypatch.setattr(
        "app.agents.kedb_generator.agent.KedbGeneratorAgent",
        lambda: FakeGenerator(failure=shared_error, fallback=shared_error),
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "KEDB generation and fallback both failed: "
            "primary=shared unavailable; fallback=shared unavailable"
        ),
    ):
        tasks._generate_kedb_sync(5, None)