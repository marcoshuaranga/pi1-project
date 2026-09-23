# text-embedding-3-small as the shared embedding model

_Also referenced elsewhere in this repo as **ADR-04**._

Three consumers need embeddings of the same ticket text: the Clasificador's kNN lookup, the Agente RAG's similarity search, and GeneradorKEDB's clustering. We use one shared model — OpenAI `text-embedding-3-small` — for all three, with an `EMBEDDING_PROVIDER=local` fallback when the OpenAI embeddings quota is insufficient.

A single embedding space keeps the three consumers aligned: a ticket's neighbors for classification are the same neighborhood used for retrieval and clustering. Maintaining separate embedding spaces per consumer would break that alignment for no benefit at this scale.

## Update

`EMBEDDING_PROVIDER=azure` was added (`packages/core/src/pi_core/services/embeddings.py`'s `AzureOpenAIBackend`) as a third option alongside `openai`/`local`. It's the same `text-embedding-3-small` model served through an Azure OpenAI resource instead of openai.com — an alternate transport for the model this ADR already commits to, not a different embedding space or a new decision.
