# LangGraph as the agent orchestration framework

_Also referenced elsewhere in this repo as **ADR-01**._

A ticket's pipeline runs through five agents (Clasificador, Priorizador, Agente RAG, GeneradorKEDB, Orquestador) that need an explicit order, conditional branching (skip RAG, escalate on high priority), and a per-step event emitted to the UI over WebSocket. We chose LangGraph to model this as an explicit state graph, instead of a single LLM prompt handling classification, scoring and retrieval together, or hand-rolled imperative coordination code.

A single prompt would mix category classification, business-rule priority scoring, and retrieval with no per-component metrics or controls. The graph gives each agent its own measurable step (classifier F1, an auditable priority score, RAG Recall@5) and a natural place to emit progress events per node.

## Considered options

- **Single LLM prompt** for classify+prioritize+retrieve — rejected: no separate metrics per concern, and ties priority scoring to LLM judgment instead of the fixed business formula ([ADR-0007](0007-fixed-business-formula-for-priority-scoring.md)).
- **Imperative coordination code** — no explicit graph structure, no built-in per-node event hooks.
