# KEDB Contract

Source of truth: `apps/api/src/pi_api/routers/kedb.py`,
`packages/core/src/pi_core/services/kedb_publisher.py`, and
`packages/core/src/pi_core/storage/kedb_store/`. Verified by
`apps/api/tests/test_kedb_lifecycle_contract.py`, `test_kedb_search_contract.py`,
`test_kedb_fsm.py`, `test_kedb_markdown.py`, and
`packages/core/tests/test_kedb_publisher.py`.

## Generation

`POST /kedb/generate?max_articles=&keyword=`

Enqueues asynchronous clustering and article synthesis and returns `202` with a
queued job identity; completion must be checked through the jobs contract. A
duplicate job id returns `409`.

## Article lifecycle

- `GET /kedb/articulos?estado=&categoria=` lists articles.
- `GET /kedb/articulos/{articulo_id}` returns content and `tickets_fuente`; `404`
  when unknown.
- `PATCH /kedb/articulos/{articulo_id}` edits content and/or requests a state
  change (`KedbArticuloUpdate`). Content edits bump `version`.
- `PATCH /kedb/articulos/{articulo_id}/ciclo-vida?estado=` requests a state
  change. **The default when `estado` is omitted is `archivado`.**
- `GET /kedb/pendientes` lists `borrador` articles awaiting expert validation.

Permitted transitions: `borrador -> validado | obsoleto`,
`validado -> obsoleto | archivado`, `obsoleto -> archivado`. Anything else returns
`409` and does not mutate the stored article. Rejecting a draft transitions it to
`obsoleto`; it does not publish the article.

## Publication and withdrawal

Publication has two read projections: the Markdown Live Docs file and the
`estado="validado"` vector entry used by retrieval.

- Entering `validado` publishes both projections.
- Editing an article that stays `validado` republishes both projections.
- Leaving `validado` (`obsoleto` or `archivado`) withdraws both projections: the
  Markdown file is deleted and the vector entry is removed.
- If a projection fails, the API returns `5xx` while the stored state has already
  changed; the error names the failed and completed projections. There is no
  automatic rollback or retry in the baseline.

## Reusable knowledge and Live Docs

- `GET /kedb/buscar?q=` (`q` at least 2 characters) returns `{query, results}` of
  validated articles only. If the vector store cannot apply the `estado` filter,
  results are filtered locally to `validado`.
- `GET /kedb/docs?estado=` lists Markdown projections; default `validado`, `todos`
  disables the filter.
- `GET /kedb/docs/{articulo_id}` returns `{articulo_id, markdown}`; `404` for a
  non-validated or unpublished article.
- `POST /kedb/export-docs?solo_validados=true` re-projects validated articles.
  Passing `false` writes every state and bypasses the validated-only rule; it is an
  administrative backup, not a publication path.
- `GET /kedb/integridad` is a read-only audit of `tickets_fuente` against the
  ticket collection.

Only validated articles may be returned as reusable knowledge or published as Live
Docs.

## Demo fixture

`POST /kedb/seed-demo` idempotently creates the Kyocera demo `borrador`. It is a
fixture operation, unauthenticated in the baseline, and is not evidence of live
generation.

## Jobs

`GET /jobs/{job_id}` and `GET /jobs/{job_id}/result` expose asynchronous generation
and evaluation status and results. A queued job is not equivalent to a generated
article. `GET /jobs/{job_id}` returns `status` (the ARQ status), `success`, `result`,
and `error`; a job that raised has `status = complete` with `success = false`.
`GET /jobs/{job_id}/result` returns `404` for an unknown job, `409` while it has not
completed, and `500` with the error for a failed job.
