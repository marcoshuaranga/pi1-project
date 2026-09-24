# Feature Specification: KEDB Lifecycle Audit Trail

**Feature Branch**: `002-kedb-lifecycle-audit-trail`

**Created**: 2026-09-24

**Status**: Draft

**Input**: Close the constitution principle I deviation found in
`specs/001-mvp-closed-assistance-kedb-loop` (plan risk R1, checklist item CHK011):
every KEDB lifecycle transition must be auditable.

This feature adds history to behavior that already exists. It does not change the
lifecycle state machine (`borrador`, `validado`, `obsoleto`, `archivado` and their
permitted transitions), does not add authentication, and does not re-project
published articles. The baseline it builds on is
[specs/001-mvp-closed-assistance-kedb-loop/spec.md](../001-mvp-closed-assistance-kedb-loop/spec.md).

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Answer "who changed this article, and when" (Priority: P1)

As a technical expert or coordinator, I want to open a KEDB article and see its full
change history so that I can say who validated, rejected, edited, or archived it, when,
and why.

**Why this priority**: This is the question the constitution requires the product to be
able to answer. Without it, human approval of reusable knowledge cannot be shown to
have happened.

**Independent Test**: Take an article, approve it, edit it, and archive it, each with a
named actor. Open its history and verify that exactly those three entries appear in
order, each with actor, time, previous state, new state, and reason or edit summary.

**Acceptance Scenarios**:

1. **Given** an article that was approved by an expert, **When** anyone opens its
   history, **Then** an entry shows the state change `borrador -> validado`, the actor
   who made it, the time, and any reason given.
2. **Given** an article that was rejected, **When** its history is opened, **Then** an
   entry shows `borrador -> obsoleto`, the actor, the time, and the reason.
3. **Given** a validated article whose content was edited while it stayed `validado`,
   **When** its history is opened, **Then** an entry shows that content changed, which
   fields changed, the actor, the time, and the resulting version, with no state change.
4. **Given** an article with several entries, **When** its history is opened, **Then**
   entries are ordered from oldest to newest and none are missing or duplicated.
5. **Given** an article that existed before this feature, **When** its history is opened,
   **Then** the history states that no record exists before the feature and shows only
   entries made afterwards. No past entries are invented.

---

### User Story 2 - Every change is recorded automatically (Priority: P1)

As a system owner, I want every lifecycle transition and content edit to leave an audit
entry without depending on the operator remembering to write one, so that the history
is complete by construction.

**Why this priority**: An audit trail that can be skipped is not an audit trail; this
story is what makes principle I true rather than aspirational.

**Independent Test**: Perform each permitted transition and a content edit through every
way the product allows them (expert view, direct lifecycle request, article edit request,
draft generation, demo seeding) and verify each produced exactly one entry.

**Acceptance Scenarios**:

1. **Given** a permitted transition is requested by any route, **When** it succeeds,
   **Then** exactly one audit entry exists for it and the entry's new state equals the
   article's stored state.
2. **Given** a transition is rejected as not permitted, **When** the request completes,
   **Then** the article is unchanged and no audit entry is created.
3. **Given** the audit entry cannot be stored, **When** a transition or edit is
   requested, **Then** the change is not applied, the requester receives an explicit
   failure, and the article keeps its previous state and content. A change never exists
   without its record.
4. **Given** a draft is created by generation or demo seeding, **When** it is stored,
   **Then** an initial entry records its creation as `borrador` with the system as actor.
5. **Given** a transition to `obsoleto` or `archivado`, **When** it is requested without
   a reason, **Then** it is refused with an explicit message and nothing changes.

---

### User Story 3 - Record who acted and why from the expert view (Priority: P2)

As an expert, I want to state who I am and give a reason when I approve, reject, or
archive an article, and to read the history next to the article I am reviewing, so that
my decision is recorded where I make it.

**Why this priority**: The trail is only useful if the people making changes can supply
the actor and the reason, and if reviewers can read it without leaving the review flow.

**Independent Test**: In the expert view, set an actor name, reject a draft with a
reason, and confirm the article's history section shows the new entry immediately.

**Acceptance Scenarios**:

1. **Given** the expert view, **When** an expert enters an actor name once, **Then**
   that name is used for their following changes until they change it.
2. **Given** an expert rejects or archives an article, **When** the reason field is
   empty, **Then** the action cannot be submitted and the view says why.
3. **Given** an article is selected, **When** the view loads, **Then** its history is
   shown in the same screen, newest entry clearly identifiable.
4. **Given** the history cannot be loaded, **When** the view opens an article, **Then**
   it shows an explicit error state and does not present an empty history as if no
   changes had occurred.

---

### User Story 4 - Review recent changes across articles (Priority: P3)

As a coordinator, I want to list recent lifecycle changes across all articles and filter
them by article, actor, state, or date range, so that I can review expert activity
without opening each article.

**Why this priority**: It serves oversight and periodic review but is not needed to
answer the per-article question.

**Independent Test**: Create entries for three articles by two actors on different days;
filter by one actor and by a date range and verify the results match exactly.

**Acceptance Scenarios**:

1. **Given** entries exist for several articles, **When** a coordinator lists changes
   with no filter, **Then** entries are returned newest first and in pages of a bounded
   size.
2. **Given** filters for actor, resulting state, article, or date range, **When** they
   are applied, **Then** only entries matching all of them are returned.
3. **Given** a filter that matches nothing, **When** it is applied, **Then** an empty
   result is returned, distinguishable from a failure to read the trail.

---

### User Story 5 - Publication effects are part of the trail (Priority: P2)

As a system owner, I want the trail to show when an approval made an article available
for reuse and when leaving `validado` withdrew it, including when that did not succeed,
so that a validated article that is not actually reusable is visible in its history.

**Why this priority**: 001 observed a validated article that was published to Live Docs
but missing from retrieval. Recording the outcome makes such divergence discoverable.

**Independent Test**: Approve an article while the retrieval index is unavailable and
verify the history shows the approval and a failed publication effect naming the failed
destination.

**Acceptance Scenarios**:

1. **Given** an article is approved, **When** publication completes, **Then** the
   history shows a publication entry listing the destinations that were updated.
2. **Given** an article leaves `validado`, **When** withdrawal completes, **Then** the
   history shows a withdrawal entry listing the destinations that were cleaned.
3. **Given** a destination fails during publication or withdrawal, **When** the request
   completes, **Then** the history shows a failure entry naming the destination, and
   the requester still receives the failure as today.

### Edge Cases

- Two changes to the same article arrive at nearly the same time; both must be recorded
  in the order they were applied, and neither may overwrite the other's entry.
- An expert supplies no actor name; the entry is recorded with an explicit "not
  identified" actor rather than being refused or given a made-up name.
- An article is deleted by a demo reset; its audit entries must remain and be readable
  by article identifier, marked as belonging to an article that no longer exists.
- A very long reason or actor name is submitted; it is refused or bounded with an
  explicit message, never silently truncated.
- The history of an article grows large; reading it must stay bounded and paged.
- A content edit changes nothing (same values submitted); no entry is created because
  nothing changed.
- An entry is requested to be edited or deleted through any interface; the request is
  refused, since no such operation exists.
- Reason or actor text contains personal data; the trail stores what it is given and the
  interface warns that it must not be used for personal data (see Assumptions).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST record one audit entry for every successful KEDB article
  lifecycle transition, containing article identifier, previous state, new state, actor,
  timestamp, and reason.
- **FR-002**: The system MUST record one audit entry for every successful content edit,
  containing the fields changed, the resulting version, actor, timestamp, and an edit
  summary, whether or not the state changed.
- **FR-003**: The system MUST record an initial entry when an article is created,
  identifying the creating source (draft generation or demo seeding) and the system as
  actor.
- **FR-004**: The system MUST NOT record entries for requests that are refused
  (invalid transition, missing article, invalid input) and MUST leave the article
  unchanged in those cases.
- **FR-005**: A change and its audit entry MUST succeed or fail together: if the entry
  cannot be stored, the change MUST NOT be applied and the requester MUST receive an
  explicit failure.
- **FR-006**: The audit trail MUST be append-only: no interface of the product MAY edit
  or delete an entry, and entries MUST outlive the deletion of the article they describe.
- **FR-007**: The system MUST require a non-empty reason for transitions to `obsoleto`
  and `archivado`, and MUST accept an optional reason for other transitions.
- **FR-008**: The actor of an entry MUST be a self-declared label supplied with the
  request, or the fixed value "no identificado" when none is supplied, or "sistema" for
  changes the product makes itself. The system MUST NOT present a self-declared actor as
  a verified identity.
- **FR-009**: The system MUST record publication and withdrawal effects of a transition
  as separate entries linked to it, naming each destination and whether it succeeded.
- **FR-010**: The system MUST return an article's history in chronological order, with
  bounded page size, and MUST report an explicit error, not an empty list, when the
  history cannot be read.
- **FR-011**: The system MUST allow the trail to be listed across articles, newest
  first, filtered by article, actor, resulting state, and date range, with bounded page
  size.
- **FR-012**: The expert view MUST let an expert set an actor label, MUST require a
  reason for rejection and archiving, and MUST show the selected article's history.
- **FR-013**: The system MUST state, for an article created before this feature, that no
  history exists before the feature, and MUST NOT backfill inferred entries.
- **FR-014**: Entries MUST use the canonical domain terms of `CONTEXT.md` for states and
  actions, and MUST keep field names in Spanish where the domain model does.
- **FR-015**: The system MUST NOT change which lifecycle transitions are permitted, nor
  the existing responses of the lifecycle, search, and Live Docs routes for successful
  requests, beyond accepting the optional actor and reason inputs.

### Key Entities _(include if feature involves data)_

- **Audit Entry (`RegistroAuditoria`)**: An immutable record of one event on one
  article: identifier, article identifier, event kind (creation, state change, content
  edit, publication, withdrawal, publication failure), previous state, new state,
  version, changed fields, actor and actor kind (declared, not identified, system),
  timestamp, reason or summary, and a link to the entry that caused it when it is a
  publication effect.
- **Actor**: A self-declared label plus a kind. It identifies a person only as far as
  the person declared themselves; it is not authenticated.
- **KEDB Article (`KedbArticulo`)**: Unchanged. Gains an ordered history of Audit
  Entries that outlives it.
- **KEDB Lifecycle State**: Unchanged (`borrador`, `validado`, `obsoleto`, `archivado`).

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: For every permitted transition and content edit performed in acceptance
  testing, through every supported route, exactly one audit entry exists and its new
  state matches the article's stored state (100% of cases, zero missing or duplicated).
- **SC-002**: When storing the audit entry is made to fail, 100% of attempted changes
  are refused and leave the article unchanged.
- **SC-003**: A reviewer can answer "who validated this article and when" from the expert
  view in a single screen without leaving the article, and the answer appears within
  2 seconds of opening an article with up to 500 entries.
- **SC-004**: No product interface can alter or remove an existing entry; attempts are
  refused (verified for every route that touches articles).
- **SC-005**: For 100% of approvals and withdrawals in acceptance testing, the history
  shows which publication destinations succeeded and which failed.
- **SC-006**: Listing changes across articles with any combination of the supported
  filters returns exactly the matching entries in acceptance testing (no false
  inclusions or omissions).

## Assumptions

- The baseline has no authentication, so identity is declared, not verified. An entry
  therefore supports operational review, not non-repudiation. When authentication is
  introduced by a later feature, the actor kind gains a verified value without changing
  existing entries. This is a known limit of how far principle I is met by this feature.
- Refused requests (invalid transitions, missing articles) are not part of the trail
  because they change nothing; they remain visible through ordinary error responses.
- A reason is mandatory only for rejecting and archiving because those are the decisions
  a later reviewer most needs explained; approval is self-explanatory from its actor and
  time, and a reason stays optional there.
- Entries store free text supplied by users. The product does not screen it for personal
  data; the interface tells users not to include any, consistent with the privacy
  principle, and the existing anonymization scope does not extend to this text.
- Articles created before this feature have no earlier history and are not backfilled;
  their trail begins with the first change made after the feature is in use.
- Audit entries and the article they describe live in the same store, which is what lets
  a change and its entry succeed or fail together. A store that cannot make them atomic
  is out of scope.
- Retention of the trail is indefinite in the baseline; archival or purging policy is a
  later decision.
- Out of scope: authentication and access governance, changing the lifecycle state
  machine or its permitted transitions, re-projecting already published articles, and
  ticket-session or feedback history.

## Constitution Alignment

- **Human-Controlled Knowledge**: this feature is the mechanism that makes "every KEDB
  lifecycle transition MUST be auditable" true; it does not weaken the approval
  boundary or the state machine.
- **Privacy Before Processing**: the trail stores actor labels and reasons, which are
  user-entered text; it stores no ticket text and the assumption above records the
  personal-data limit.
- **Canonical Domain Language**: states, actions, and field names stay in Spanish as in
  `CONTEXT.md`; new domain terms (`RegistroAuditoria`) follow the same convention.
- **Clean Core and Application Boundaries**: the audit model belongs to shared domain
  code; delivery routes and the expert view consume it without reaching into core
  internals.
- **Evidence-Based Delivery**: each user story has an independent test, and the change
  to lifecycle routes and stored data requires contract and integration coverage.
