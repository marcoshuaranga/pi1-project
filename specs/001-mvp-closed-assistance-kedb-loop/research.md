# Research: Implemented Closed Assistance-KEDB Loop

## Decision 1: Treat the first feature as a current-state baseline

- **Decision**: Specify the behavior that exists in the repository today, while labelling target and aspirational behavior explicitly.
- **Rationale**: The PRD and implementation have drifted. A future-state spec would create false coverage and make generated tasks misleading.
- **Alternatives considered**: Rewriting the PRD as the only specification; rejected because it would not describe current API, worker, and frontend behavior. Treating only the original MVP as shipped; rejected because dashboard, search, feedback, lifecycle, and Live Docs paths are already implemented.

## Decision 2: Preserve the existing monorepo ownership boundaries

- **Decision**: Keep shared models and domain logic in `packages/core`; keep HTTP/WebSocket delivery in `apps/api`, asynchronous jobs in `apps/worker`, ingestion in `apps/pipeline`, and UI in `web/`.
- **Rationale**: ADR-0010 and the repository structure establish one-way dependencies. The constitution makes this boundary mandatory.
- **Alternatives considered**: Moving route-specific logic into core; rejected because it would couple the shared domain package to an application layer.

## Decision 3: Treat human validation as the KEDB publication gate

- **Decision**: Only `validado` articles may be reused by RAG or projected as Live Docs. Draft, obsolete, and archived articles remain excluded from validated knowledge.
- **Rationale**: The lifecycle store and publisher enforce this product safety rule, and it is required by the constitution.
- **Alternatives considered**: Publishing generated drafts automatically; rejected because it bypasses expert governance and conflicts with the domain workflow.

## Decision 4: Label metric evidence by semantics and source

- **Decision**: Keep F1, Recall@5, Kappa, response time, and privacy outcomes distinguishable as measured values, targets, or proxies, including the dataset and evaluation type.
- **Rationale**: The repository contains cached evaluation results and golden-set endpoints, while demo documentation identifies limitations in some metric semantics.
- **Alternatives considered**: Treating all PRD numbers as current acceptance evidence; rejected because it would overstate the evidence and violate the constitution.

## Decision 5: Record known architecture gaps as follow-up features

- **Decision**: Do not claim conditional routing or KEDB internal-coherence filtering as shipped in this baseline. Track them as separate feature specifications.
- **Rationale**: ADR-0006 describes conditional routing, but the current graph is sequential; ADR-0005 records that coherence filtering is incomplete.
- **Alternatives considered**: Expanding this baseline to implement the gaps; rejected because it mixes reverse-engineering with new product work and obscures independent acceptance.

## Decision 6: Use the existing asynchronous job boundary

- **Decision**: Treat KEDB generation and evaluation as queued operations with observable job status and results.
- **Rationale**: API routes enqueue ARQ jobs and the worker owns long-running work. This prevents the web/API contract from pretending these operations are synchronous.
- **Alternatives considered**: Making generation synchronous in the baseline; rejected because it contradicts the current runtime behavior and risks request timeouts.

## Decision 7: Withdraw reusable knowledge when validation is lost

- **Decision**: Leaving `validado` (to `obsoleto` or `archivado`) deletes the Markdown projection and the vector entry; the API only unpublishes when the previous state was `validado`.
- **Rationale**: Publication wrote both projections on approval but nothing removed them, so an archived article stayed searchable and listed in Live Docs, contradicting FR-006. Drafts never touch the projections, so editing a draft does not depend on Chroma being up.
- **Alternatives considered**: Filtering by SQLite state at read time; rejected because Live Docs and vector retrieval read their own stores and would each need a join. Rewriting the Markdown with the new state; rejected because the docs view is defined as validated-only.

## Decision 8: Default evidence kind is `proxy`

- **Decision**: `MetricasEvaluacion.tipo_evidencia` is constrained to `medido | objetivo | proxy` and defaults to `proxy`, including for legacy caches and the no-cache empty response.
- **Rationale**: An earlier default of `medido` would have labelled old caches and zero-sample placeholders as measurements, the exact confusion the constitution forbids.
- **Alternatives considered**: A fourth `desconocido` value; rejected as unnecessary since every stored value so far comes from the same proxy method.

## Boundary check (T008)

`grep` for `pi_api`, `pi_worker`, and `pi_pipeline` imports under `packages/core/src` finds none, so `pi_core` does not depend on application packages. No exception to document.

## Open follow-up research

- Define the authoritative Recall@5 ground-truth semantics and golden-set annotation procedure.
- Replace the regex-only privacy gate with an independent residual-PII audit that also covers names; the current gate only re-checks the anonymizer's own patterns.
- Decide the acceptance behavior for concurrent article edits and version conflicts.
- Measure the 30-second assistance target under a documented service configuration.
