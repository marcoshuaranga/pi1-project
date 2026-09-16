"""C6 — KEDB generator (HDBSCAN + LLM synthesis)."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

import hdbscan
import numpy as np

from app.config import Settings, get_settings
from app.schemas import KedbArticulo, KedbEstado
from app.services.llm import extract_json, get_chat_model
from app.storage.kedb_store.store import KedbStore, new_articulo_id
from app.storage.vector_db.client import get_tickets_collection

logger = logging.getLogger(__name__)

# Keyword seeds for metadata-only clustering (avoids loading all embeddings).
_DEFAULT_KEYWORDS = (
    "kyocera",
    "vpn",
    "globalprotect",
    "buzón",
    "buzon",
    "correo",
    "std",
    "impresora",
)

KEDB_TEMPLATE = """
# {titulo}

## Síntoma
{sintoma}

## Categoría
{categoria}

## Causa probable
{causa}

## Solución
{solucion}

## Aplicable a
{aplicable_a}

## Trazabilidad
- Tickets fuente: {tickets_fuente}
"""


class KedbGeneratorAgent:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.collection = get_tickets_collection(self.settings)
        self.store = KedbStore(self.settings)
        self.llm = get_chat_model(self.settings)
        self.fetch_batch = max(16, int(self.settings.kedb_cluster_fetch_batch))
        self.max_samples = max(100, int(self.settings.kedb_cluster_max_samples))

    def _get_all_ids(self) -> list[str]:
        """Fetch ids in pages — never request embeddings in bulk."""
        ids: list[str] = []
        offset = 0
        while True:
            try:
                chunk = self.collection.get(
                    include=[],
                    limit=self.fetch_batch * 5,
                    offset=offset,
                )
            except TypeError:
                # Older chroma stubs may not support limit/offset.
                chunk = self.collection.get(include=[])
                return list(chunk.get("ids") or [])
            batch_ids = list(chunk.get("ids") or [])
            if not batch_ids:
                break
            ids.extend(str(i) for i in batch_ids)
            offset += len(batch_ids)
            if len(batch_ids) < self.fetch_batch * 5:
                break
        return ids

    def _get_rows(
        self,
        ids: list[str],
        *,
        include_embeddings: bool = False,
    ) -> tuple[list[str], list[dict], list[list[float]] | None]:
        """Fetch metadatas (and optional embeddings) in small id batches."""
        include = ["metadatas"]
        if include_embeddings:
            include.append("embeddings")

        out_ids: list[str] = []
        out_metas: list[dict] = []
        out_embeds: list[list[float]] = []

        for i in range(0, len(ids), self.fetch_batch):
            batch_ids = ids[i : i + self.fetch_batch]
            try:
                chunk = self.collection.get(ids=batch_ids, include=include)
            except Exception:
                logger.exception(
                    "Chroma get falló en lote offset=%s size=%s", i, len(batch_ids)
                )
                raise
            got_ids = list(chunk.get("ids") or [])
            metas = list(chunk.get("metadatas") or [])
            if include_embeddings:
                embeds = list(chunk.get("embeddings") or [])
                if len(embeds) != len(got_ids):
                    logger.warning(
                        "Lote embeddings incompleto (%s vs %s); se omite lote",
                        len(embeds),
                        len(got_ids),
                    )
                    continue
                out_embeds.extend(embeds)
            for tid, meta in zip(got_ids, metas):
                out_ids.append(str(tid))
                out_metas.append(meta or {})

        if include_embeddings:
            return out_ids, out_metas, out_embeds
        return out_ids, out_metas, None

    def cluster_tickets(self, min_cluster_size: int = 5) -> list[dict]:
        """HU08a — HDBSCAN on a sampled subset of ticket embeddings (batched fetch)."""
        all_ids = self._get_all_ids()
        if not all_ids:
            return []

        rng = random.Random(self.settings.random_seed)
        if len(all_ids) > self.max_samples:
            sample_ids = rng.sample(all_ids, self.max_samples)
            logger.info(
                "HDBSCAN sample: %s/%s tickets (batch=%s)",
                len(sample_ids),
                len(all_ids),
                self.fetch_batch,
            )
        else:
            sample_ids = all_ids

        ids, metas, embeds = self._get_rows(sample_ids, include_embeddings=True)
        if not ids or not embeds:
            return []

        embeddings = np.asarray(embeds, dtype=np.float32)
        if embeddings.ndim != 2 or embeddings.shape[0] < min_cluster_size:
            return []

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(embeddings)

        clusters: dict[int, list[dict]] = {}
        for tid, label, meta in zip(ids, labels, metas):
            if label < 0:
                continue
            clusters.setdefault(int(label), []).append({"ticket_id": tid, **meta})

        return [
            {"cluster_id": cid, "tickets": tickets, "size": len(tickets)}
            for cid, tickets in clusters.items()
            if len(tickets) >= min_cluster_size
        ]

    def synthesize_article(self, cluster: dict) -> KedbArticulo:
        """HU08b — LLM synthesis for a cluster."""
        tickets = cluster["tickets"]
        ticket_ids = [t["ticket_id"] for t in tickets]
        categoria = tickets[0].get("categoria", "General")
        samples = "\n\n".join(
            f"Ticket {t['ticket_id']}:\nTítulo: {t.get('titulo', '')}\nSolución: {t.get('solucion', '')}"
            for t in tickets[:20]
        )

        prompt = f"""Eres un experto técnico de Mesa de Ayuda del MTC.
A partir de estos tickets resueltos similares, genera un artículo KEDB en JSON con campos:
titulo, sintoma, causa, solucion, aplicable_a.

Tickets:
{samples}

Responde SOLO con JSON válido."""

        response = self.llm.invoke(prompt)
        content = extract_json(str(response.content))

        articulo = KedbArticulo(
            articulo_id=new_articulo_id(),
            titulo=content.get("titulo", f"Artículo clúster {cluster.get('cluster_id')}"),
            categoria=categoria,
            sintoma=content.get("sintoma", ""),
            causa=content.get("causa", ""),
            solucion=content.get("solucion", ""),
            tickets_fuente=ticket_ids,
            fecha_generacion=datetime.now(timezone.utc),
            estado=KedbEstado.BORRADOR,
            aplicable_a=content.get("aplicable_a", "Sedes MTC"),
        )
        self.store.create(articulo)
        return articulo

    def _metadata_keyword_clusters(
        self,
        keywords: tuple[str, ...] = _DEFAULT_KEYWORDS,
        min_size: int = 5,
    ) -> list[dict]:
        """Build clusters from titles in metadata only (no embedding payload)."""
        all_ids = self._get_all_ids()
        if not all_ids:
            return []
        ids, metas, _ = self._get_rows(all_ids, include_embeddings=False)
        buckets: dict[str, list[dict]] = {kw: [] for kw in keywords}
        for tid, meta in zip(ids, metas):
            titulo = (meta.get("titulo") or "").lower()
            for kw in keywords:
                if kw.lower() in titulo:
                    buckets[kw].append({"ticket_id": tid, **meta})
                    break

        return [
            {"cluster_id": idx, "tickets": tickets, "size": len(tickets), "keyword": kw}
            for idx, (kw, tickets) in enumerate(buckets.items())
            if len(tickets) >= min_size
        ]

    def generate_from_cluster_keyword(self, keyword: str, min_size: int = 5) -> KedbArticulo | None:
        """Generate article for a specific keyword cluster (demo Kyocera)."""
        all_ids = self._get_all_ids()
        if not all_ids:
            return None
        ids, metas, _ = self._get_rows(all_ids, include_embeddings=False)
        matching = []
        kw = keyword.lower()
        for tid, meta in zip(ids, metas):
            titulo = (meta.get("titulo") or "").lower()
            if kw in titulo:
                matching.append({"ticket_id": tid, **meta})
        if len(matching) < min_size:
            return None
        cluster = {"cluster_id": 0, "tickets": matching, "size": len(matching)}
        return self.synthesize_article(cluster)

    def generate_all(self, max_articles: int = 50) -> list[KedbArticulo]:
        """Prefer metadata keyword clusters; fall back to sampled HDBSCAN."""
        articles: list[KedbArticulo] = []
        seen_titles: set[str] = set()

        def _add(art: KedbArticulo) -> None:
            key = (art.titulo or "").strip().lower()
            if key in seen_titles:
                return
            seen_titles.add(key)
            articles.append(art)

        # 1) Metadata-only clusters (cheap; does not dump all embeddings)
        try:
            meta_clusters = self._metadata_keyword_clusters()
            meta_clusters.sort(key=lambda c: c["size"], reverse=True)
            for cluster in meta_clusters:
                if len(articles) >= max_articles:
                    break
                try:
                    _add(self.synthesize_article(cluster))
                except Exception:
                    logger.exception(
                        "Síntesis KEDB (keyword=%s) falló size=%s",
                        cluster.get("keyword"),
                        cluster.get("size"),
                    )
        except Exception:
            logger.exception("Clustering por keyword/metadata falló")

        # 2) Sampled HDBSCAN if we still need articles
        if len(articles) < max_articles:
            try:
                clusters = self.cluster_tickets()
                clusters.sort(key=lambda c: c["size"], reverse=True)
                for cluster in clusters:
                    if len(articles) >= max_articles:
                        break
                    try:
                        _add(self.synthesize_article(cluster))
                    except Exception:
                        logger.exception(
                            "Síntesis KEDB falló para cluster size=%s",
                            cluster.get("size"),
                        )
            except Exception:
                logger.exception("HDBSCAN muestreado falló; se continúa con lo ya generado")

        return articles[:max_articles]

    def generate_demo_fixture(self) -> KedbArticulo:
        """Pre-built Kyocera article for demo (idempotent: one clean borrador)."""
        from app.fixtures.kyocera_demo import ensure_clean_demo_articulo

        articulo, _removed = ensure_clean_demo_articulo(self.store)
        return articulo
