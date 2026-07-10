"""ARQ task functions — heavy work runs in a thread so the worker event loop stays free."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _generate_kedb_sync(max_articles: int, keyword: str | None) -> dict[str, Any]:
    from app.agents.kedb_generator.agent import KedbGeneratorAgent

    generator = KedbGeneratorAgent()
    if keyword:
        articulo = generator.generate_from_cluster_keyword(keyword)
        if not articulo:
            articulo = generator.generate_demo_fixture()
        return {"generated": 1, "articulos": [articulo.model_dump(mode="json")]}

    articles = generator.generate_all(max_articles=max_articles)
    if not articles:
        articles = [generator.generate_demo_fixture()]
    return {
        "generated": len(articles),
        "articulos": [a.model_dump(mode="json") for a in articles],
    }


def _run_evaluation_sync() -> dict[str, Any]:
    from app.config import get_settings
    from app.evaluation.metrics import EvaluationFramework

    framework = EvaluationFramework()
    metrics = framework.run_evaluation()
    payload = {
        "f1_macro": metrics["f1_macro"],
        "recall_at_5": metrics["recall_at_5"],
        "kappa": metrics.get("kappa"),
        "muestra": metrics.get("muestra", 0),
        "fecha_calculo": datetime.now(timezone.utc).isoformat(),
    }
    processed = Path(get_settings().data_processed_path)
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "evaluation_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


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
