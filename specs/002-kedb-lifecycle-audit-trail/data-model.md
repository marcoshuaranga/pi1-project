# Data Model: KEDB Lifecycle Audit Trail

## Audit Entry (`RegistroAuditoria`)

An immutable record of one event on one article. Stored in table `kedb_auditoria` in the KEDB database.

| Field | Type | Notes |
| :--- | :--- | :--- |
| `id` | integer, autoincrement | Sequence of application order; the only ordering key. |
| `articulo_id` | text, indexed | No foreign key: entries outlive the article. |
| `tipo` | text | `creacion`, `cambio_estado`, `edicion`, `publicacion`, `retiro`, `fallo_publicacion`, `eliminacion`. |
| `estado_anterior` | text, nullable | `KedbEstado` value; null on `creacion`. |
| `estado_nuevo` | text, nullable | `KedbEstado` value; null on `eliminacion`. |
| `version` | integer, nullable | Article version after the event. |
| `campos_modificados` | text (JSON list), nullable | Content fields that changed, for `edicion`. |
| `actor` | text | Label; max 80 characters. |
| `tipo_actor` | text | `declarado`, `no_identificado`, `sistema`. |
| `motivo` | text, nullable | Reason or edit summary; max 500 characters. |
| `destinos` | text (JSON list), nullable | For effect entries: `[{"destino": "markdown", "ok": true}, ...]`. |
| `entrada_origen_id` | integer, nullable | `id` of the transition entry that caused an effect entry. |
| `creado_en` | text, ISO-8601 UTC | Server clock. |

### Rules

- Append-only: `BEFORE UPDATE` and `BEFORE DELETE` triggers abort any modification.
- `cambio_estado` and `edicion` entries are inserted in the same transaction as the article change. If the insert fails, the change does not commit.
- A refused request (invalid transition, missing article, validation error) produces no entry.
- A content edit that changes no field produces no `edicion` entry.
- `cambio_estado` to `obsoleto` or `archivado` requires a non-empty `motivo`; otherwise the request is refused before anything is written.
- A request that changes both content and state produces two entries in order: `edicion`, then `cambio_estado`, in one transaction.
- Effect entries (`publicacion`, `retiro`, `fallo_publicacion`) reference their cause through `entrada_origen_id` and are appended after the transition commits.

### Indexes

- `(articulo_id, id)` for per-article history.
- `(creado_en)` for date-range listing.
- `(tipo_actor, actor)` and `(estado_nuevo)` are not indexed; the listing filters on them after the date or article narrowing, which is adequate at the expected volume.

## Actor

Not a separate table. A pair `(actor, tipo_actor)` on each entry.

- `declarado`: label supplied with the request. Not verified.
- `no_identificado`: no label supplied; stored label is `no identificado`.
- `sistema`: the product itself; stored label is `sistema`.

## Audit Context (`ContextoAuditoria`)

Core model passed alongside every write: `actor: str | None`, `motivo: str | None`. It is not persisted on `kedb_articulos` and does not alter `KedbArticulo` or `KedbArticuloUpdate`.

## Article History (response model `HistorialArticulo`)

- `articulo_id`
- `articulo_existe`: whether the article still exists.
- `registro_desde_creacion`: true only if a `creacion` entry exists; false means history before the feature is unknown.
- `total`, `limite`, `desplazamiento`
- `entradas`: `RegistroAuditoria` list in application order.

## Relationships

- One `KedbArticulo` has zero or more `RegistroAuditoria`; the relation is by `articulo_id` only and survives deletion.
- An effect entry points to exactly one transition entry through `entrada_origen_id`.

## Unchanged

`KedbArticulo`, `KedbArticuloUpdate`, `KedbEstado`, and the permitted transitions are not modified.
