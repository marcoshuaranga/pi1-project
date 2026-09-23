"""ARQ worker entrypoint: `arq pi_worker.worker.WorkerSettings`."""

from pi_core.queue import get_redis_settings
from pi_worker.tasks import generate_kedb, run_evaluation, run_golden_evaluation


class WorkerSettings:
    """One heavy job at a time to avoid RAM spikes (spaCy / HDBSCAN / embeddings)."""

    functions = [generate_kedb, run_evaluation, run_golden_evaluation]
    redis_settings = get_redis_settings()
    max_jobs = 1
    job_timeout = 3600
    keep_result = 3600
    max_tries = 2
