# Research: KEDB Lifecycle Audit Trail

## Decision 1: Store the trail in the same SQLite database as the articles

- **Decision**: Add a `kedb_auditoria` table to the database that already holds `kedb_articulos`. Every change to an article and its audit row are written in one SQLite transaction.
- **Rationale**: FR-005 requires that a change and its entry succeed or fail together. That is only achievable without distributed-transaction machinery if both live in one store. `KedbStore` already owns the connection and commit logic.
- **Alternatives considered**: A JSONL file or a separate database; rejected because a change and its entry could then diverge. Writing the entry after the change; rejected because a crash between the two leaves an unrecorded change, which is the exact failure the feature exists to prevent.

## Decision 2: Append-only enforced by the database, not by convention

- **Decision**: Create `BEFORE UPDATE` and `BEFORE DELETE` triggers on `kedb_auditoria` that raise an abort. No API route exposes edit or delete of entries.
- **Rationale**: FR-006 and SC-004 say no interface may alter an entry. A trigger also protects against a future code path or script that forgets the rule. It is a few lines of SQL and testable by attempting the write.
- **Alternatives considered**: Relying on the absence of an update method; rejected because it is not enforced. A hash chain over entries; rejected as disproportionate for a declared, unauthenticated actor (see Decision 5).
- **Limit**: A person with direct file access to the database can drop the triggers. The trail supports operational review, not tamper-proof evidence. This is stated in the spec's Assumptions.

## Decision 3: Read-then-write inside one transaction

- **Decision**: `KedbStore.update` currently reads the article (`get`), checks the transition, then writes in a separate connection. The new implementation opens the transaction with `BEGIN IMMEDIATE`, reads the article inside it, validates, updates, and inserts the audit row, then commits.
- **Rationale**: The "two changes at nearly the same time" edge case requires both to be recorded in the order applied with the correct previous state. With separate read and write, two requests can both read `borrador` and both record `borrador -> validado`. `BEGIN IMMEDIATE` serializes writers. This also closes the last-write-wins gap for state transitions (content edits remain last-write-wins; the previous version is recorded).
- **Alternatives considered**: Optimistic version check with a conflict response; rejected as a behavior change to a route whose responses FR-015 says must not change.

## Decision 4: Where the audit context travels

- **Decision**: `KedbArticuloUpdate` (a core schema that is dumped into the SQL `SET` clause) is left untouched. A new core model `ContextoAuditoria(actor, motivo)` is passed as a separate argument to `KedbStore.update`, `create`, and `delete`. The API request model for `PATCH /kedb/articulos/{id}` gains optional `actor` and `motivo` fields in the API layer and the router splits them.
- **Rationale**: Adding `actor`/`motivo` to `KedbArticuloUpdate` would write them into `kedb_articulos` columns that do not exist. Keeping the context separate preserves FR-015 and keeps the article schema unchanged.
- **Alternatives considered**: HTTP headers for actor; rejected because body/query fields are easier to supply from the browser and to document in the contract.

## Decision 5: Actor identity in the baseline

- **Decision**: `actor` is an optional string up to 80 characters. Its kind is derived: supplied -> `declarado`; absent on an API request -> `no_identificado` with the label "no identificado"; changes made by the product itself (generation, demo seeding, demo reset) -> `sistema` with the label "sistema". The expert view keeps the label in browser `localStorage` as a per-viewer convenience.
- **Rationale**: The product has no authentication and ADR scope excludes it. Refusing requests without an actor would break existing API callers (FR-015); inventing a name would be dishonest.
- **Alternatives considered**: Requiring an actor on every write; rejected for the compatibility reason above. Reading the OS or browser user; rejected as unverifiable and privacy-invasive.

## Decision 6: Publication effects are separate entries, written after the transition

- **Decision**: The transition entry commits with the change. The publisher then runs (as today) and its outcome is appended as `publicacion`, `retiro`, or `fallo_publicacion` entries linked to the transition entry by `entrada_origen_id`, listing each destination and its result.
- **Rationale**: Publication talks to Markdown files and Chroma and cannot join the SQLite transaction. FR-009 asks for separate, linked entries.
- **Consequence**: The effect entries are best-effort relative to the transition: if appending one fails after publication already ran, the change stands, the requester still sees the existing publication error behavior, and the failure is logged and returned in the response detail. This is the one place where "a change never exists without its record" does not hold for effect entries, and the spec distinguishes it: FR-005 covers transition and edit entries only.
- **Alternatives considered**: Recording intent before publishing and outcome after (two entries per effect); rejected as more states for little gain.

## Decision 7: History reads and listing

- **Decision**: Two read routes: `GET /kedb/articulos/{articulo_id}/historial` and `GET /kedb/auditoria`. Both page with `limite` (default 50, max 200) and `desplazamiento`. An index on `(articulo_id, id)` and one on `(creado_en)` keep reads bounded. Ordering uses the autoincrement `id`, not the timestamp, so order is exactly the order applied.
- **Rationale**: SC-003 requires opening an article with 500 entries in under 2 seconds; a single indexed query meets this easily. Using the row id as the sequence avoids clock ties.
- **Alternatives considered**: Embedding history inside `GET /kedb/articulos/{id}`; rejected because it changes an existing response (FR-015).

## Decision 8: Pre-existing articles and deleted articles

- **Decision**: No backfill. The history response carries `registro_desde_creacion` (true only if a `creacion` entry exists) so the UI can say "sin registro anterior a esta función". `KedbStore.delete` appends an `eliminacion` entry (actor `sistema` unless provided) in the same transaction as the delete, and entries are not tied to the article by a foreign key, so they outlive it.
- **Rationale**: Inferring past history would present guesses as an audit trail. Demo resets delete articles; the trail must remain readable and must show that the article is gone.
- **Spec reconciliation**: `eliminacion` is an event kind not listed in the spec's Key Entities; the spec is updated to include it.

## Decision 9: Expert view scope

- **Decision**: The expert view gets an actor field, a required reason on reject, and a history section for the selected article. It has no archive control today, so a required reason on archive is enforced by the API only.
- **Rationale**: Adding a new archive workflow to the view is a UI feature beyond this spec's scope. The API rejects `obsoleto`/`archivado` without a reason regardless of the client.
- **Spec reconciliation**: FR-012 and User Story 3 mention archiving in the view; they are reworded to match.

## Decision 10: Failure status and message

- **Decision**: If the audit write fails, the route returns `503` with a Spanish detail and the article is unchanged. A missing reason returns `422`. Over-length actor or reason returns `422`.
- **Rationale**: `503` distinguishes "the audit store is unavailable" from client errors and from the existing `409` invalid-transition response.

## Open questions

None blocking. Two items are deferred by design: retention/purging policy, and verified actor identity (needs an authentication feature).
