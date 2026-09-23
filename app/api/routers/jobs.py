"""Job status endpoints for ARQ background tasks."""

from arq.jobs import Job
from fastapi import APIRouter, HTTPException

from app.jobs.redis import get_redis_pool
from app.schemas import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    """Poll ARQ job status / result."""
    redis = await get_redis_pool()
    job = Job(job_id, redis)
    status = await job.status()
    status_value = status.value if hasattr(status, "value") else str(status)

    task: str | None = None
    success: bool | None = None
    result = None
    error: str | None = None

    info = await job.info()
    if info is not None:
        task = getattr(info, "function", None)
        if hasattr(info, "success"):
            success = bool(info.success)
            if info.success:
                result = info.result
            else:
                err = info.result
                error = str(err) if err is not None else "job failed"

    return JobStatusResponse(
        job_id=job_id,
        status=status_value,
        task=task,
        success=success,
        result=result,
        error=error,
    )


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    """Return job result only when complete; 404/409 otherwise."""
    redis = await get_redis_pool()
    job = Job(job_id, redis)
    status = await job.status()
    status_value = status.value if hasattr(status, "value") else str(status)

    if status_value == "not_found":
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if status_value != "complete":
        raise HTTPException(
            status_code=409,
            detail={"job_id": job_id, "status": status_value, "message": "Job aún no completado"},
        )

    result_info = await job.result_info()
    if result_info is None:
        raise HTTPException(status_code=404, detail="Resultado no disponible")
    if not result_info.success:
        raise HTTPException(
            status_code=500,
            detail={"job_id": job_id, "error": str(result_info.result)},
        )
    return {"job_id": job_id, "status": "complete", "result": result_info.result}
