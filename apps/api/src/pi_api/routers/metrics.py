"""Metrics and evaluation endpoints (C9, HU15)."""

import contextlib
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from pi_api.deps import get_kedb_store as get_store
from pi_api.deps import require_feature
from pi_core.config import get_settings
from pi_core.schemas import MetricasEvaluacion

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _cached_evaluacion(cached: Path, dataset: str) -> MetricasEvaluacion:
    """Read a cached evaluation, or an explicit empty proxy when none exists."""
    if not cached.exists():
        return MetricasEvaluacion(
            f1_macro=0.0,
            recall_at_5=0.0,
            kappa=None,
            fecha_calculo=datetime.now(UTC),
            muestra_tickets=0,
            tipo_evidencia="proxy",
            metodo="Sin resultados en caché; ejecutar la evaluación",
            dataset=dataset,
        )
    data = json.loads(cached.read_text(encoding="utf-8"))
    fecha = data.get("fecha_calculo")
    fecha_calculo = datetime.now(UTC)
    if isinstance(fecha, str):
        with contextlib.suppress(ValueError):
            fecha_calculo = datetime.fromisoformat(fecha)
    return MetricasEvaluacion(
        f1_macro=data.get("f1_macro", 0.0),
        recall_at_5=data.get("recall_at_5", 0.0),
        recall_at_5_categoria=data.get("recall_at_5_categoria"),
        recall_at_5_experto=data.get("recall_at_5_experto"),
        kappa=data.get("kappa"),
        fecha_calculo=fecha_calculo,
        muestra_tickets=data.get("muestra", 0),
        tipo_evidencia=data.get("tipo_evidencia", "proxy"),
        fuente=data.get("fuente"),
        metodo=data.get("metodo"),
        dataset=data.get("dataset", dataset),
    )


@router.get("/evaluacion", response_model=MetricasEvaluacion)
async def get_evaluacion():
    """C9 — F1, Recall@5 metrics from cached results.

    To recompute, POST /metrics/evaluacion (ARQ worker).
    """
    processed = Path(get_settings().data_processed_path)
    return _cached_evaluacion(processed / "evaluation_results.json", "tickets_eval")


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


@router.get("/evaluacion-golden", response_model=MetricasEvaluacion)
async def get_evaluacion_golden():
    """C9 sobre golden_set_sample.json (200 tickets, doble etiquetado por 2 expertos).

    Ver packages/core/src/pi_core/evaluation/golden_set.py y scripts/build_golden_set.py para generarlo.
    A diferencia de /metrics/evaluacion (muestra aleatoria de tickets_eval.json),
    este endpoint también reporta Kappa inter-anotador.
    """
    processed = Path(get_settings().data_processed_path)
    return _cached_evaluacion(processed / "evaluation_results_golden.json", "golden_set")


@router.post("/evaluacion-golden", status_code=202)
async def enqueue_evaluacion_golden():
    """Enqueue golden-set evaluation recompute on the ARQ worker."""
    from fastapi.responses import JSONResponse

    from pi_core.queue import get_redis_pool
    from pi_core.schemas import JobEnqueueResponse

    redis = await get_redis_pool()
    job = await redis.enqueue_job("run_golden_evaluation")
    if job is None:
        raise HTTPException(status_code=409, detail="No se pudo encolar el job (id duplicado)")
    return JSONResponse(
        status_code=202,
        content=JobEnqueueResponse(
            job_id=job.job_id,
            status="queued",
            task="run_golden_evaluation",
        ).model_dump(),
    )


@router.get("/dashboard", dependencies=[Depends(require_feature("e05_tablero_coordinador"))])
async def get_dashboard(
    categoria: str | None = None, desde: date | None = None, hasta: date | None = None
):
    """HU15 — coordinator dashboard, filtrable por categoría y rango de fechas de generación."""
    if desde and hasta and desde > hasta:  # CA3
        raise HTTPException(
            status_code=422,
            detail="Rango de fechas inválido: la fecha de inicio es posterior a la de fin.",
        )
    settings = get_settings()
    articulos = get_store().list_all()
    if categoria:
        articulos = [a for a in articulos if categoria.lower() in a.categoria.lower()]
    if desde:
        articulos = [a for a in articulos if a.fecha_generacion.date() >= desde]
    if hasta:
        articulos = [a for a in articulos if a.fecha_generacion.date() <= hasta]

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
        "filtro_desde": desde.isoformat() if desde else None,
        "filtro_hasta": hasta.isoformat() if hasta else None,
        # CA2: la UI muestra un estado vacío explícito en vez de ceros o un gráfico en blanco.
        "sin_datos": not articulos,
    }
