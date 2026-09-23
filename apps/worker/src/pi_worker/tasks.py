"""ARQ task functions — heavy work runs in a thread so the worker event loop stays free."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pi_core.services.kedb_generation import KedbGenerationStatus

logger = logging.getLogger(__name__)


def _generate_kedb_sync(max_articles: int, keyword: str | None) -> dict[str, Any]:
    from pi_core.agents.kedb_generator.agent import KedbGeneratorAgent

    generator = KedbGeneratorAgent()
    outcome = generator.generate(max_articles=max_articles, keyword=keyword)
    if outcome.status == KedbGenerationStatus.FAILED:
        message = outcome.describe_failure()
        if message is None:
            raise RuntimeError("KEDB generation failed without an error")
        raise RuntimeError(message) from outcome.error
    if outcome.status == KedbGenerationStatus.EMPTY:
        return {"generated": 0, "articulos": [], "status": outcome.status.value}

    if outcome.status == KedbGenerationStatus.FALLBACK:
        logger.warning(
            "generate_kedb usó fixture de demo%s error=%s",
            " tras un fallo de generación" if outcome.error else " por resultado vacío",
            outcome.error,
        )
    result = {
        "generated": len(outcome.articles),
        "articulos": [a.model_dump(mode="json") for a in outcome.articles],
        "status": outcome.status.value,
    }
    if outcome.status == KedbGenerationStatus.FALLBACK:
        result["fallback"] = "demo_fixture"
    return result


def _run_evaluation_sync() -> dict[str, Any]:
    from pi_core.evaluation.metrics import EvaluationFramework

    # Framework already persists evaluation_results.json with fecha_calculo.
    return EvaluationFramework().run_evaluation()


async def generate_kedb(
    ctx: dict[str, Any],
    max_articles: int = 50,
    keyword: str | None = None,
) -> dict[str, Any]:
    """Cluster tickets and synthesize KEDB articles (CPU/RAM heavy)."""
    return await asyncio.to_thread(_generate_kedb_sync, max_articles, keyword)


async def run_evaluation(ctx: dict[str, Any]) -> dict[str, Any]:
    """Recompute F1 / Recall@5 and persist cache file."""
    return await asyncio.to_thread(_run_evaluation_sync)
