# Data Model: Implemented Closed Assistance-KEDB Loop

## Ticket

Represents an anonymized help-desk request and its assistance result.

- Identity: stable `ticket_id`.
- Input: anonymized ticket text.
- Result: category, confidence, priority, and ordered solution suggestions.
- Lifecycle: submitted, processing, completed, or failed as represented by the
  ticket status workflow.
- Resolution: optional applied solution recorded for future KEDB work.
- Feedback: optional usefulness and new-solution information.

Validation rules:

- Input must contain valid ticket text.
- Historical ticket text must pass anonymization before indexing or evaluation.
- A missing ticket must produce a not-found result rather than an empty success.

## Pipeline Event

Represents observable progress or failure for a ticket processing stage.

- Identity: event identifier and timestamp.
- Association: `ticket_id` and pipeline stage/agent.
- Outcome: start, completion, or error.
- Context: stage input/output metadata suitable for UI progress and diagnosis.

Events are delivery records, not authority to mutate a ticket or publish KEDB.

## KEDB Article

Represents a candidate or reusable operational knowledge article.

- Identity: `articulo_id`.
- Content: title, symptom, category, probable cause, solution, and applicability.
- Traceability: one or more `tickets_fuente` references.
- Lifecycle: `borrador`, `validado`, `obsoleto`, or `archivado`.
- Quality: generation metadata and optional expert quality information.
- Publication: Markdown/Live Docs projection only when policy permits it.

Rules:

- Draft generation may be asynchronous.
- Expert edits preserve source-ticket traceability.
- Invalid state transitions are rejected without mutating the article.
- Rejection transitions the article from `borrador` to `obsoleto`.
- Only `validado` articles are eligible for reusable KEDB retrieval and Live Docs.
- Permitted transitions: `borrador -> validado | obsoleto`,
  `validado -> obsoleto | archivado`, `obsoleto -> archivado`; `archivado` is
  terminal.
- Entering or staying in `validado` publishes the Markdown and vector projections;
  leaving `validado` withdraws both.

## Job

Represents an asynchronous KEDB generation or evaluation operation.

- Identity: `job_id`.
- Task: generation, evaluation, or golden-set evaluation.
- Status: queued, running, completed, or failed.
- Result: task-specific output or error details.

A queued job response is not evidence that the task completed successfully.

## Evaluation Result

Represents a metric calculation tied to an explicit evidence source.

- Metric values: F1 macro, Recall@5, and optional Kappa.
- Context: dataset/evaluation type, sample size, and calculation timestamp.
- Semantics: `tipo_evidencia` is `medido`, `objetivo`, or `proxy` (default
  `proxy`), with `fuente`, `metodo`, and `dataset` describing where the value came
  from. Current evaluators emit `proxy`.

The baseline does not redefine the ground-truth semantics of Recall@5; that is a
follow-up evaluation-methodology feature.

## Privacy Validation Record

Represents the gate applied before historical data is used downstream.

- Input dataset/sample identity.
- Validation outcome.
- Detection summary and timestamp.
- Downstream permission: allowed or blocked.

A failed privacy validation prevents indexing, embedding, evaluation, and display
of the affected historical data.

**Current implementation**: this entity is conceptual. The gate is
`validate_anonymized_texts` in `pi_core.anonymize.anonymizer`, called by the
ingestion pipeline's `run_anonymize` (before the parquet is written) and
`run_ingest` (before splits and embeddings). A failure raises `ValueError` with
only a match count, never the matched text; no record is persisted. It checks the
anonymizer's structured-PII patterns only (see the spec's Known Limitations).

## Relationships

- One Ticket may produce many Pipeline Events.
- One KEDB Article references one or more source Tickets.
- One Ticket may receive feedback and later contribute a resolution to KEDB work.
- One Job produces an Evaluation Result or a set of KEDB Articles.
- A Privacy Validation Record gates the historical Tickets used by indexing and
  evaluation.
