"""Metrics and evaluation endpoints (C9, HU15)."""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pi_api.deps import get_kedb_store as get_store
from pi_core.config import get_settings
from pi_core.schemas import MetricasEvaluacion

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/evaluacion", response_model=MetricasEvaluacion)
async def get_evaluacion():
    """C9 — F1, Recall@5 metrics from cached results.

    To recompute, POST /metrics/evaluacion (ARQ worker).
    """
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    cached = processed / "evaluation_results.json"

    if cached.exists():
        data = json.loads(cached.read_text(encoding="utf-8"))
        fecha = data.get("fecha_calculo")
        if isinstance(fecha, str):
            try:
                fecha_calculo = datetime.fromisoformat(fecha)
            except ValueError:
                fecha_calculo = datetime.now(UTC)
        else:
            fecha_calculo = datetime.now(UTC)
        return MetricasEvaluacion(
            f1_macro=data.get("f1_macro", 0.0),
            recall_at_5=data.get("recall_at_5", 0.0),
            kappa=data.get("kappa"),
            fecha_calculo=fecha_calculo,
            muestra_tickets=data.get("muestra", 0),
        )

    return MetricasEvaluacion(
        f1_macro=0.0,
        recall_at_5=0.0,
        kappa=None,
        fecha_calculo=datetime.now(UTC),
        muestra_tickets=0,
    )


@router.post("/evaluacion", status_code=202)
async def enqueue_evaluacion():
    """Enqueue evaluation recompute on the ARQ worker."""
    from fastapi.responses import JSONResponse

    from pi_core.queue import get_redis_pool
    from pi_core.schemas import JobEnqueueResponse

    redis = await get_redis_pool()
    job = await redis.enqueue_job("run_evaluation")
    if job is None:
        raise HTTPException(status_code=409, detail="No se pudo encolar el job (id duplicado)")
    return JSONResponse(
        status_code=202,
        content=JobEnqueueResponse(
            job_id=job.job_id,
            status="queued",
            task="run_evaluation",
        ).model_dump(),
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
    # Prefer lightweight manifests over loading tickets_all.json (~35MB+)
    for name in ("embeddings_manifest.json", "tickets_train.json"):
        path = processed / name
        if name == "embeddings_manifest.json" and path.exists():
            total_tickets = json.loads(path.read_text(encoding="utf-8")).get("total_embedded", 0)
            break
    if not total_tickets:
        tickets_path = processed / "tickets_all.json"
        if tickets_path.exists():
            # Count records without building a huge Python list of dicts when possible
            text = tickets_path.read_text(encoding="utf-8")
            total_tickets = text.count('"ticket_id"')

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
