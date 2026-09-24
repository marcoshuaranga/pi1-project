# Setup and operations

## Minimum requirements

- Docker and Docker Compose
- OpenAI API key
- export GLPI as `Tickets_Consolidados.xlsx` placed in `data/raw/`

## Initial setup

```bash
cp .env.example .env
# set OPENAI_API_KEY

# place the raw inbox export in data/raw/
```

## Start the stack

```bash
docker compose up --build
```

## Run data pipeline

```bash
docker compose --profile pipeline run --rm pipeline full
```

## Seed demo data

```bash
curl -X POST http://localhost:8000/kedb/seed-demo
# or
# docker compose exec api python scripts/seed_demo.py
```

## Reset demo state

```bash
docker compose exec api python scripts/reset_demo.py
```

## Validation commands

```bash
uv run pytest
uv run ruff check .
```

For member-scoped validation, run the tests in the package that owns the code:

```bash
uv run pytest packages/core/tests
uv run pytest apps/api/tests
uv run pytest apps/worker/tests
uv run pytest apps/pipeline/tests
```

This keeps the shared core boundary visible and catches imports that only work
because another workspace member happens to be installed.

## Useful URLs

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Web UI: http://localhost:3000
- ChromaDB: http://localhost:8001

## Troubleshooting

- If embeddings are unavailable, set `EMBEDDING_PROVIDER=local` in `.env`.
- If the demo state is stale, use the reset script above.
- If the KEDB draft does not appear, rerun the demo seed flow and confirm the API is healthy.
