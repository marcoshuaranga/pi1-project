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

- PASS: The feature preserves human approval as the publication boundary for
  reusable KEDB knowledge.
- PASS: The feature treats anonymization as a prerequisite and does not add raw
  data or generated PII artifacts.
- PASS: The design keeps shared behavior in `packages/core` and application
  delivery in `apps/*`/`web/`.
- PASS: The specification labels target metrics, proxy metrics, demo fixtures,
  and aspirational conditional routing separately from measured behavior.
- PASS: The plan identifies contract/integration validation for shared schemas,
  REST, WebSocket events, jobs, lifecycle transitions, and privacy gates.
- PASS: No constitution violation requires complexity justification for this
  baseline documentation and validation feature.

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

| Violation | Why Needed                                                                                                | Simpler Alternative Rejected Because                                                   |
| --------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| None      | The baseline maps and validates an existing architecture rather than adding a new project or abstraction. | Existing package boundaries and direct local stores already satisfy the current scope. |
