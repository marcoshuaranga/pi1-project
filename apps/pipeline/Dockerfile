# Build context = repo root: docker build -f apps/pipeline/Dockerfile .
FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Every workspace member's manifest must be present for `--locked` to validate
# uv.lock, but only pi-pipeline (+ its pi-core dependency) gets installed.
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml ./packages/core/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/pipeline/pyproject.toml ./apps/pipeline/pyproject.toml
RUN uv sync --locked --package pi-pipeline --no-install-workspace --no-cache

# Batch ingest anonymizes with spaCy NER (ADR-08); same layer ordering as api.
RUN uv run --no-sync python -m spacy download es_core_news_lg

COPY packages/core ./packages/core
COPY apps/pipeline ./apps/pipeline
COPY scripts ./scripts
COPY data/fixtures ./data/fixtures
# --inexact: an exact sync would uninstall the spaCy model above (it isn't in uv.lock).
RUN uv sync --locked --inexact --package pi-pipeline --no-cache

RUN mkdir -p /data/processed /data/raw /data/kedb

ENTRYPOINT ["uv", "run", "--no-sync", "python", "-m", "pi_pipeline.cli"]
