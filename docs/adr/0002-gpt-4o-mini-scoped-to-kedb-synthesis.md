# GPT-4o-mini, scoped to KEDB article synthesis

_Also referenced elsewhere in this repo as **ADR-02**._

GeneradorKEDB needs to synthesize free-text KEDB articles (symptom, cause, solution) from clusters of resolved tickets — the one place in the pipeline that genuinely needs LLM generation. We use GPT-4o-mini (OpenAI) for that step only. Classification, prioritization, and retrieval all stay on embeddings + similarity/heuristics instead of routing through the LLM.

Keeping the LLM out of the hot path (classify → prioritize → retrieve, target ≤30s end-to-end) keeps that path cheaper, more reproducible, and easier to measure (F1, Recall@5) than if every ticket triggered an LLM call. The LLM's variability is accepted only where free-text synthesis is the actual job.
