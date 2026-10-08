# Quickstart: KEDB Lifecycle Audit Trail

Validation guide for the feature once implemented. See [data-model.md](data-model.md) and [contracts/auditoria.md](contracts/auditoria.md) for details; this file does not duplicate them.

## Prerequisites

- `uv sync` from the repository root.
- For the live check: `docker compose up --build -d api web` (the audit table is created on first start; existing articles keep working).
- Node via mise on this machine: `mise exec node@24.19.0 -- npm run build` from `web/`.

## Automated validation

```powershell
uv run pytest packages/core/tests apps/api/tests
uv run pytest
uv run ruff check .
cd web
mise exec node@24.19.0 -- npm run build
```

## Live check (use a throwaway article, never real data)

Replace `ID` with a disposable draft.

1. Approve with an actor: `PATCH /kedb/articulos/ID` with `{"estado":"validado","actor":"Ana"}`; then `GET /kedb/articulos/ID/historial`. Expect a `cambio_estado` entry `borrador -> validado`, actor `Ana`/`declarado`, and a `publicacion` entry listing `markdown` and `vector`.
2. Edit while validated: `PATCH` with `{"titulo":"Nuevo título"}`. Expect an `edicion` entry with `campos_modificados = ["titulo"]` and a higher `version`.
3. Archive without a reason: `PATCH /kedb/articulos/ID/ciclo-vida?estado=archivado`. Expect `422` and no new entry.
4. Archive with a reason: add `&motivo=Reemplazado`. Expect `cambio_estado` and a `retiro` entry.
5. Invalid transition: `PATCH` `{"estado":"validado"}` on the archived article. Expect `409` and no new entry.
6. List: `GET /kedb/auditoria?actor=Ana` returns only Ana's entries, newest first.
7. Append-only: attempt `DELETE /kedb/auditoria` and `PUT`; expect `405`. Direct SQL `UPDATE`/`DELETE` on `kedb_auditoria` fails with the trigger's abort message.
8. Delete the throwaway article through the demo fixture; its history is still readable with `articulo_existe = false` and an `eliminacion` entry.
9. Existing article: open the history of an article created before the feature; expect `registro_desde_creacion = false`.

## Expert view check

Open `/experto`, enter an actor name, select a draft, reject it with an empty reason (blocked with a message), then with a reason, and confirm the history section shows the new entry. Confirm a history load failure shows an error state, not an empty list.

## Failure check

With the audit table made unwritable in a test database, an approval returns `503` and the article keeps `borrador` (covered by an automated test; do not do this against real data).
