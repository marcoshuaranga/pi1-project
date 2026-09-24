# Architecture overview

## 1. Purpose

This project implements a help-desk workflow with three major outcomes:

- classify and prioritize incoming tickets
- retrieve similar historical solutions or validated KEDB articles
- generate and validate KEDB articles from resolved-ticket clusters

## 2. High-level layers

### Layer 1 — data and ingestion

- anonymization of raw GLPI exports
- normalization and split preparation
- indexing into ChromaDB

### Layer 2 — intelligence agents

- Orquestador coordinates the pipeline
- Clasificador assigns category and confidence
- Priorizador computes business priority
- Agente RAG retrieves the Top-5 solutions
- GeneradorKEDB clusters resolved tickets and drafts KEDB articles

### Layer 3 — interfaces and evaluation

- API and WebSocket for ticket processing
- React UI for operator and expert flows
- metrics/dashboard and evaluation outputs

## 3. Runtime flow

```text
Raw GLPI export
  -> anonymize
  -> normalize / ingest
  -> embeddings in Chroma
  -> ticket processing pipeline
  -> RAG retrieval
  -> expert validation of KEDB drafts
  -> validated articles feed the next retrieval cycle
```

## 4. Key architectural decisions

The project’s technical choices are captured in the ADRs under [docs/adr](../adr):

- LangGraph orchestration
- OpenAI GPT-4o-mini for synthesized KEDB content
- ChromaDB for vector retrieval
- text-embedding-3-small for shared embedding space
- HDBSCAN for KEDB clustering
- fixed business-formula prioritization
- regex + spaCy anonymization

## 5. Repository boundaries

- backend domain logic under `packages/core`
- app services under `apps/*`
- frontend under `web/`
- project documentation under root and `docs/`
- demo material isolated under `demo/`

## 6. Typical entry points

- [../../AGENTS.md](../../AGENTS.md)
- [../../CONTEXT.md](../../CONTEXT.md)
- [../../PRD.md](../../PRD.md)
- [../../demo/README.md](../../demo/README.md)
