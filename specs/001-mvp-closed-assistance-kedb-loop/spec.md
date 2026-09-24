# Feature Specification: Implemented Closed Assistance-KEDB Loop

**Feature Branch**: `001-mvp-closed-assistance-kedb-loop`

**Created**: 2026-09-23

**Status**: Baseline, reconciled with the code on 2026-09-23

**Input**: Reverse-engineer the currently implemented product into a Spec Kit
baseline specification before planning further changes.

This specification describes the behavior currently represented by the
repository. It is not a proposal to silently implement every statement in the
PRD. Behavior described as a target, demo fixture, proxy metric, or aspirational
architecture is marked explicitly below.

## User Scenarios & Testing _(mandatory)_

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Operator Assistance (Priority: P1)

As an operator, I want to submit a help-desk ticket and receive a category,
priority, and relevant prior solutions so that I can resolve recurring issues
without starting the investigation from zero.

**Why this priority**: This is the primary product value and the smallest
independently useful slice of the closed assistance loop.

**Independent Test**: Submit an anonymized ticket through the operator workflow,
wait for the pipeline result, and verify that the response contains a category,
priority, and an ordered list of suggested solutions. The test is valuable even
when KEDB generation is not running.

**Acceptance Scenarios**:

1. **Given** a valid ticket title and description, **When** the operator submits
   it, **Then** the system creates a ticket result with a category, confidence,
   priority, and suggested solutions.
2. **Given** the ticket pipeline is running, **When** the operator observes its
   progress, **Then** pipeline events identify the stages executed and the final
   result is available through the ticket status workflow.
3. **Given** similar historical tickets or validated KEDB articles exist,
   **When** assistance is generated, **Then** the suggestions are ordered by
   relevance and include enough source information for the operator to choose a
   resolution.
4. **Given** no usable match exists, **When** assistance is generated, **Then**
   the system returns an explicit empty or low-confidence result without
   presenting fabricated source evidence.
5. **Given** an operator starts from the simulated WhatsApp intake view,
   **When** they forward the conversation, **Then** its transcript is submitted
   to the same assistance flow as a directly typed ticket. There is no live
   WhatsApp integration in the baseline.

---

### User Story 2 - Expert KEDB Validation (Priority: P1)

As a technical expert, I want to review and change the lifecycle state of a KEDB
draft so that reusable operational knowledge is published only after human
validation.

**Why this priority**: Human validation is the product's safety and trust
boundary; without it, generated knowledge must not become reusable guidance.

**Independent Test**: Load a draft article, edit or reject it, and verify the
state transition and persisted content. Approve a separate draft and verify that
it becomes eligible for publication and retrieval.

**Acceptance Scenarios**:

1. **Given** a KEDB article in `borrador`, **When** an expert edits and saves it,
   **Then** the updated content remains associated with its source tickets and
   the article remains a draft.
2. **Given** a KEDB article in `borrador`, **When** an expert approves it, **Then**
   its state becomes `validado` and it is eligible for reusable retrieval and
   publication.
3. **Given** an article in a state that does not permit the requested transition,
   **When** a lifecycle change is attempted, **Then** the system rejects the
   transition and preserves the previous state.
4. **Given** a draft is rejected, **When** the expert completes the rejection,
   **Then** the article transitions to `obsoleto` and is not made available as
   validated knowledge.

---

### User Story 3 - Validated Knowledge Reuse (Priority: P1)

As an operator, I want a previously validated KEDB article to appear in a later
assistance result so that expert knowledge improves future ticket handling.

**Why this priority**: This proves the closed-loop product value rather than a
one-off generation or review workflow.

**Independent Test**: Approve a draft article, perform a semantically related
ticket search, and verify that the validated article is returned. Repeat with an
unvalidated draft and verify that it is excluded from reusable knowledge.

**Acceptance Scenarios**:

1. **Given** an article is `validado`, **When** an operator submits a related
   ticket or searches the KEDB, **Then** the article can appear with source and
   relevance information.
2. **Given** an article is `borrador`, `obsoleto`, or `archivado`, **When** an
   operator requests reusable knowledge, **Then** that article is not returned as
   a validated recommendation.
3. **Given** a validated article is published to the documentation view, **When**
   a user opens it, **Then** the displayed content identifies it as validated and
   preserves its traceability information.
4. **Given** a validated article, **When** an expert moves it to `obsoleto` or
   `archivado`, **Then** it stops appearing in KEDB search and Live Docs without
   waiting for a re-index or manual cleanup.

---

### User Story 4 - Operational Visibility (Priority: P2)

As a coordinator or maintainer, I want to inspect dashboard and evaluation
information so that I can understand system behavior and identify quality gaps.

**Why this priority**: Visibility supports operational decisions and evaluation,
but it is not required for the operator's primary assistance path.

**Independent Test**: Open the coordinator dashboard and evaluation views with
available processed data, then verify that displayed values correspond to the
available evaluation or operational records and distinguish measured values from
targets.

**Acceptance Scenarios**:

1. **Given** metrics data is available, **When** a coordinator opens the
   dashboard, **Then** the system displays current coverage, priority, and
   recurrence information.
2. **Given** an evaluation is requested, **When** the evaluation job completes,
   **Then** its result can be retrieved and identified by evaluation type and
   dataset.
3. **Given** a metric is a target rather than a measured result, **When** it is
   displayed or documented, **Then** it is labelled as a target and not reported
   as observed performance.

### User Story 5 - Privacy-Gated Historical Knowledge (Priority: P1)

As a system owner, I want historical ticket data anonymized before downstream
processing so that assistance and KEDB workflows do not expose personal data.

**Why this priority**: Privacy is a precondition for safe use of the historical
corpus and applies even when no user-facing feature is being changed.

**Independent Test**: Process a representative historical sample, inspect the
anonymized output and downstream index inputs, and verify that the privacy gate
blocks processing when residual personal data is detected.

**Acceptance Scenarios**:

1. **Given** a raw historical export, **When** it enters the processing flow,
   **Then** personal data is replaced or removed before indexing, embedding, or
   evaluation.
2. **Given** privacy validation fails, **When** downstream ingestion is requested,
   **Then** the ingestion does not proceed and the failure is observable.
3. **Given** processed data is included in a demo or test fixture, **When** it is
   committed or displayed, **Then** it contains no unreviewed personal data.

### Edge Cases

<!--
  These cases constrain the current-state contract and should be covered by
  acceptance or integration tests during planning.
-->

- A ticket is missing required text, is malformed, or exceeds the accepted input
  size.
- Classification, prioritization, retrieval, or an asynchronous job fails or
  times out; the user must receive an observable failure state rather than a
  fabricated success.
- There are no retrieval hits or all hits are below the usable relevance
  threshold.
- A requested ticket, article, job, metric, or documentation projection does not
  exist.
- An expert attempts an invalid KEDB lifecycle transition or edits an article
  concurrently with another update.
- A draft exists but its source tickets are missing, duplicated, or not
  traceable.
- A raw or partially anonymized input reaches an ingestion boundary.
- A demo seed or fixture is mistaken for a live KEDB generation result.

## Requirements _(mandatory)_

<!--
  Requirements describe observable product behavior. Implementation choices such
  as framework, database, queue, and model belong in plan and ADR artifacts.
-->

### Functional Requirements

- **FR-001**: The system MUST accept a valid ticket submission and return a
  traceable result containing classification, confidence, priority, and ordered
  solution suggestions.
- **FR-002**: The system MUST expose observable progress and terminal outcome for
  ticket processing, including failure states.
- **FR-003**: The system MUST preserve the source identity and relevance context
  for every returned solution suggestion.
- **FR-004**: The system MUST allow an expert to view, edit, approve, or reject a
  KEDB draft while preserving its source-ticket traceability.
- **FR-005**: The system MUST enforce valid KEDB lifecycle transitions and reject
  invalid transitions without mutating the article.
- **FR-006**: The system MUST exclude non-validated articles from reusable KEDB
  recommendations and documentation publication, including an article that was
  previously validated and then left the `validado` state.
- **FR-007**: The system MUST make validated articles searchable and reusable in
  later related-ticket assistance.
- **FR-008**: The system MUST expose operational dashboard and evaluation results
  with enough context to distinguish measured values, targets, datasets, and
  evaluation types.
- **FR-009**: The system MUST require anonymization before historical data is
  indexed, embedded, evaluated, or displayed.
- **FR-010**: The system MUST stop or quarantine downstream processing when
  privacy validation fails.
- **FR-011**: The system MUST expose failures for missing resources, invalid
  inputs, unavailable jobs, and unavailable external model or storage services
  without inventing successful results.
- **FR-012**: The system MUST retain an auditable association between generated
  KEDB articles and their source tickets.

### Key Entities _(include if feature involves data)_

- **Ticket**: A help-desk request with anonymized text, classification,
  confidence, priority, processing status, resolution, and feedback.
- **Pipeline Event**: A traceable status update for a processing stage, including
  ticket association, stage identity, outcome, and error context when applicable.
- **KEDB Article**: A reusable knowledge record with title, symptom, cause,
  solution, lifecycle state, quality information, and source-ticket references.
- **KEDB Lifecycle State**: The controlled states `borrador`, `validado`,
  `obsoleto`, and `archivado`, with permitted transitions enforced by the system.
- **Evaluation Result**: A metric result tied to a named dataset and evaluation
  type, with target and observed values kept distinguishable.
- **Job**: An asynchronous generation or evaluation operation with status, result,
  and failure information.
- **Privacy Validation Record**: Evidence that a dataset passed or failed the
  anonymization gate before downstream processing.

## Success Criteria _(mandatory)_

<!--
  These outcomes describe the baseline and its evidence boundaries. Values that
  are product targets rather than currently measured results are labelled as
  targets.
-->

### Measurable Outcomes

- **SC-001**: In a representative valid-ticket run, the operator receives a
  category, priority, and ordered solution result within the product target of
  30 seconds end-to-end. This is a target until measured by the evaluation
  workflow.
- **SC-002**: A validated KEDB article can be found in a later related-ticket
  assistance result, while an unvalidated draft cannot be returned as reusable
  knowledge.
- **SC-003**: All accepted KEDB articles retain one or more traceable source
  ticket references, and invalid lifecycle transitions are rejected.
- **SC-004**: A representative historical sample passes the privacy validation
  gate with zero detected residual personal data before downstream indexing.
  This is a target until the sample and detection methodology are recorded.
- **SC-005**: Evaluation results identify their dataset and metric semantics;
  target values are never presented as measured values.
- **SC-006**: An operator, expert, or coordinator can complete the relevant
  primary workflow without encountering an unlabelled terminal error in a
  supported environment.

## Assumptions

<!--
  These assumptions are deliberately explicit because the current repository
  contains both shipped behavior and older target language.
-->

- The baseline is a reverse-engineered current-state specification; it does not
  claim that every PRD target is already met.
- The supported historical corpus is anonymized before use and is primarily in
  Spanish; other languages and formal registers are outside this baseline.
- Demo fixtures and pre-seeded KEDB articles are evidence of a demo workflow, not
  proof that live clustering and synthesis are complete or deterministic.
- Conditional routing described in ADR-0006 is aspirational until the graph and
  tests implement it; the current baseline assumes the observed sequential path.
- Internal KEDB coherence filtering beyond the minimum cluster rule is a future
  capability and is not treated as shipped behavior here.
- Recall@5 proxies, F1 targets, Kappa, and response-time targets must be labelled
  according to their actual measurement status.
- Authentication, access governance, live GLPI integration, mobile support, and
  production support remain outside this baseline unless a later feature spec
  explicitly brings them into scope.
- Runtime operation depends on the existing repository setup, configured model
  and storage services, and the validation commands documented by the plan's
  quickstart artifact.

## Known Limitations (current state, not requirements)

These are true of the code today. They are recorded so later features can
address them; none is promoted to a requirement of this baseline.

- **Sequential orchestration**: the pipeline graph is a fixed
  anonymize -> classify -> prioritize -> rag chain; ADR-0006 conditional routing
  is not implemented (follow-up: conditional pipeline routing).
- **No KEDB coherence filtering** beyond the minimum cluster rule (follow-up:
  KEDB quality and coherence filtering).
- **Recall@5 is a proxy**: a hit means the retrieved suggestions contain the
  query ticket's own source ticket. Evaluation responses therefore carry
  `tipo_evidencia = proxy`; nothing is labelled `medido`. Kappa is computed only on
  the golden set and is absent (`null`) for the general evaluation (follow-up:
  evaluation methodology).
- **Privacy gate scope**: the ingestion gate re-applies the anonymizer's own
  structured-PII patterns (emails, DNI, IPs, phone numbers). It blocks
  non-idempotent or bypassed anonymization but cannot detect personal names the
  NER model missed. SC-004 stays a target until an independent residual-PII audit
  exists (follow-up: operational governance and privacy hardening).
- **Demo-only generation path**: `POST /kedb/seed-demo` creates a pre-seeded
  draft and is unauthenticated; it is not evidence that live clustering and
  synthesis work.
- **Non-atomic publication**: a failure in one publication projection leaves the
  stored lifecycle state changed while the projection is stale; there is no
  rollback or retry.
- **Synchronous ticket route**: `POST /tickets` does not record a failed ticket
  session on an unexpected pipeline error; only the WebSocket route does.
- **No frontend tests**: `web/` intentionally has no test runner. Frontend
  behavior is guarded by `npm run build` (type-check and bundle) and the route
  smoke check in the quickstart.

## Constitution Alignment

- **Human-Controlled Knowledge**: expert approval is required before an article
  becomes reusable; rejection transitions the article to `obsoleto`.
- **Privacy Before Processing**: historical data is anonymized before indexing,
  embedding, evaluation, or display, and failed validation blocks downstream use.
- **Canonical Domain Language**: domain state values remain `borrador`,
  `validado`, `obsoleto`, and `archivado`; English entity descriptions are
  explanatory translations of the canonical model names.
- **Clean Core and Application Boundaries**: implementation tasks preserve the
  existing `packages/core`, `apps/*`, and `web/` ownership boundaries.
- **Evidence-Based Delivery**: target, measured, and proxy metrics are explicitly
  distinguished, and each story has an independent validation path.
