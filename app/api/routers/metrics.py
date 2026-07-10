"""Metrics and evaluation endpoints (C9, HU15)."""

import json
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

from app.config import get_settings
from app.evaluation.metrics import EvaluationFramework
from app.schemas import MetricasEvaluacion
from app.storage.kedb_store.store import KedbStore

router = APIRouter(prefix="/metrics", tags=["metrics"])


@lru_cache
def get_store() -> KedbStore:
    return KedbStore()


@router.get("/evaluacion", response_model=MetricasEvaluacion)
async def get_evaluacion():
    """C9 — F1, Recall@5 metrics."""
    framework = EvaluationFramework()
    metrics = framework.run_evaluation()
    return MetricasEvaluacion(
        f1_macro=metrics["f1_macro"],
        recall_at_5=metrics["recall_at_5"],
        kappa=metrics.get("kappa"),
        fecha_calculo=datetime.now(timezone.utc),
        muestra_tickets=metrics.get("muestra", 0),
    )


@router.get("/dashboard")
async def get_dashboard(categoria: str | None = None):
    """HU15 — coordinator dashboard."""
    settings = get_settings()
    articulos = get_store().list_all()
    if categoria:
        articulos = [a for a in articulos if categoria.lower() in a.categoria.lower()]

    por_estado = Counter(a.estado.value for a in articulos)
    por_categoria = Counter(a.categoria for a in articulos)

    processed = Path(settings.data_processed_path)
    total_tickets = 0
    tickets_path = processed / "tickets_all.json"
    if tickets_path.exists():
        total_tickets = len(json.loads(tickets_path.read_text(encoding="utf-8")))

    return {
        "cobertura_kedb": {
            "total_articulos": len(articulos),
            "validados": por_estado.get("validado", 0),
            "borradores": por_estado.get("borrador", 0),
            "por_categoria": dict(por_categoria.most_common(10)),
        },
        "tickets_procesados": total_tickets,
        "filtro_categoria": categoria,
    }
