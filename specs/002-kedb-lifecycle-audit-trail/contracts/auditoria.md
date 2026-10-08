# Audit Trail Contract

Delivery routes live in `apps/api/src/pi_api/routers/kedb.py`; models in `packages/core/src/pi_core/schemas/`. Unchanged routes keep their existing responses (FR-015).

## Changed inputs (backward compatible)

`PATCH /kedb/articulos/{articulo_id}` accepts, in addition to `KedbArticuloUpdate`:

- `actor` (string, max 80, optional)
- `motivo` (string, max 500, optional; required when `estado` is `obsoleto` or `archivado`)

`PATCH /kedb/articulos/{articulo_id}/ciclo-vida?estado=` accepts query parameters `actor` and `motivo` with the same rules. Its default `estado=archivado` therefore requires `motivo` unless `estado` says otherwise.

New outcomes:

| Status | When |
| :--- | :--- |
| `422` | `motivo` missing for `obsoleto`/`archivado`, or `actor`/`motivo` over length. Nothing is written. |
| `503` | The audit entry could not be stored. The article is unchanged. |

Existing outcomes (`200`, `404`, `409` for invalid transition) are unchanged. Successful responses still return the `KedbArticulo`.

## Article history

`GET /kedb/articulos/{articulo_id}/historial?limite=&desplazamiento=`

- `200` with `HistorialArticulo` (see data model), entries oldest first.
- `limite` default 50, maximum 200; larger values return `422`.
- `200` with `articulo_existe = false` for a deleted article that has entries.
- `404` only when the article does not exist and has no entries.
- `503` when the trail cannot be read. An empty `entradas` list is never returned for a read failure.

## Cross-article listing

`GET /kedb/auditoria?articulo_id=&actor=&estado_nuevo=&tipo=&desde=&hasta=&limite=&desplazamiento=`

- All filters optional and combined with AND. `desde`/`hasta` are ISO-8601 instants, inclusive.
- Entries newest first; same paging limits as above.
- `200` with `{total, limite, desplazamiento, entradas}`. A filter matching nothing returns `total = 0` and `entradas = []`.
- `503` when the trail cannot be read.

## Not provided

There is no route to create, edit, or delete an entry. `PUT`, `PATCH`, and `DELETE` on `/kedb/auditoria` and `/kedb/articulos/{id}/historial` return `405`.

## Entry shape (`RegistroAuditoria`)

```json
{
  "id": 12,
  "articulo_id": "KEDB-ABC",
  "tipo": "cambio_estado",
  "estado_anterior": "borrador",
  "estado_nuevo": "validado",
  "version": 1,
  "campos_modificados": null,
  "actor": "Ana Pérez",
  "tipo_actor": "declarado",
  "motivo": "Verificado con soporte de red",
  "destinos": null,
  "entrada_origen_id": null,
  "creado_en": "2026-10-08T15:04:05+00:00"
}
```

Effect entries carry `destinos`, for example `[{"destino":"markdown","ok":true},{"destino":"vector","ok":false}]`, and `entrada_origen_id`.

## Frontend contract (`web/src/api.ts`)

- `api.getHistorialArticulo(id, limite?, desplazamiento?)`
- `api.listAuditoria(filtros)`
- `api.approveArticulo(id, actor?)`, `api.rejectArticulo(id, motivo, actor?)`, `api.updateArticulo(id, data, actor?)` pass `actor`/`motivo` through.
