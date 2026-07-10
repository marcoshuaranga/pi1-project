"""C6 — KEDB generator (HDBSCAN + LLM synthesis)."""

import json
from datetime import datetime, timezone

import hdbscan
import numpy as np
from openai import OpenAI

from app.config import Settings, get_settings
from app.schemas import KedbArticulo, KedbEstado
from app.services.embeddings import EmbeddingService
from app.storage.kedb_store.store import KedbStore, new_articulo_id
from app.storage.vector_db.client import get_tickets_collection


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
        self.embedder = EmbeddingService(self.settings)
        self.collection = get_tickets_collection(self.settings)
        self.store = KedbStore(self.settings)
        self.llm = OpenAI(api_key=self.settings.openai_api_key)

    def cluster_tickets(self, min_cluster_size: int = 5) -> list[dict]:
        """HU08a — HDBSCAN clustering on ticket embeddings."""
        data = self.collection.get(include=["embeddings", "metadatas"])
        if not data["ids"]:
            return []

        embeddings = np.array(data["embeddings"])
        ids = data["ids"]
        metas = data["metadatas"]

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
            clusters.setdefault(label, []).append({"ticket_id": tid, **meta})

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

        response = self.llm.chat.completions.create(
            model=self.settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = json.loads(response.choices[0].message.content or "{}")

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

    def generate_from_cluster_keyword(self, keyword: str, min_size: int = 5) -> KedbArticulo | None:
        """Generate article for a specific keyword cluster (demo Kyocera)."""
        data = self.collection.get(include=["metadatas"])
        matching = []
        for tid, meta in zip(data["ids"], data["metadatas"]):
            titulo = meta.get("titulo", "").lower()
            if keyword.lower() in titulo:
                matching.append({"ticket_id": tid, **meta})
        if len(matching) < min_size:
            return None
        cluster = {"cluster_id": 0, "tickets": matching, "size": len(matching)}
        return self.synthesize_article(cluster)

    def generate_all(self, max_articles: int = 50) -> list[KedbArticulo]:
        clusters = self.cluster_tickets()
        clusters.sort(key=lambda c: c["size"], reverse=True)
        articles = []
        for cluster in clusters[:max_articles]:
            try:
                articles.append(self.synthesize_article(cluster))
            except Exception:
                continue
        return articles

    def generate_demo_fixture(self) -> KedbArticulo:
        """Pre-built Kyocera article for demo (fallback without LLM)."""
        articulo = KedbArticulo(
            articulo_id=new_articulo_id(),
            titulo="Configuración de impresora Kyocera TaskAlfa 7003i",
            categoria="Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional",
            sintoma=(
                "El usuario no puede imprimir o requiere configurar la impresora "
                "multifuncional Kyocera 7003 en su equipo."
            ),
            causa=(
                "Impresora predeterminada no configurada correctamente, "
                "o driver de la Kyocera 7003 no instalado."
            ),
            solucion=(
                "1. Instalar/verificar el driver de la impresora Kyocera 7003.\n"
                "2. Configurar la impresora como predeterminada.\n"
                "3. Validar con hoja de prueba."
            ),
            tickets_fuente=["96044", "95984", "95645", "95439", "94922"],
            fecha_generacion=datetime.now(timezone.utc),
            estado=KedbEstado.BORRADOR,
            aplicable_a="Impresoras Kyocera TaskAlfa 7003i en sedes MTC",
        )
        self.store.create(articulo)
        return articulo
