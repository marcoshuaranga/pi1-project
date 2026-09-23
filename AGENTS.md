# AGENTS.md

Guidance for AI coding agents working in this repo.

## What this is

`pi1-rag-kedb`: a multi-agent RAG + KEDB (Known Error Database) platform for OITSI-MTC's help desk. It classifies and prioritizes incoming tickets, retrieves similar past solutions, and — from resolved tickets — generates KEDB articles with N:1 traceability to their source tickets, validated by a human expert before publication. See [CONTEXT.md](CONTEXT.md) for the full domain glossary and [docs/adr/](docs/adr/) for the architecture decisions behind the stack below.

**Read [CONTEXT.md](CONTEXT.md) before writing code that touches domain entities.** This is a bilingual codebase: domain terms are Spanish (`Ticket`, `Orquestador`, `Clasificador`, `borrador`/`validado`) even though class names are English (`Orchestrator`, `ClassifierAgent`). Use the Spanish terms in comments, commit messages, and new identifiers where you're modeling the domain — match the existing convention in `packages/core/src/pi_core/agents/` and `.../schemas/`, don't silently translate it.

## "Agents" — two unrelated meanings in this repo

Don't conflate them:

1. **The product's own agents** (`packages/core/src/pi_core/agents/`): five pipeline components — Clasificador, Priorizador, Agente RAG, GeneradorKEDB, Orquestador — defined in `pi_core/schemas/__init__.py`'s `AgenteTipo` enum and orchestrated by a LangGraph state graph (`pi_core/agents/orchestrator/graph.py`). This is core product code.
2. **Claude Code / AI-coding-agent tooling** (`.claude/`, `.agents/skills/`): editor/assistant scaffolding, unrelated to the product. Not part of the runtime.

## Repo layout

Monorepo: a `uv` workspace for the Python backend (`packages/` + `apps/`) plus a separate npm frontend under `web/`. See [ADR-0010](docs/adr/0010-uv-workspace-monorepo-split.md) for why it is split this way.

```
packages/core/src/pi_core/   Shared domain library — imported by every backend app, imports none of them
  agents/                    The 5 agents — classifier, prioritizer, rag, kedb_generator, orchestrator
  schemas/                   Canonical Pydantic models (Ticket, KedbArticulo, AgenteTipo, ...)
  storage/                   ChromaDB client, KEDB store, SQLite ticket sessions
  services/                  KEDB generation policy, publisher (Live Docs projection), embeddings, LLM
  anonymize/, enrich/        Regex+spaCy anonymizer (used at request time AND by ingest), resolution enrichment/reindex
  evaluation/, fixtures/     C9 metrics + golden set, Kyocera demo fixture
  queue.py, config.py        arq/Redis pool settings, pydantic Settings
apps/api/src/pi_api/         FastAPI app: routers + WebSocket (/ws/pipeline/{ticket_id})
apps/worker/src/pi_worker/   arq worker: KEDB generation + evaluation jobs
apps/pipeline/src/pi_pipeline/  Batch DVC ingest CLI (extract → anonymize → ingest → embed)
web/                  React + Vite + TypeScript frontend (3 screens: Operador, Experto KEDB, Coordinador)
litellm/config.yaml   LiteLLM proxy config (model aliases for gpt-4o-mini / claude-sonnet-5)
scripts/              seed_demo.py, reset_demo.py — demo data lifecycle
data/, .dvc/, dvc.yaml  DVC pipeline (extract → anonymize → ingest → embed); never commit the raw .xlsx
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
uv sync                    # installs all 4 workspace members + the root `dev` group
uv run pytest              # tests (pytest-asyncio, testpaths = tests/; centralized at the repo root)
uv run ruff check .        # lint
```

The root `pyproject.toml` is a non-packaged meta-project: it only lists the workspace members and the shared `dev` tooling. Each service declares its own runtime dependencies in `packages/core/pyproject.toml` or `apps/*/pyproject.toml` — add a dependency to the member that actually imports it, and never let `pi_core` import from `pi_api`/`pi_worker`/`pi_pipeline` (apps depend on core, never the reverse, and never on each other).

`uv run pytest` alone doesn't hit live services — tests marked `@pytest.mark.integration` (e.g. the 30s end-to-end DoD check) skip themselves if Chroma isn't reachable; run `docker compose up` first to actually exercise them. The `es_core_news_lg` spaCy model (anonymization NER, ADR-0008) isn't installed by `uv sync` — without it, `Anonymizer.nlp` is silently `None` and name-scrubbing is skipped both at runtime and in tests. Install it once with `uv run python -m spacy download es_core_news_lg` (`apps/api/Dockerfile` and `apps/pipeline/Dockerfile` do this automatically; a bare local `uv` env doesn't). Those two Dockerfiles run their final `uv sync` with `--inexact` on purpose: an exact sync would uninstall the model, since it isn't in `uv.lock`. The worker image has no model — it never runs the Anonymizer.

CI (`.github/workflows/ci.yml`) runs lint + tests + one Docker build per service (`api`, `worker`, `pipeline`, and `web`) on every push/PR to `main`/`master`, not just on manual dispatch. If you change a Dockerfile or a dependency, verify the image actually builds locally (from the repo root: `docker build -f apps/api/Dockerfile -t pi1-api .`, likewise `apps/worker` / `apps/pipeline`; and `docker build -t pi1-web ./web --build-arg VITE_API_URL=http://localhost:8000`) before pushing — don't rely on reading the Dockerfile alone. The backend build context is the repo root because every workspace member's manifest must be present for `uv sync --locked`.

The data pipeline (`docker compose --profile pipeline run --rm pipeline <stage>`) is described as a DVC pipeline in `dvc.yaml` (`extract → anonymize → ingest → embed`). The `dvc` CLI itself isn't a project dependency here — `dvc.yaml` documents the stage graph and lets you run `dvc repro` if you have DVC installed, but the stages also run standalone via the CLI commands above.

## Frontend (`web/`, npm)

```bash
npm run dev      # vite dev server
npm run build    # tsc && vite build
```

## Making architectural changes

If you're changing something covered by an existing ADR in `docs/adr/` (framework choice, vector store, clustering algorithm, priority-scoring approach, anonymization technique), read that ADR first — several note *why* the current approach was picked over an alternative. If you're introducing a new decision that's hard to reverse, would surprise a future reader, and involved a genuine trade-off, add a new ADR (`docs/adr/000N-slug.md`) rather than leaving the reasoning only in a commit message or PR description.
