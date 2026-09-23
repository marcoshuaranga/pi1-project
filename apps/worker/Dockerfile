# Build context = repo root: docker build -f apps/worker/Dockerfile .
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Every workspace member's manifest must be present for `--locked` to validate
# uv.lock, but only pi-worker (+ its pi-core dependency) gets installed.
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml ./packages/core/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/pipeline/pyproject.toml ./apps/pipeline/pyproject.toml
RUN uv sync --locked --package pi-worker --no-install-workspace --no-cache

# No spaCy model download: the worker never runs the Anonymizer.
COPY packages/core ./packages/core
COPY apps/worker ./apps/worker
RUN uv sync --locked --package pi-worker --no-cache

RUN mkdir -p /data/processed /data/raw /data/kedb

CMD ["uv", "run", "--no-sync", "arq", "pi_worker.worker.WorkerSettings"]
