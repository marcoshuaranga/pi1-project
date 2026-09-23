FROM python:3.11-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps in their own layer, keyed off the lockfile, so code-only
# changes below don't bust the dependency cache.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --extra dev --no-install-project --no-cache

# Pre-install spaCy Spanish model (ADR-08). Depends only on pyproject.toml/
# uv.lock (spacy itself, installed above), not on application code — keep
# it before COPY app/tests/scripts so a code-only change doesn't force a
# re-download of this 541MB layer.
RUN uv run python -m spacy download es_core_news_lg

COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
COPY data/fixtures ./data/fixtures

RUN uv sync --locked --extra dev --no-cache

RUN mkdir -p /data/processed /data/raw /data/kedb

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
