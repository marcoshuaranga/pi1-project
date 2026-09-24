# Metrics and Evaluation Contract

Source of truth: `apps/api/src/pi_api/routers/metrics.py`,
`MetricasEvaluacion` in `packages/core/src/pi_core/schemas/__init__.py`, and
`packages/core/src/pi_core/evaluation/`. Verified by
`apps/api/tests/test_metrics_evaluation_contract.py` and
`packages/core/tests/test_evaluation_evidence.py`.

## Evaluation response shape

`GET /metrics/evaluacion` and `GET /metrics/evaluacion-golden` return
`MetricasEvaluacion`:

| Field | Meaning |
| :--- | :--- |
| `f1_macro`, `recall_at_5`, `kappa` | Metric values; `kappa` is `null` unless the golden set computed it. |
| `muestra_tickets` | Sample size the values were computed on. |
| `fecha_calculo` | Calculation timestamp. |
| `tipo_evidencia` | `medido`, `objetivo`, or `proxy`. Defaults to `proxy`. |
| `fuente` | Source artifact, for example `golden_set_sample.json`. |
| `metodo` | How the value was obtained. |
| `dataset` | `tickets_eval` for the general run, `golden_set` for the golden run. |

## General evaluation

- `GET /metrics/evaluacion` returns cached results from `evaluation_results.json`.
- `POST /metrics/evaluacion` enqueues recomputation (`202`, job identity).

## Golden-set evaluation

- `GET /metrics/evaluacion-golden` returns cached results from
  `evaluation_results_golden.json`, including inter-annotator Kappa.
- `POST /metrics/evaluacion-golden` enqueues golden-set recomputation.

## Missing or legacy caches

- With no cache file, the response is an explicit empty result: zero values,
  `muestra_tickets = 0`, `tipo_evidencia = "proxy"`, `metodo` stating that no
  results are cached, and the endpoint's `dataset`. It is not a measurement.
- A cache written before the evidence fields existed is reported as `proxy`, never
  as `medido`.

## Dashboard

`GET /metrics/dashboard?categoria=` returns operational coverage and
ticket/article summary. It reports current store contents, not evaluation evidence.

## Evidence rules

- Every `recall_at_5` produced by the current evaluators is a **proxy**: a hit is
  a suggestion that matches the query ticket's own source ticket. It measures
  retrieval self-consistency, not the share of operators who received a useful
  Top-5.
- `f1_macro` and `kappa` are calculated on the named dataset but are reported under
  the same response-level `tipo_evidencia`; no metric here is labelled `medido`
  until the evaluation-methodology feature defines ground truth.
- Targets from the PRD (F1, Recall@5, 30-second response time) are not evaluation
  results and must be labelled `objetivo` wherever they are shown.
- The web dashboard shows `tipo_evidencia`, `dataset`, and `metodo` next to the
  metric values.
