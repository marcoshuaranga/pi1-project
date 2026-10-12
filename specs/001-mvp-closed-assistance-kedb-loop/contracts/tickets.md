# Ticket Assistance Contract

Source of truth: `apps/api/src/pi_api/routers/tickets.py`,
`apps/api/src/pi_api/ws/pipeline.py`, and the `Ticket*` / `PipelineEvento` models
in `packages/core/src/pi_core/schemas/__init__.py`. Verified by
`apps/api/tests/test_ticket_assistance_contract.py` and
`apps/api/tests/test_pipeline_websocket_contract.py`.

## Submit ticket

`POST /tickets`

Request: `{"texto": string}` with `texto` at least 5 characters (`TicketInput`).
Shorter or missing text is rejected with `422` before the pipeline runs.

Response `200` (`TicketResponse`):

- `ticket_id`;
- `categoria` and `confianza`;
- `prioridad` and optional `justificacion_prioridad` (score components);
- `soluciones`: ordered list of `{articulo_o_ticket_id, score, tipo, titulo,
  solucion}` where `tipo` is `"ticket"` or `"kedb"`. An empty list is a valid
  no-hit result.

Failure behavior: an unexpected pipeline exception on this synchronous route is
not converted to a failed ticket session; it surfaces as an HTTP `5xx`. The
service does not invent a successful result. This behavior is read from the route
code and has no dedicated test. The WebSocket route below is the path that
records an `error` session (covered by `test_pipeline_websocket_contract.py`).

## Ticket status

`GET /tickets/{ticket_id}`

Returns `TicketStatusResponse`: `status` is `procesando`, `completado`, or
`error`; `result` is present when completed and `error` when failed. Unknown
identities return `404`.

## Correction, resolution, and feedback

- `GET /tickets/categorias` lists the valid categories (top-9, `pi_core.constants`).
- `PATCH /tickets/{ticket_id}/categoria` (`{"categoria": string}`) records an
  operator category correction; requires a completed ticket, otherwise `404`. A
  category outside the top-9 is rejected with `422`; the same category the ticket
  already has returns `{"cambio": false}` and writes nothing (HU03).
- `POST /tickets/{ticket_id}/feedback` (`FeedbackRequest`) takes either
  `articulo_id` + `util` (HU11: one rating per `(ticket_id, articulo_id)`, a second
  one updates it) or `nueva_solucion` (HU12). Neither → `422`.
- HU12 `nueva_solucion`: at least 20 characters (`422` otherwise, `404` for an unknown
  ticket). The solution is registered as a **candidate KEDB article**: a `borrador`
  `KedbArticulo` with `tickets_fuente=[ticket_id]`, so it enters the expert review
  queue and is never reusable or published before human approval. Before saving it is
  compared against validated KEDB articles with the Agente RAG retriever
  (`search_kedb`); a hit with similarity ≥ `umbral_duplicado_kedb` (0.85) returns
  `409 {"detail": {"codigo": "posible_duplicado", "similares": [...]}}` and nothing is
  saved until the client resends with `"confirmar_duplicado": true`.
- `POST /tickets/{ticket_id}/resolucion` is **deprecated**: same behaviour as
  `/feedback` with `nueva_solucion` (body `{"solucion", "confirmar_duplicado"}`).

These actions preserve the ticket identity and never change KEDB lifecycle state.

## Pipeline events

`WS /ws/pipeline/{ticket_id}`

Protocol:

1. The client sends `{"action": "process", "texto": string}`. The server records
   the ticket as `procesando` before the pipeline starts.
2. The server emits one `PipelineEvento` JSON message per stage transition
   (`evento_id`, `timestamp`, `agente`, `ticket_id`, `tipo`, optional `entrada`,
   `salida`, `metadata`).
3. The server ends the run with `{"type": "result", "data": TicketResponse}` or
   `{"type": "error", "message": string}`; an error also marks the session
   `error`. Results are fanned out to every socket subscribed to the ticket.

Events provide observability; they do not publish KEDB or override human
lifecycle decisions.
