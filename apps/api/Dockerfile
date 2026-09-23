# Build context = repo root: docker build -f apps/api/Dockerfile .
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
# uv.lock, but only pi-api (+ its pi-core dependency) gets installed.
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml ./packages/core/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/pipeline/pyproject.toml ./apps/pipeline/pyproject.toml
RUN uv sync --locked --package pi-api --no-install-workspace --no-cache

# Pre-install spaCy Spanish model (ADR-08). Depends only on the lockfile
# (spacy itself, installed above), not on application code — keep it before
# the source COPY so a code-only change doesn't re-download this 541MB layer.
RUN uv run --no-sync python -m spacy download es_core_news_lg

COPY packages/core ./packages/core
COPY apps/api ./apps/api
COPY scripts ./scripts
COPY data/fixtures ./data/fixtures
# --inexact: an exact sync would uninstall the spaCy model above (it isn't in uv.lock).
RUN uv sync --locked --inexact --package pi-api --no-cache

RUN mkdir -p /data/processed /data/raw /data/kedb

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "pi_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
