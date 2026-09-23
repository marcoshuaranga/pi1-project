# Split the Python backend into a uv workspace (`pi_core` + `pi_api` / `pi_worker` / `pi_pipeline`)

_Written from a 2026-09 architecture review, ahead of adding more agents, WebSocket channels and realtime events._

The backend used to be one flat `app/` package with one `pyproject.toml`, one `uv.lock` and one `Dockerfile` shared by three deployables (`api`, `worker`, `pipeline`). Any dependency upgrade (e.g. `langgraph`) had to be absorbed by all three at once, all three images installed everything (including the 541MB spaCy model the worker never uses), and nothing stopped one service from importing another's code.

It is now a `uv` workspace: `packages/core` (`pi_core`, the shared domain library) and `apps/api`, `apps/worker`, `apps/pipeline`, each with its own `pyproject.toml`, `src/`-layout package and `Dockerfile`. One `uv.lock` at the root keeps resolution consistent; `uv sync --package <name>` scopes what each image installs. The rule is one-directional: apps depend on `pi_core`, `pi_core` depends on no app, apps never depend on each other.

## Boundary violations found and how they were resolved

Mapping the import graph before moving anything showed three couplings that a naive directory split would have baked in:

- `agents/orchestrator/graph.py` imported the anonymizer from `pipeline/`, and runs it on **every ticket at request time**, not only in batch ingest. Anonymization is a shared domain capability, so `anonymize/` moved into `pi_core`.
- The API's `/kedb/seed-demo` imported `pipeline/enrich/reindex.py`. `enrich/` moved into `pi_core` (ingest and the API both use it).
- The API imported `jobs/redis.py` (the arq pool settings) from the worker package just to enqueue jobs by name. It moved to `pi_core/queue.py`, which both `api` and `worker` import.

These were fixed **inside the old monolithic `app/` first** (move, repoint, run tests), and only then was the code split into packages one service at a time, testing and running the Docker stack after each step.

## Considered options

- **Dependency extras + multi-stage Dockerfile, keep one package** — cheaper, but only isolates *installs*; it does not stop `worker` code importing `api` code, which is the refactoring risk that motivated this.
- **`import-linter` contracts over the flat package** — worth adding on top, but a convention enforced in CI rather than a physical boundary.
- **Implicit namespace package (`app.*` split across distributions)** — would have avoided renaming imports, but real code changed owner (`anonymize/`, `enrich/`, the queue settings), and shared-namespace editable installs are fragile with type checkers, pytest and IDEs.
- **Nx / Turborepo / Bazel** — JS-native task graphs with second-class Python support; over-engineered for three services.

## Consequences

- Backend Docker build context is the **repo root** (`docker build -f apps/api/Dockerfile .`): `uv sync --locked` needs every member's manifest to validate `uv.lock`, even though only one member is installed.
- The api and pipeline images run their final `uv sync` with `--inexact`, because the spaCy model is installed with `spacy download` (not in `uv.lock`) and an exact sync silently uninstalls it. Do not remove that flag.
- Tests stay centralized in `tests/` at the repo root; several span api + core + pipeline in one file, so they run against the full workspace (`uv sync`), not per package.
- The root `pyproject.toml` is a non-packaged meta-project that lists the four members and hosts the `dev` dependency group, so `uv sync` / `uv run pytest` at the root keep working.
- Adding a dependency now means putting it in the member that imports it. A `pi_core` module importing FastAPI, arq's worker, or pandas is a smell that the boundary is leaking.
