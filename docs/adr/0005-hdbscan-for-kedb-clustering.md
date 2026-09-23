# HDBSCAN for KEDB clustering

_Also referenced elsewhere in this repo as **ADR-05**._

GeneradorKEDB groups resolved tickets before synthesizing a KEDB article per group. We use HDBSCAN over K-Means for this clustering step.

HDBSCAN doesn't require fixing the number of clusters (`k`) upfront, detects clusters of variable density, and lets outlier tickets fall out as noise instead of being forced into a group. That matches the actual requirement — "group what's similar enough" — better than K-Means, which would force every ticket into some cluster. Clusters below 5 tickets are filtered out before synthesis runs.

## Status

A 2026-09 architecture audit found `generate_all()` had drifted to running a keyword/metadata clustering pass *before* HDBSCAN, with HDBSCAN only used as a fallback when the keyword pass didn't fill `max_articles` — the inverse of this ADR. Fixed in `app/agents/kedb_generator/agent.py:267-315`: HDBSCAN (`cluster_tickets`) is now the primary path again; metadata keyword clustering (`_metadata_keyword_clusters`) is the fallback for when HDBSCAN doesn't produce enough clusters. `generate_from_cluster_keyword` (the explicit demo-Kyocera path, invoked via `generate(keyword=...)`) is unaffected — it's a deliberate, named-keyword tool for seeding demo data, not part of `generate_all`'s auto-discovery.

Not yet implemented: the "coherencia interna alta" (high internal coherence) filter PRD §7.6 describes alongside the ≥5-ticket threshold. Only the size threshold exists today (`agent.py:170-174`). Defining what "high coherence" means (e.g. an intra-cluster average cosine-similarity threshold) is an open design question, not addressed by this fix.

