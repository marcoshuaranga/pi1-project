# Constitution Compliance Checklist: Implemented Closed Assistance-KEDB Loop

**Purpose**: Verify implementation tasks preserve the project constitution
**Created**: 2026-09-23
**Feature**: [spec.md](../spec.md)

## Governance

- [x] CHK001 Human approval remains required before KEDB knowledge becomes reusable. Evidence: `test_kedb_lifecycle_contract.py`, `test_kedb_publisher.py`, `test_rag_retrieval.py`.
- [x] CHK002 Historical data passes anonymization before indexing, embedding, evaluation, or display. Evidence: `test_privacy_gate.py`. Scope: structured PII only; names are not re-checked (spec Known Limitations).
- [x] CHK003 Domain terms and lifecycle states match `CONTEXT.md` and `packages/core/src/pi_core/schemas/`. Evidence: `test_kedb_fsm.py`.
- [x] CHK004 Shared behavior remains in `packages/core`; application layers do not become core dependencies. Evidence: no `pi_api`, `pi_worker`, or `pi_pipeline` import under `packages/core/src` (research.md).
- [x] CHK005 REST, WebSocket, job, lifecycle, and privacy changes have focused contract or integration coverage. Evidence: `apps/api/tests/test_*_contract.py`, `apps/pipeline/tests/test_privacy_gate.py`.
- [x] CHK006 Measured, target, and proxy evidence are labelled distinctly. Evidence: `test_metrics_evaluation_contract.py`; dashboard shows `tipo_evidencia`, dataset, and method.

## Validation

- [x] CHK007 `uv run pytest` passes for the affected backend members. 119 passed, 2 skipped (integration, services not running).
- [x] CHK008 `uv run ruff check .` passes.
- [x] CHK009 `npm run build` passes from `web/` when frontend files are changed.
- [x] CHK010 No raw PII or unreviewed generated data artifacts are added. Evidence: `test_privacy_artifacts.py`; `data/raw`, `data/processed`, and `data/kedb/articles` are ignored.
