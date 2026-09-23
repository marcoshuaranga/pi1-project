"""KEDB generation policy tests."""

from app.services.kedb_generation import KedbGenerationPolicy, KedbGenerationStatus


def test_generator_owns_primary_selection_and_fallback_policy():
    from app.agents.kedb_generator.agent import KedbGeneratorAgent

    generator = object.__new__(KedbGeneratorAgent)
    calls = []
    generator.generate_from_cluster_keyword = lambda keyword: calls.append(keyword) or "article"
    generator.generate_all = lambda max_articles: calls.append(max_articles) or []
    generator.generate_demo_fixture = lambda: "fallback"

    outcome = generator.generate(max_articles=7, keyword="kyocera")

    assert outcome.status == KedbGenerationStatus.GENERATED
    assert outcome.articles == ["article"]
    assert calls == ["kyocera"]


def test_generator_uses_all_generation_and_falls_back_when_empty():
    from app.agents.kedb_generator.agent import KedbGeneratorAgent

    generator = object.__new__(KedbGeneratorAgent)
    calls = []
    generator.generate_all = lambda max_articles: calls.append(max_articles) or []
    generator.generate_demo_fixture = lambda: "fallback"

    outcome = generator.generate(max_articles=7)

    assert outcome.status == KedbGenerationStatus.FALLBACK
    assert outcome.articles == ["fallback"]
    assert calls == [7]


def test_policy_reports_generated_articles():
    outcome = KedbGenerationPolicy(lambda: ["article"], lambda: "fallback").run()

    assert outcome.status == KedbGenerationStatus.GENERATED
    assert outcome.articles == ["article"]
    assert outcome.error is None


def test_policy_reports_fallback_after_empty_generation():
    outcome = KedbGenerationPolicy(lambda: [], lambda: "demo").run()

    assert outcome.status == KedbGenerationStatus.FALLBACK
    assert outcome.articles == ["demo"]
    assert outcome.error is None


def test_policy_reports_fallback_after_generation_failure():
    def fail():
        raise RuntimeError("cluster unavailable")

    outcome = KedbGenerationPolicy(fail, lambda: "demo").run()

    assert outcome.status == KedbGenerationStatus.FALLBACK
    assert outcome.articles == ["demo"]
    assert isinstance(outcome.error, RuntimeError)


def test_policy_reports_empty_when_no_generation_or_fallback_exists():
    outcome = KedbGenerationPolicy(lambda: [], lambda: None).run()

    assert outcome.status == KedbGenerationStatus.EMPTY
    assert outcome.articles == []


def test_policy_reports_failed_when_fallback_also_fails():
    def primary_fail():
        raise RuntimeError("primary unavailable")

    def fallback_fail():
        raise RuntimeError("fallback unavailable")

    outcome = KedbGenerationPolicy(primary_fail, fallback_fail).run()

    assert outcome.status == KedbGenerationStatus.FAILED
    assert outcome.articles == []
    assert str(outcome.error) == "fallback unavailable"
    assert str(outcome.primary_error) == "primary unavailable"
    assert outcome.fallback_error is outcome.error


def test_policy_reports_failed_when_primary_fails_without_fallback():
    def primary_fail():
        raise RuntimeError("primary unavailable")

    outcome = KedbGenerationPolicy(primary_fail, lambda: None).run()

    assert outcome.status == KedbGenerationStatus.FAILED
    assert str(outcome.error) == "primary unavailable"
    assert outcome.primary_error is outcome.error
