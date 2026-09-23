# Conditional routing in the orchestrator graph

_Also referenced elsewhere in this repo as **ADR-06**. Extends [ADR-0001](0001-langgraph-for-agent-orchestration.md) (LangGraph as the framework) with the specific routing behavior the graph is designed to support._

The Orquestador's graph is designed to skip the Agente RAG step when an incident type already has a known direct resolution, and to escalate immediately when the Priorizador detects high priority — instead of always running the full agent chain in the same order.

Skipping known-resolution tickets avoids unnecessary retrieval calls, and escalating on detected high priority gets urgent tickets flagged without waiting on the rest of the pipeline to finish.

## Status

The current build runs the graph as a strictly sequential chain (anonymize → classify → prioritize → RAG); the conditional routing described here is the designed extension, not yet implemented. It wasn't required to demonstrate the MVP's closed loop. Treat this ADR as the target design for the routing behavior, not a description of what ships today.
