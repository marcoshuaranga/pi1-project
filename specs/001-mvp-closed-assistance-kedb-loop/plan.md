# Implementation Plan: Implemented Closed Assistance-KEDB Loop

**Branch**: `001-mvp-closed-assistance-kedb-loop` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-mvp-closed-assistance-kedb-loop/spec.md`

## Summary

Document and validate the currently implemented closed assistance-to-KEDB loop:
anonymized historical knowledge supports ticket classification, prioritization,
and retrieval; resolved knowledge produces KEDB drafts; an expert validates the
article; validated knowledge becomes reusable. The implementation work for this
baseline is primarily contract documentation, focused acceptance coverage, and
truthful alignment between current code, the PRD, and Spec Kit artifacts.

## Technical Context

**Language/Version**: Python 3.11+ backend; TypeScript/React frontend

**Primary Dependencies**: FastAPI, Pydantic, LangGraph, ChromaDB, SQLite,
ARQ/Redis, spaCy, OpenAI-compatible model services, React, Vite, Tailwind CSS

**Storage**: SQLite for KEDB/session state; ChromaDB for vector retrieval;
JSON/Markdown processed artifacts; Redis for asynchronous job queues

**Testing**: pytest/pytest-asyncio, Ruff, FastAPI endpoint tests, core unit and
integration tests. The frontend has no test runner by decision; `npm run build`
(`tsc && vite build`) is its automated gate.

**Target Platform**: Linux containers and local Windows development through the
repository's Docker/uv/npm workflows

**Project Type**: Python monorepo with shared domain package, FastAPI API,
asynchronous worker, batch pipeline, and React web application

**Performance Goals**: Product target is ticket assistance within 30 seconds
end-to-end. This is a target until measured by a named evaluation run; demo
fixtures and proxy Recall@5 values are not production evidence.

**Constraints**: Anonymization precedes indexing, embedding, evaluation, and
display. Only human-validated articles are reusable KEDB knowledge. Apps depend
on `packages/core`, never the reverse. Existing ADRs govern adopted technical
choices. Raw PII and unreviewed exports must not enter committed artifacts.

**Scale/Scope**: Spanish help-desk ticket corpus, nine principal categories in
the product scope, five frontend operational views, asynchronous KEDB and
evaluation jobs, and the current API contracts described in this feature.

**Evidence semantics**: Evaluation responses must identify whether a value is a
measured result, target, or proxy, including dataset and method/source context.
This is implemented: `MetricasEvaluacion` carries `tipo_evidencia` (`medido`,
`objetivo`, `proxy`; default `proxy`), `fuente`, `metodo`, and `dataset`, and the
dashboard displays them. Current evaluators emit `proxy` only.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- PARTIAL: The feature preserves human approval as the publication boundary for
  reusable KEDB knowledge, but principle I also requires every lifecycle
  transition to be auditable and the store keeps no transition history. Tracked
  in Complexity Tracking and Risks; not silently accepted.
- PASS (structured PII only): The feature treats anonymization as a prerequisite
  and does not add raw data or generated PII artifacts. The ingestion gate does
  not re-check personal names (see the spec's Known Limitations).
- PASS: The design keeps shared behavior in `packages/core` and application
  delivery in `apps/*`/`web/`.
- PASS: The specification labels target metrics, proxy metrics, demo fixtures,
  and aspirational conditional routing separately from measured behavior.
- PASS: The plan identifies contract/integration validation for shared schemas,
  REST, WebSocket events, jobs, lifecycle transitions, and privacy gates.
- DEVIATION: One constitution gap (missing lifecycle audit trail) exists in the
  code this baseline documents. It is justified below because closing it is new
  product work, not baseline validation.

## Project Structure

### Documentation (this feature)

```text
specs/001-mvp-closed-assistance-kedb-loop/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/           # tickets.md, kedb.md, metrics.md
├── checklists/          # requirements.md, constitution.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/core/src/pi_core/
├── schemas/              # canonical Ticket, KEDB, event, job, metric models
├── agents/               # classifier, prioritizer, RAG, KEDB, orchestrator
├── anonymize/             # privacy preprocessing
├── storage/               # SQLite KEDB/session and Chroma access
├── services/              # embeddings, LLM, publisher, policy, integrity
└── evaluation/            # metrics, golden-set, evaluation workflows

apps/api/src/pi_api/
├── routers/               # tickets, kedb, metrics, jobs
└── ws/                    # pipeline event delivery

apps/worker/src/pi_worker/ # ARQ KEDB generation and evaluation jobs
apps/pipeline/src/pi_pipeline/
├── cli.py                 # extract, anonymize, ingest, embed, enrich-kyocera, full
└── ingest/                # pipeline.py (privacy gate, splits, embeddings), normalize.py
web/src/
├── pages/                 # operator, WhatsApp (simulated intake), expert, Live Docs, dashboard
├── api.ts                 # frontend API boundary
└── useJobRun.ts           # asynchronous job polling
scripts/                   # seed_demo.py, reset_demo.py, build_golden_set.py

packages/core/tests/       # shared domain fixtures in conftest.py
apps/api/tests/            # REST, WebSocket, and job contract tests
apps/worker/tests/
apps/pipeline/tests/       # privacy gate tests
conftest.py                # repo-root /data isolation fixture
```

**Structure Decision**: Preserve the existing uv workspace boundaries and
document contracts at the feature level. Shared domain entities and lifecycle
rules remain in `packages/core`; API, worker, pipeline, and web layers consume
them. The baseline plan does not move code across these boundaries.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| Principle I: lifecycle transitions are not auditable (no history in `kedb_articulos`) | The baseline documents current behavior. Adding an audit table changes the schema, the API, and probably the ADR set, which is a separate feature. | Silently marking principle I as PASS would misreport the code; changing the store inside a documentation baseline would hide a schema change. Resolve through a dedicated KEDB lifecycle audit trail spec before implementation of follow-ups that depend on it. |

## Risks

| ID | Risk | Effect | Mitigation or owner |
| -- | ---- | ------ | ------------------- |
| R1 | No lifecycle audit trail | Cannot show who validated, edited, or archived an article; principle I is unmet | Follow-up audit trail spec; tracked deviation above |
| R2 | Vector-store failures are logged and swallowed by `RAGAgent` | Outages look like no-hit results; evaluation counts them as misses, deflating the Recall@5 proxy | Follow-up retrieval failure signalling spec; pinned by a characterization test |
| R3 | Publication is not atomic and nothing re-projects a validated article | Live Docs and vector index can disagree (observed live) | Report divergence; a re-projection path belongs to a follow-up spec |
| R4 | Failed ARQ jobs report `status = complete` | Clients that read only `status` treat a failed evaluation as finished | Document `success`/`error`; contract now states it |
| R5 | Recall@5 is a proxy and the general evaluation cache can be stale or unrefreshable | Coordinator could read an old number as current | `tipo_evidencia`, `fuente`, `metodo`, `dataset` shown with every value |
| R6 | Privacy gate re-checks structured PII only | A missed personal name passes the gate | Independent residual-PII audit in the privacy hardening spec |
| R7 | No frontend test runner | UI regressions are caught only by `tsc && vite build` and the route smoke check | Accepted by project decision |
| R8 | Cold first ticket request can reach the 30 s target | SC-001 met warm, not guaranteed cold | Measure and document under a named service configuration |

Validation commands for this baseline are `uv run pytest`, `uv run ruff check .`,
and `npm run build` from `web/`; the quickstart lists the service-backed checks.
