# Synchronous ticket pipeline, asynchronous KEDB generation and evaluation

_Not part of the original ADR-01..08 numbering (those are transcribed from the thesis chapters); written from a 2026-09 architecture audit of code that had no corresponding ADR._

`POST /tickets` runs the Clasificador → Priorizador → Agente RAG chain synchronously in-request (`app/api/routers/tickets.py:14-19`, via `asyncio.to_thread` awaited before responding). GeneradorKEDB and the C9 evaluation run instead as background jobs queued through arq + redis (`app/jobs/tasks.py:62-73`, enqueued from `app/api/routers/kedb.py:33-51` and `app/api/routers/metrics.py:60-79`).

The two are treated differently because they have different latency requirements: the ticket path has a hard end-to-end budget (PRD §7.7: ≤30s, since an operator is waiting on the response), while KEDB generation (clustering + LLM synthesis over many tickets) and evaluation (scoring over a golden/eval set) are minutes-scale batch work with no one blocking on the HTTP response. Running the batch work in-request would either blow the ticket-path latency budget or force the operator-facing endpoint to poll a job it didn't ask for.

## Considered options

- **Everything synchronous** — rejected: KEDB generation/evaluation runtime is unbounded relative to the ticket path's 30s budget.
- **Everything asynchronous** (including tickets) — rejected: the Operador screen needs an immediate classify+prioritize+retrieve response, not a job to poll, for the interactive golden-path flow (Escena 1 of the demo).

## Consequences

Two execution models coexist in one codebase (sync request/response vs. arq job queue). New agents or endpoints need an explicit latency-budget decision — not a default — for which model they use.
