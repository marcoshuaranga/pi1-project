# Copilot instructions

This repo is the OITSI-MTC RAG + KEDB platform. Start with [../AGENTS.md](../AGENTS.md) and [../CONTEXT.md](../CONTEXT.md) before making product changes.

## Core rules

- Keep backend/app boundaries intact: shared domain logic lives under `packages/core`, while `apps/*` consume it.
- Use the project’s bilingual domain language consistently; Spanish terms such as `Ticket`, `Orquestador`, `Clasificador`, and `borrador`/`validado` are part of the domain model.
- Respect the monorepo split: Python is managed by `uv`, and the frontend is a separate `web/` app managed by `npm`.
- Read the relevant ADR before changing frameworks, model choices, or pipeline architecture.
- Do not commit raw XLSX or generated data artifacts unless the task specifically calls for them.

## Validation

- Python changes: `uv run pytest` and `uv run ruff check .`
- Frontend changes: `npm run build` from `web/`
- If the task affects architecture or data flow, check the relevant docs in [../docs/adr](../docs/adr) and [../PRD.md](../PRD.md) before editing.
