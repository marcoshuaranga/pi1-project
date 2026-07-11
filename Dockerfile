FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY scripts ./scripts
COPY tests ./tests
COPY data/fixtures ./data/fixtures

RUN pip install --upgrade pip && pip install -e ".[dev]"

# Pre-install spaCy Spanish model (ADR-08)
RUN python -m spacy download es_core_news_lg

RUN mkdir -p /data/processed /data/raw /data/kedb

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
