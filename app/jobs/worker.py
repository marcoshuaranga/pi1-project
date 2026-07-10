"""ARQ worker entrypoint: `arq app.jobs.worker.WorkerSettings`."""

from app.jobs.redis import get_redis_settings
from app.jobs.tasks import generate_kedb, run_evaluation


class WorkerSettings:
    """One heavy job at a time to avoid RAM spikes (spaCy / HDBSCAN / embeddings)."""

    functions = [generate_kedb, run_evaluation]
    redis_settings = get_redis_settings()
    max_jobs = 1
    job_timeout = 3600
    keep_result = 3600
    max_tries = 2
