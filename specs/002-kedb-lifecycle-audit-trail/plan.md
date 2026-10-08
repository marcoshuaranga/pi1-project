# Implementation Plan: KEDB Lifecycle Audit Trail

**Branch**: `002-kedb-lifecycle-audit-trail` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-kedb-lifecycle-audit-trail/spec.md`

## Summary

Record every KEDB article creation, state change, content edit, publication effect, and deletion as an append-only entry in the same SQLite database as the articles. Transition and edit entries commit in the same transaction as the change, so a change never exists without its record; publication effects are appended afterwards and linked to their cause. History is readable per article and across articles through two new routes, and the expert view gains an actor field, a required rejection reason, and a history section. Lifecycle rules, existing responses, and authentication are untouched. This closes the principle I deviation tracked as risk R1 in [spec 001](../001-mvp-closed-assistance-kedb-loop/plan.md).

## Technical Context

**Language/Version**: Python 3.11+ backend; TypeScript/React frontend

**Primary Dependencies**: FastAPI, Pydantic, SQLite (stdlib `sqlite3`), React, Vite. No new dependencies.

**Storage**: A new table `kedb_auditoria` (plus triggers and two indexes) in the existing KEDB SQLite database, created with `CREATE ... IF NOT EXISTS` like the other tables. No data migration and no backfill.

**Testing**: pytest with FastAPI test client and temporary SQLite files (as in `apps/api/tests/test_kedb_lifecycle_contract.py`); `npm run build` for the frontend (no frontend test runner by decision).

**Target Platform**: Linux containers and local Windows development.

**Project Type**: uv workspace monorepo; shared domain in `packages/core`, delivery in `apps/api`, UI in `web/`.

**Performance Goals**: Opening an article with 500 entries returns its history in under 2 seconds (SC-003). A single indexed query on `(articulo_id, id)` is expected to be orders of magnitude faster; verified by a test with 500 entries.

**Constraints**: Backward compatible responses for successful requests (FR-015). Transition and edit entries are atomic with the change (FR-005). Entries are immutable (FR-006). Actor is self-declared and never presented as verified (FR-008). Free text in `actor` and `motivo` is not screened for personal data.

**Scale/Scope**: Hundreds of articles, tens of entries each. Retention is indefinite.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

- PASS: Principle I is the purpose of this feature. It adds auditability without touching the state machine or the approval boundary. Residual: because actor identity is declared, not verified, auditability is operational, not non-repudiable. Recorded in the spec's Assumptions and not hidden.
- PASS: Principle II. The trail stores no ticket text or historical data. It stores user-entered free text; the limit is documented and the view warns against personal data.
- PASS: Principle III. Entry kinds, fields, and routes use Spanish domain terms (`RegistroAuditoria`, `cambio_estado`, `motivo`, `historial`).
- PASS: Principle IV. `RegistroAuditoria`, `ContextoAuditoria`, and the table live in `packages/core`; routes in `apps/api`; the view consumes only the published routes.
- PASS: Principle V. Each story has an independent test; schema, REST contract, and lifecycle rules get contract and integration coverage (see Validation).
- PASS: ADR check. Nothing adopted by an ADR changes (SQLite, FastAPI, state machine). No new ADR is required. One decision is worth an ADR if reviewers want it recorded: enforcing append-only with database triggers.

**Post-design re-check (after Phase 1)**: unchanged. Design stays inside the existing store, adds no dependency, and does not import from apps into core.

## Project Structure

### Documentation (this feature)

```text
specs/002-kedb-lifecycle-audit-trail/
├── spec.md
├── plan.md              # This file
├── research.md          # 10 decisions
├── data-model.md        # RegistroAuditoria, ContextoAuditoria, HistorialArticulo
├── quickstart.md
├── contracts/auditoria.md
├── checklists/requirements.md
└── tasks.md             # Created by /speckit-tasks
```

### Source Code (repository root)

```text
packages/core/src/pi_core/
├── schemas/__init__.py                 # RegistroAuditoria, ContextoAuditoria, HistorialArticulo
└── storage/kedb_store/
    ├── store.py                        # table + triggers; transactional create/update/delete; history and listing reads
    └── auditoria.py                    # (new) entry building, validation of actor/motivo, effect appending
packages/core/src/pi_core/services/
└── kedb_publisher.py                   # report per-destination outcomes to the store

apps/api/src/pi_api/routers/kedb.py     # actor/motivo inputs, 422/503 mapping, /historial and /auditoria routes
apps/worker/src/pi_worker/tasks.py      # no change expected; generator creates drafts through KedbStore.create with sistema context
packages/core/src/pi_core/agents/kedb_generator/agent.py   # pass system context on create
packages/core/src/pi_core/fixtures/kyocera_demo.py          # pass system context on create/delete

web/src/
├── api.ts                              # types and calls
└── pages/ExpertPage.tsx                # actor field, rejection reason, history section

packages/core/tests/                    # store atomicity, triggers, ordering, no-op edit, effects
apps/api/tests/                         # contract tests for new inputs and routes
```

**Structure Decision**: Keep all persistence inside `KedbStore` so atomicity is a property of one connection. A new module `auditoria.py` keeps entry construction and validation out of the already large `store.py`. No new package and no cross-app imports.

### Call sites that write articles (all must carry an audit context)

| Call site | Context |
| :--- | :--- |
| `routers/kedb.py` `update_articulo` (also reached by `ciclo_vida`) | Request `actor`/`motivo`. |
| `agents/kedb_generator/agent.py` `store.create` | `sistema`, reason "generación automática". |
| `fixtures/kyocera_demo.py` `store.create` / `store.delete` | `sistema`, reason "fixture de demo". |

`KedbStore.create/update/delete` take a required `ContextoAuditoria`; making it required, not optional, is what guarantees no write path silently skips the trail.

## Complexity Tracking

No constitution violations. One accepted limitation is carried from the spec: effect entries are appended after the transition commits and can fail independently (research Decision 6).

## Risks

| ID | Risk | Effect | Mitigation |
| -- | ---- | ------ | ---------- |
| R1 | Making `ContextoAuditoria` required breaks existing callers and tests | Failing tests, broken scripts | Update the three call sites and test helpers in the same task; ruff and the full suite gate the change |
| R2 | `BEGIN IMMEDIATE` serializes writers | Brief waits under concurrent edits | Acceptable at current volume; set a busy timeout and test two concurrent writers |
| R3 | An effect entry fails to append after a successful publication | Trail shows the transition but not its publication outcome | Log and return the failure in the response; the destinations are still discoverable by comparing Live Docs and retrieval |
| R4 | Database triggers can be dropped by someone with file access | Entries could be altered | Stated as a limit; not a security boundary |
| R5 | Free-text reasons may contain personal data | Privacy exposure in the trail | View warning, length limit, and the documented assumption; follow up in the privacy hardening work |
| R6 | Declared actors can be mistyped or impersonated | Misleading history | Always displayed as "declarado"; verified identity awaits an authentication feature |
| R7 | Unfiltered rows from demo resets (`eliminacion`) clutter the listing | Noise for coordinators | `tipo` filter on the listing |

## Spec reconciliations found while planning

1. The expert view offers approve and reject only; nothing in the web app archives an article. FR-012 and User Story 3 are reworded to require a reason on reject in the view, with the archive reason enforced by the API.
2. Demo resets delete articles, so `eliminacion` is added as an entry kind.

## Validation

`uv run pytest`, `uv run ruff check .`, `npm run build` from `web/`, and the live checks in [quickstart.md](quickstart.md). Key automated cases: atomic rollback when the insert fails, trigger-enforced immutability, two concurrent transitions recorded in order, no entry on refused requests, no entry on a no-op edit, unchanged responses for successful requests, and history of a deleted article.
