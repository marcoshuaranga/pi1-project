# Quickstart: Implemented Closed Assistance-KEDB Loop

This guide validates the current baseline. It does not claim that all target
metrics are already achieved.

## Prerequisites

- Windows or Linux development environment with Python/uv and Node/npm.
- Repository dependencies installed with `uv sync`.
- Frontend dependencies installed from `web/` with `npm install` or the repository
  lockfile workflow.
- For asynchronous KEDB and evaluation jobs, Redis and the worker service must be
  available through the repository's Docker Compose setup.
- ChromaDB and configured model services must be available for live retrieval and
  generation paths.

## Start the services

From the repository root:

```powershell
docker compose up --build
```

For a frontend-only development loop (Node from the system PATH, or
`mise exec node@24 -- npm run dev` where Node is managed by mise):

```powershell
cd web
npm run dev
```

## Validate operator assistance

1. Open the operator view or call `POST /tickets` with valid anonymized ticket
   text.
2. Verify the response contains a ticket identity, category, confidence,
   priority, and ordered solution suggestions.
3. Open the ticket status endpoint and verify the completed or failed state.
4. Observe `/ws/pipeline/{ticket_id}` while processing and confirm stage events
   are visible when the WebSocket path is enabled.

## Validate expert KEDB governance

1. Create or load a draft article through the KEDB workflow.
2. Retrieve it from `GET /kedb/pendientes` or `GET /kedb/articulos` filtered by
   `borrador`.
3. Edit or approve it through the article lifecycle endpoint.
4. Confirm invalid transitions return a conflict and preserve the previous state.
5. Confirm an approved article is `validado`, appears in validated docs, and is
   eligible for retrieval.
6. Confirm a draft is not exposed as validated Live Docs or reusable knowledge.
7. Move the validated article to `archivado` and confirm it disappears from
   `GET /kedb/docs` and `GET /kedb/buscar`.

## Validate asynchronous jobs

1. Enqueue KEDB generation with `POST /kedb/generate` or evaluation with
   `POST /metrics/evaluacion`.
2. Poll `GET /jobs/{job_id}` until `status` is `complete`, then check `success`: a
   job that raised is `complete` with `success = false` and an `error`.
3. Read `GET /jobs/{job_id}/result` (`500` when the job failed) and record the task,
   dataset, and outcome.
4. Treat a queued response as scheduling evidence only, not completion evidence.

## Validate metrics honestly

- Use `GET /metrics/evaluacion` for cached/general evaluation results.
- Use `GET /metrics/evaluacion-golden` for the golden-set result and Kappa when
  the corresponding artifact exists.
- Record dataset, sample size, timestamp, and whether each value is measured,
  targeted, or a documented proxy.
- Do not use a demo fixture or same-ticket proxy as proof of general retrieval
  quality.

## Validate privacy

1. Place the source export only in the local, ignored `data/raw/` directory.
2. Run the anonymization stage before ingestion:

```powershell
docker compose --profile pipeline run --rm pipeline anonymize
```

3. Inspect `data/processed/sample_anonymized.parquet` and run the privacy tests:

```powershell
uv run pytest apps/pipeline/tests/test_privacy_gate.py packages/core/tests/test_anonymization_dod.py
```

4. A residual structured PII match causes the anonymization stage to fail before
   `sample_anonymized.parquet` is written; the `ingest` stage re-runs the same
   check on the parquet it reads, so a stale file cannot bypass the gate. The check
   covers structured PII only, not personal names (see the spec's Known
   Limitations). Downstream indexing/embedding must not be started after a failure.
5. Never use an unreviewed raw export in a demo, test fixture, or committed file.

## Automated validation

```powershell
uv run pytest
uv run ruff check .
cd web
npm run build
```

Run the narrowest relevant member tests first when iterating. Integration checks
that require ChromaDB, Redis, or model services require those services to be up.

## Frontend route smoke check

After `npm run dev -- --host 127.0.0.1`, verify that the SPA serves each supported
view without a route-level 404 and that the compiled UI exposes the corresponding
workflow:

| Route        | Workflow                                               |
| :----------- | :----------------------------------------------------- |
| `/`          | Operador: ticket assistance and pipeline result        |
| `/whatsapp`  | Simulated WhatsApp intake feeding the operator flow    |
| `/experto`   | Experto KEDB: draft review and approval/rejection      |
| `/kedb`      | KEDB management and pending knowledge                  |
| `/docs`      | Live Docs for validated articles                       |
| `/dashboard` | Coordinador: metrics, search, and lifecycle visibility |

The route check is a smoke check, not a substitute for API contract tests or
live-service evaluation.

## Related documentation

- [README.md](../../README.md): project entry point.
- [docs/README.md](../../docs/README.md): documentation index.
- [docs/operations/setup.md](../../docs/operations/setup.md): environment setup and runtime commands.
