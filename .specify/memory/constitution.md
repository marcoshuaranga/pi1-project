<!--
Sync Impact Report
- Version change: unratified scaffold -> 1.0.0
- Modified principles: replaced all five template placeholders with project rules
- Added sections: Product and Architecture Constraints; Development Workflow and Quality Gates
- Removed sections: none
- Follow-up TODOs: confirm whether 2026-09-23 should be replaced by a historical adoption date
-->

# OITSI-MTC RAG + KEDB Constitution

## Core Principles

### I. Human-Controlled Knowledge

The platform MUST assist operators and experts, but it MUST NOT close tickets,
publish reusable KEDB knowledge, or replace expert judgment autonomously. Only a
human-approved article may become reusable KEDB knowledge. Every KEDB lifecycle
transition MUST be auditable and MUST respect the domain state machine.

### II. Privacy Before Processing

Personal data MUST be anonymized before historical data is indexed, embedded,
evaluated, or shown in a user-facing workflow. Raw exports and generated
artifacts containing personal data MUST NOT be committed to the repository.
Privacy checks MUST be automated or documented as an explicit validation step,
and a failed privacy gate MUST block downstream ingestion.

### III. Canonical Domain Language

Product behavior MUST use the canonical terminology in `CONTEXT.md`, including
`Ticket`, `Orquestador`, `Clasificador`, `Priorizador`, `Agente RAG`,
`GeneradorKEDB`, and the lifecycle states `borrador`, `validado`, and
`obsoleto`/`archivado`. New domain models, contracts, and documentation MUST
preserve the existing Spanish terms rather than silently introducing synonyms.

### IV. Clean Core and Application Boundaries

Shared domain logic MUST live under `packages/core` and MUST remain independent
of application layers. `apps/api`, `apps/worker`, and `apps/pipeline` MAY depend
on `packages/core`; `packages/core` MUST NOT import from an app, and backend
apps MUST NOT depend on one another without an explicit architectural decision.
Frontend code under `web/` MUST consume published application contracts rather
than reaching into core internals.

### V. Evidence-Based Delivery

Every feature MUST have a testable specification, an independently verifiable
acceptance path, and evidence appropriate to its risk. Target metrics MUST be
labelled separately from measured metrics; a proxy or demo fixture MUST NOT be
reported as production-quality evidence. Changes to shared schemas, REST or
WebSocket contracts, asynchronous jobs, privacy gates, or lifecycle rules MUST
include focused contract or integration coverage.

## Product and Architecture Constraints

- The closed product loop is: anonymized historical data -> ticket assistance ->
  human resolution -> KEDB draft -> expert validation -> validated-article reuse.
- The system provides recommendations; the operator remains responsible for the
  final ticket decision and closure.
- An article in `borrador` MUST remain excluded from reusable KEDB retrieval until
  it reaches `validado` through the approved lifecycle.
- Python backend dependencies MUST be managed by the owning `uv` workspace member;
  frontend dependencies MUST be managed by `web/` with npm.
- Existing ADRs are authoritative for adopted technical decisions. A change to a
  framework, model, vector store, anonymization method, clustering approach, or
  pipeline architecture MUST update or add an ADR before implementation.
- Architecture described by an ADR but absent from the current implementation
  MUST be labelled aspirational in specifications and documentation. In
  particular, conditional routing and KEDB coherence filtering MUST NOT be
  represented as shipped behavior until verified in code and tests.
- Documentation MUST keep product requirements, architecture, operations, ADRs,
  and demo instructions in their designated locations rather than duplicating
  competing sources of truth.

## Development Workflow and Quality Gates

- New work MUST begin with a Spec Kit feature specification under `specs/` and
  proceed through specify, review, plan, review, tasks, and implementation gates.
- A plan MUST identify affected ownership boundaries, data entities, contracts,
  risks, and validation commands before implementation begins.
- Tasks MUST be organized by independently testable user story and MUST identify
  concrete file paths and dependencies.
- Python changes MUST pass `uv run pytest` and `uv run ruff check .`; frontend
  changes MUST pass `npm run build` from `web/`. Narrow tests SHOULD run first,
  followed by the applicable repository-wide checks.
- Before implementation, `/speckit-analyze` MUST report no unresolved critical
  constitution conflicts or uncovered baseline requirements.
- Reviews MUST check privacy, human approval, domain terminology, core/app
  boundaries, contract compatibility, and target-versus-measured evidence.

## Governance

This constitution supersedes conflicting repository practices for product and
engineering work. Every specification, plan, task set, and review MUST include
the applicable constitution check. A violation MUST be resolved in the artifact
or explicitly approved as a constitution amendment; it MUST NOT be silently
ignored.

Amendments require a written rationale, an updated Sync Impact Report, a semantic
version change, and review of affected specifications, plans, tasks, ADRs, and
validation commands. Versioning follows SemVer: MAJOR for incompatible rule
changes or removals, MINOR for new or materially expanded rules, and PATCH for
clarifications that do not change obligations. The last amended date MUST be
updated for every accepted amendment.

The constitution is reviewed whenever the architecture, data handling model,
approval workflow, or quality gates change. `AGENTS.md`, `CONTEXT.md`, the ADRs,
and the Spec Kit artifacts provide supporting guidance but cannot weaken these
rules.

**Version**: 1.0.0 | **Ratified**: 2026-09-23 | **Last Amended**: 2026-09-23
