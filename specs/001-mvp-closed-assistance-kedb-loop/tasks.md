---
description: "Task list for validating the reverse-engineered closed assistance-KEDB loop"
---

# Tasks: Implemented Closed Assistance-KEDB Loop

**Input**: Design documents from `/specs/001-mvp-closed-assistance-kedb-loop/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Organization**: Tasks are grouped by user story so each journey can be validated independently.

## Constitution Alignment

- The plan and story phases preserve human KEDB approval, privacy gates, canonical
  lifecycle states, and `packages/core`/application boundaries.
- Setup, foundational, and polish tasks are cross-cutting quality gates required
  by the constitution; all product behavior tasks are grouped under an
  independently testable user story.
- Metric tasks must distinguish measured, target, and proxy evidence rather than
  treating cached or demo values as production-quality results.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the Spec Kit validation baseline without changing product architecture.

- [x] T001 Confirm the feature artifact set and source-of-truth links in `specs/001-mvp-closed-assistance-kedb-loop/plan.md` and `README.md`
- [x] T002 [P] Record the baseline validation commands and service prerequisites in `specs/001-mvp-closed-assistance-kedb-loop/quickstart.md`
- [x] T003 [P] Map the current API, WebSocket, job, and frontend surfaces to `specs/001-mvp-closed-assistance-kedb-loop/contracts/`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared evidence and contract checks before validating individual journeys.

- [x] T004 Add a constitution compliance checklist for privacy, human approval, domain terminology, and `packages/core` boundaries in `specs/001-mvp-closed-assistance-kedb-loop/checklists/constitution.md`
- [x] T005 [P] Add shared API test fixtures for the FastAPI ticket, KEDB, jobs, and metrics routes in `apps/api/tests/conftest.py`
- [x] T006 [P] Add shared domain fixtures for Ticket, Pipeline Event, KedbArticulo, Job, and metric evidence in `packages/core/tests/conftest.py`
- [x] T007 Verify that baseline tests run in member-owned environments with `uv run pytest packages/core/tests`, `uv run pytest apps/api/tests`, and `uv run pytest apps/worker/tests` in `docs/operations/setup.md`
- [x] T008 Verify that `packages/core` does not import application packages and document any exception in `specs/001-mvp-closed-assistance-kedb-loop/research.md`

**Checkpoint**: Shared fixtures, constitution checks, and member-scoped validation are ready before story-specific work.

## Phase 3: User Story 1 - Operator Assistance (Priority: P1)

**Goal**: Prove that a valid anonymized ticket produces an honest, traceable assistance result.

**Independent Test**: Submit a valid ticket through the API test client, inspect the returned category, confidence, priority, suggestions, and status, and verify failure behavior for invalid or unavailable processing.

- [x] T009 [US1] Add contract tests for `POST /tickets` and `GET /tickets/{ticket_id}` in `apps/api/tests/test_ticket_assistance_contract.py`
- [x] T010 [P] [US1] Add pipeline event contract tests for `WS /ws/pipeline/{ticket_id}` in `apps/api/tests/test_pipeline_websocket_contract.py`
- [x] T011 [P] [US1] Add core acceptance tests for classifier, prioritizer, and RAG result shape in `packages/core/tests/test_assistance_contract.py`
- [x] T012 [US1] Verify no-hit (`test_create_ticket_returns_explicit_empty_result_when_nothing_matches`, `test_retrieve_returns_empty_list_when_nothing_matches`), invalid-input (422), and missing-ticket (404) behavior in `apps/api/tests/test_ticket_assistance_contract.py` and `packages/core/tests/test_rag_retrieval.py`, and the failed-pipeline behavior of the WebSocket route in `apps/api/tests/test_pipeline_websocket_contract.py`. The synchronous `POST /tickets` failure path has no test (see Known Limitations)
- [x] T013 [US1] DESCOPED: `web/` has no test runner by project decision; guarded by `npm run build` and the quickstart route smoke check. (was: operator UI acceptance test in `web/src/pages/OperatorPage.test.tsx`)
- [x] T014 [US1] Update `specs/001-mvp-closed-assistance-kedb-loop/contracts/tickets.md` with observed response fields and error semantics after tests are run

**Checkpoint**: User Story 1 is independently testable through API/core/UI evidence.

## Phase 4: User Story 2 - Expert KEDB Validation (Priority: P1)

**Goal**: Prove that experts can review articles and that lifecycle rules protect reusable knowledge.

**Independent Test**: Create a draft article, edit it, approve or reject it, attempt invalid transitions, and verify state plus traceability after every action.

- [x] T015 [US2] Add article lifecycle contract tests for `GET /kedb/articulos`, `GET /kedb/articulos/{articulo_id}`, and `PATCH /kedb/articulos/{articulo_id}` in `apps/api/tests/test_kedb_lifecycle_contract.py`
- [x] T016 [P] [US2] Verify invalid-transition and persistence coverage for `InvalidEstadoTransition` in `apps/api/tests/test_kedb_fsm.py`
- [x] T017 [P] [US2] Verify source-ticket traceability integrity coverage in `apps/api/tests/test_kedb_integrity.py`
- [x] T018 [US2] DESCOPED: `web/` has no test runner by project decision; guarded by `npm run build` and the quickstart route smoke check. (was: `web/src/pages/ExpertPage.test.tsx`)
- [x] T019 [US2] Verify only validated articles are sent to the publisher in `packages/core/tests/test_kedb_publisher.py`
- [x] T020 [US2] Update `specs/001-mvp-closed-assistance-kedb-loop/contracts/kedb.md` with observed transition and publication semantics

**Checkpoint**: User Story 2 is independently testable and human approval remains mandatory.

## Phase 5: User Story 3 - Validated Knowledge Reuse (Priority: P1)

**Goal**: Prove that validated knowledge is reusable and unvalidated knowledge is excluded.

**Independent Test**: Approve one article, search for related knowledge, and verify its appearance; repeat with a draft or archived article and verify exclusion.

- [x] T021 [US3] Verify retrieval-state filtering and fallback safety in `packages/core/tests/test_rag_retrieval.py`
- [x] T022 [P] [US3] Add contract tests for `GET /kedb/buscar` in `apps/api/tests/test_kedb_search_contract.py`
- [x] T023 [P] [US3] Verify Live Docs publication/exclusion for `GET /kedb/docs` and `GET /kedb/docs/{articulo_id}` in `apps/api/tests/test_kedb_markdown.py`
- [x] T024 [US3] DESCOPED: `web/` has no test runner by project decision; guarded by `npm run build` and the quickstart route smoke check. (was: `web/src/pages/DocsPage.test.tsx`)
- [x] T025 [US3] Update `specs/001-mvp-closed-assistance-kedb-loop/contracts/kedb.md` with verified retrieval and publication filters

**Checkpoint**: User Story 3 demonstrates the closed-loop reuse boundary.

## Phase 6: User Story 4 - Operational Visibility (Priority: P2)

**Goal**: Prove that dashboard and evaluation views expose contextual evidence without overstating targets.

**Independent Test**: Load dashboard and cached evaluation data, request recomputation jobs, and verify dataset, timestamp, sample, metric, and target/measured labelling.

- [x] T026 [US4] Verify dashboard response coverage for `GET /metrics/dashboard` in `apps/api/tests/test_api_smoke.py`
- [x] T027 [P] [US4] Add general and golden evaluation contract tests for `GET/POST /metrics/evaluacion` and `GET/POST /metrics/evaluacion-golden` in `apps/api/tests/test_metrics_evaluation_contract.py`
- [x] T028 [P] [US4] Add job status/result contract tests for generation and evaluation jobs in `apps/api/tests/test_jobs_contract.py`
- [x] T029 [US4] Add metric-semantic validation tests for target, measured, and proxy labels in `packages/core/tests/test_evaluation_evidence.py`
- [x] T030 [US4] DESCOPED: `web/` has no test runner by project decision; guarded by `npm run build` and the quickstart route smoke check. The dashboard now renders `tipo_evidencia`, dataset, and method (see T048). (was: `web/src/pages/DashboardPage.test.tsx`)
- [x] T031 [US4] Update `specs/001-mvp-closed-assistance-kedb-loop/contracts/metrics.md` with verified evidence fields and limitations

**Checkpoint**: User Story 4 exposes operational evidence without conflating targets with measurements.

## Phase 7: User Story 5 - Privacy-Gated Historical Knowledge (Priority: P1)

**Goal**: Prove that anonymization gates historical data before downstream use.

**Independent Test**: Process a representative fixture, inspect anonymized output, and verify that a failed privacy check blocks downstream processing.

- [x] T032 [US5] Verify anonymization acceptance coverage for structured identifiers and names in `packages/core/tests/test_anonymizer_basic.py` and `packages/core/tests/test_anonymization_dod.py`
- [x] T033 [P] [US5] Add ingestion gate tests proving failed privacy validation blocks indexing/embedding in `apps/pipeline/tests/test_privacy_gate.py`
- [x] T034 [P] [US5] Add committed-fixture scanning coverage for raw PII policy in `packages/core/tests/test_privacy_artifacts.py`
- [x] T035 [US5] Add pipeline quickstart validation for anonymize-before-index ordering in `apps/pipeline/tests/test_privacy_gate.py`
- [x] T036 [US5] Update `specs/001-mvp-closed-assistance-kedb-loop/quickstart.md` with the verified privacy validation command and expected failure behavior

**Checkpoint**: User Story 5 establishes privacy as a blocking precondition.

## Phase 8: Polish and Cross-Cutting Concerns

- [x] T037 [P] Run `/speckit-analyze` and resolve critical or high findings in `specs/001-mvp-closed-assistance-kedb-loop/spec.md`, `plan.md`, or `tasks.md` (re-run 2026-09-24: 1 critical, 2 high, 9 medium/low; see T052 and the plan's Complexity Tracking. The critical finding is a tracked constitution deviation, so `/speckit-implement` stays gated on the audit-trail decision)
- [x] T038 [P] Reconcile implemented capabilities and stale phase labels in `PRD.md` without moving architecture decisions out of ADRs
- [x] T039 [P] Add cross-links from `docs/README.md`, `README.md`, and `specs/001-mvp-closed-assistance-kedb-loop/quickstart.md`
- [x] T040 Run `uv run pytest` and `uv run ruff check .` from the repository root and record results in the feature review (see Validation Record)
- [x] T041 Run `npm run build` from `web/` and record results in the feature review
- [x] T042 Run the documented Docker/demo smoke path from `specs/001-mvp-closed-assistance-kedb-loop/quickstart.md` (run 2026-09-24; results and findings in the Validation Record)
- [x] T043 [US1] Verify the 30-second assistance target measurement path in `packages/core/tests/test_pipeline_latency.py`; live measurement remains service-dependent and is labelled as an integration check
- [x] T044 [US4] Extend `MetricasEvaluacion` and the metrics API responses in `packages/core/src/pi_core/schemas/__init__.py` and `apps/api/src/pi_api/routers/metrics.py` with evidence kind and method/source context, then cover the fields in `apps/api/tests/test_metrics_evaluation_contract.py`
- [x] T045 [US3] Withdraw the Markdown and vector projections when a validated article moves to `obsoleto` or `archivado` in `apps/api/src/pi_api/routers/kedb.py`, `packages/core/src/pi_core/services/kedb_publisher.py`, `packages/core/src/pi_core/storage/kedb_store/`, and `packages/core/src/pi_core/agents/rag/agent.py`, covered by `apps/api/tests/test_kedb_lifecycle_contract.py` and `packages/core/tests/test_kedb_publisher.py`
- [x] T046 [US4] Default evidence kind to `proxy` and constrain it to `medido | objetivo | proxy`; report the no-cache response as an explicit empty proxy in `apps/api/src/pi_api/routers/metrics.py` and `packages/core/src/pi_core/schemas/__init__.py`, covered by `apps/api/tests/test_metrics_evaluation_contract.py`
- [x] T047 [US5] Re-run the privacy gate in `run_ingest` so a stale parquet cannot bypass it in `apps/pipeline/src/pi_pipeline/ingest/pipeline.py`, covered by `apps/pipeline/tests/test_privacy_gate.py`
- [x] T048 [US4] Show `tipo_evidencia`, dataset, and method next to the evaluation metrics in `web/src/pages/DashboardPage.tsx`
- [x] T049 Scope the `E402` ruff exemption to `scripts/*` in `pyproject.toml` so `uv run ruff check .` passes; the scripts bootstrap `sys.path` before importing `pi_core` on purpose
- [x] T050 [US1] Record the WhatsApp intake as a simulated entry point to the operator flow in `specs/001-mvp-closed-assistance-kedb-loop/spec.md`
- [x] T051 [US1] Pin the hidden-vector-store-failure behavior with `test_retrieve_hides_total_vector_store_failure_as_empty_result` in `packages/core/tests/test_rag_retrieval.py` so the limitation is executable
- [x] T052 Resolve the second `/speckit-analyze` run: record the missing lifecycle audit trail, hidden retrieval failures, failed-jobs-report-complete, and last-write-wins in `spec.md`; add the Constitution Check deviation, Complexity Tracking row, and Risks table to `plan.md`; align `data-model.md`, `contracts/kedb.md`, and `quickstart.md` with the real ticket, event, and job statuses

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 has no dependencies.
- Phase 2 depends on Phase 1 and blocks all user stories.
- User Stories 1, 2, 3, and 5 depend on Phase 2 and can proceed in parallel when fixtures are stable.
- User Story 3 relies on the lifecycle behavior validated by User Story 2, although its retrieval tests remain independently runnable with seeded fixtures.
- User Story 4 depends on Phase 2 and can proceed in parallel with User Stories 1-3.
- Phase 8 depends on the desired user stories being validated.

### User Story Dependencies

- **US1**: Starts after Phase 2; no story dependency.
- **US2**: Starts after Phase 2; no story dependency.
- **US3**: Starts after Phase 2; uses validated/draft fixtures from the lifecycle model and should also be checked after US2.
- **US4**: Starts after Phase 2; no story dependency.
- **US5**: Starts after Phase 2; no story dependency and should block any data-dependent implementation work.

### Parallel Opportunities

- T002-T003 can run in parallel during setup.
- T005-T006 can run in parallel during foundation.
- T010-T011, T016-T017, T022-T023, T027-T029, and T033-T034 can run in parallel because they touch separate test surfaces.
- US1, US2, US4, and US5 can be staffed in parallel after foundation; US3 can start with seeded lifecycle fixtures.

## MVP Scope

The minimum evidence slice is Phase 2 plus User Story 1 and User Story 5: a valid
privacy-gated ticket produces honest assistance results. The complete product
value slice adds User Stories 2 and 3: expert validation followed by validated
knowledge reuse. User Story 4 is operational support and can follow the core loop.

## Implementation Strategy

1. Establish shared fixtures, constitution checks, and member-scoped validation.
2. Validate operator assistance and privacy gates first.
3. Validate expert lifecycle governance and validated-article reuse.
4. Validate metrics/dashboard evidence semantics.
5. Run cross-artifact analysis and repository checks before implementing any
   follow-up architecture features.

## Validation Record

Recorded 2026-09-23 against the working tree (backend re-run 2026-09-24 after T051-T052):

- `uv run pytest`: 122 passed, 2 skipped (integration tests that need live services).
- `uv run ruff check .`: all checks passed.
- `npm run build` (from `web/`): passed.
### T042 Docker smoke (2026-09-24)

Stack rebuilt with `docker compose up --build -d api worker web` and exercised over
HTTP. A throwaway article (`KEDB-SMOKE-T042`) was used so the existing KEDB data was
left untouched (6 `borrador`, 3 `validado` before and after).

Passed:

- Lifecycle: `borrador -> archivado` returns 409; approving publishes; the article is
  searchable and in Live Docs while `validado`; after `archivado` it is gone from
  `/kedb/buscar` and `/kedb/docs` (doc `404`); `archivado -> validado` returns 409.
- Tickets: `POST /tickets` returns category, confidence, priority, and 5 ordered
  suggestions; `GET /tickets/{id}` is `completado`; short text is `422`; unknown id
  is `404`.
- Metrics: both evaluation endpoints return `tipo_evidencia = proxy`; the missing
  golden cache is an explicit empty proxy; the dashboard returns `200`.
- Web: `/`, `/whatsapp`, `/experto`, `/kedb`, `/docs`, `/dashboard` all serve `200`.
- SC-001 (30 s target): first request after restart took 30.3 s (cold); warm
  requests took 1.7-2.3 s. The target is met warm and not met cold.

Findings, none introduced by these changes:

- `POST /metrics/evaluacion` fails: the worker raises a Chroma HNSW error ("Cannot
  return the results in a contigious 2D array. Probably ef or M is too small") from
  `classifier/agent.py:39-46` on the 57,749-entry tickets collection. ARQ reports the
  job as `complete` while `/jobs/{id}/result` carries the error, and the API keeps
  serving the July 2026 cache (`recall_at_5 = 0.22`, no `fuente`/`metodo`).
- Validated article `KEDB-DCE86F1BCAAF` has a Live Docs file but no vector entry
  (the KEDB collection holds 2 of the 3 validated articles), so it is not
  retrievable. Nothing re-projects an existing validated article to the vector store.

## Notes

- The four frontend test tasks (T013, T018, T024, T030) are ticked as DESCOPED, not
  as tested: `web/` has no test runner by decision, so nothing exercises those
  pages beyond the build and the quickstart smoke check.
- Every task follows the required checkbox, sequential ID, optional `[P]`, story
  label for story work, and concrete file-path format.
- These tasks prioritize evidence and contract coverage for already implemented
  behavior. Conditional routing, KEDB coherence filtering, and revised metric
  methodology remain separate future features.
