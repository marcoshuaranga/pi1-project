# ChromaDB as the vector store

_Also referenced elsewhere in this repo as **ADR-03**._

We store ticket and KEDB-article embeddings in ChromaDB (two separate collections: historical tickets, KEDB articles) rather than Pinecone or a bare FAISS index. Chroma is embeddable and self-hosted, which fits an academic MVP prototype running in a containerized deployment without requiring a managed cloud vector-DB vendor.

## Consequences

This is the choice most likely to be revisited if the platform moves past MVP scale or deployment target — self-hosted Chroma vs. a managed cloud vector DB is a real trade-off that was decided in favor of "no mandatory vendor lock-in for the MVP," not "best at scale."
