# AGENTS.md

Guidance for AI coding agents working in this repo.

## What this is

`pi1-rag-kedb`: a multi-agent RAG + KEDB (Known Error Database) platform for OITSI-MTC's help desk. It classifies and prioritizes incoming tickets, retrieves similar past solutions, and — from resolved tickets — generates KEDB articles with N:1 traceability to their source tickets, validated by a human expert before publication. See [CONTEXT.md](CONTEXT.md) for the full domain glossary and [docs/adr/](docs/adr/) for the architecture decisions behind the stack below.

**Read [CONTEXT.md](CONTEXT.md) before writing code that touches domain entities.** This is a bilingual codebase: domain terms are Spanish (`Ticket`, `Orquestador`, `Clasificador`, `borrador`/`validado`) even though class names are English (`Orchestrator`, `ClassifierAgent`). Use the Spanish terms in comments, commit messages, and new identifiers where you're modeling the domain — match the existing convention in `app/agents/` and `app/schemas/`, don't silently translate it.

## "Agents" — two unrelated meanings in this repo

Don't conflate them:

1. **The product's own agents** (`app/agents/`): five pipeline components — Clasificador, Priorizador, Agente RAG, GeneradorKEDB, Orquestador — defined in `app/schemas/__init__.py`'s `AgenteTipo` enum and orchestrated by a LangGraph state graph (`app/agents/orchestrator/graph.py`). This is core product code.
2. **Claude Code / AI-coding-agent tooling** (`.claude/`, `.agents/skills/`): editor/assistant scaffolding, unrelated to the product. Not part of the runtime.

## Repo layout

Monorepo: Python backend at the root, a separate frontend under `web/`.

```
app/                  FastAPI backend (the product)
  agents/             The 5 agents — classifier, prioritizer, rag, kedb_generator, orchestrator
  api/                 REST routers + WebSocket (/ws/pipeline/{ticket_id})
  schemas/             Canonical Pydantic models (Ticket, KedbArticulo, AgenteTipo, ...)
  storage/             ChromaDB client, KEDB store, SQLite ticket sessions
  services/            KEDB generation policy, publisher (Live Docs projection)
  jobs/                Background jobs (arq + redis)
web/                  React + Vite + TypeScript frontend (3 screens: Operador, Experto KEDB, Coordinador)
litellm/config.yaml   LiteLLM proxy config (model aliases for gpt-4o-mini / claude-sonnet-5)
scripts/              seed_demo.py, reset_demo.py — demo data lifecycle
data/, .dvc/          DVC-versioned raw ticket export (never commit the raw .xlsx)
docs/adr/             Architecture decision records
CONTEXT.md            Domain glossary — read this first
PRD.md, DEMO*.md      Product spec and demo runbook/QA (Spanish)
```

## Running it

```bash
docker compose up --build
docker compose --profile pipeline run --rm pipeline full   # data pipeline (Phase 1)
```

Services: `api` (FastAPI), `worker` (arq), `web` (Vite dev server), `chromadb`, `redis`, `litellm`.

## Backend (Python, `uv`-managed)

```bash
uv run pytest              # tests (pytest-asyncio, testpaths = tests/)
uv run ruff check .        # lint
```

`uv run pytest` alone doesn't hit live services — tests marked `@pytest.mark.integration` (e.g. the 30s end-to-end DoD check) skip themselves if Chroma isn't reachable; run `docker compose up` first to actually exercise them. The `es_core_news_lg` spaCy model (anonymization NER, ADR-0008) isn't installed by `uv sync` — without it, `Anonymizer.nlp` is silently `None` and name-scrubbing is skipped both at runtime and in tests. Install it once with `uv run python -m spacy download es_core_news_lg` (the Dockerfile does this automatically; a bare local `uv` env doesn't).

## Frontend (`web/`, npm)

```bash
npm run dev      # vite dev server
npm run build    # tsc && vite build
```

## Making architectural changes

If you're changing something covered by an existing ADR in `docs/adr/` (framework choice, vector store, clustering algorithm, priority-scoring approach, anonymization technique), read that ADR first — several note *why* the current approach was picked over an alternative. If you're introducing a new decision that's hard to reverse, would surprise a future reader, and involved a genuine trade-off, add a new ADR (`docs/adr/000N-slug.md`) rather than leaving the reasoning only in a commit message or PR description.
