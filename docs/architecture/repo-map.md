# Repository map

## Top-level structure

```text
pi1-app/
├── AGENTS.md
├── CONTEXT.md
├── PRD.md
├── README.md
├── demo/
├── docs/
│   ├── adr/
│   ├── architecture/
│   └── operations/
├── apps/
│   ├── api/
│   ├── pipeline/
│   └── worker/
├── packages/
│   └── core/
├── web/
├── scripts/
├── data/
├── litellm/
├── compose.yml
├── compose.dev.yml
└── dvc.yaml
```

## Main directories

### packages/core

Shared domain logic and reusable models.

- agents
- schemas
- storage
- services
- anonymize
- evaluation
- fixtures

### apps/api

FastAPI application, routers and real-time workflow events.

### apps/worker

Background processing for KEDB generation and evaluation tasks.

### apps/pipeline

Batch ingestion pipeline and data flows.

Each of these workspace members owns its tests in its own `tests/` directory; the shared test fixture lives in the repo-root `conftest.py`.

### web

React + Vite frontend for operator, KEDB expert, and coordinator views.

### demo

Operational and narrative material for the live demo session.

### docs/adr

Authoritative design records for the architecture and product choices.

## Why this organization matters

This repo intentionally separates:

- product language and goals
- system architecture decisions
- runtime implementation
- demo-only content

That separation avoids mixing business requirements, engineering decisions, and presentation material in one document.
