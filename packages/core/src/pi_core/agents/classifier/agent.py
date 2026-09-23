"""C3 — Ticket classifier (embedding + kNN over ChromaDB)."""

import json
import logging
from collections import Counter
from pathlib import Path

from pi_core.config import Settings, get_settings
from pi_core.constants import TOP9_CATEGORIES
from pi_core.services.embeddings import get_embedding_service
from pi_core.storage.vector_db.client import get_tickets_collection

logger = logging.getLogger(__name__)


class ClassifierAgent:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.embedder = get_embedding_service()
        self.collection = get_tickets_collection(self.settings)
        self._category_counts: Counter | None = None

    def _load_train_distribution(self) -> Counter:
        if self._category_counts is not None:
            return self._category_counts
        path = Path(self.settings.data_processed_path) / "tickets_train.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self._category_counts = Counter(
                t.get("categoria_top9", "") for t in data if t.get("categoria_top9")
            )
        else:
            self._category_counts = Counter({c: 1 for c in TOP9_CATEGORIES})
        return self._category_counts

    def classify(self, texto: str) -> dict:
        vector = self.embedder.embed_text(texto, cache_key=f"query:{texto[:100]}")
        try:
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=15,
                where={"split": "train"},
            )
        except Exception:
            logger.debug("Filtro split=train no disponible; reintento sin where", exc_info=True)
            results = self.collection.query(query_embeddings=[vector], n_results=15)

        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not metas:
            # Keyword fallback
            cat = self._keyword_fallback(texto)
            return {"categoria": cat, "confianza": 0.5, "top3": [{"categoria": cat, "score": 0.5}]}

        votes: Counter = Counter()
        scores: dict[str, list[float]] = {}
        for meta, dist in zip(metas, distances, strict=False):
            cat = meta.get("categoria", "")
            if not cat:
                continue
            sim = 1.0 - dist
            votes[cat] += sim
            scores.setdefault(cat, []).append(sim)

        if not votes:
            cat = self._keyword_fallback(texto)
            return {"categoria": cat, "confianza": 0.5, "top3": [{"categoria": cat, "score": 0.5}]}

        top_cat = votes.most_common(1)[0][0]
        top_score = sum(scores[top_cat]) / len(scores[top_cat])
        total = sum(votes.values())
        confianza = min(0.99, votes[top_cat] / total if total else 0.5)

        top3 = [
            {"categoria": cat, "score": round(sum(scores[cat]) / len(scores[cat]), 3)}
            for cat, _ in votes.most_common(3)
        ]
        return {
            "categoria": top_cat,
            "confianza": round(confianza, 3),
            "top3": top3,
            "similitud_vecinos": round(top_score, 3),
        }

    def _keyword_fallback(self, texto: str) -> str:
        t = texto.lower()
        if any(k in t for k in ("impresora", "kyocera", "imprimir", "escaneo")):
            return TOP9_CATEGORIES[0]
        if any(k in t for k in ("vpn", "remoto", "globalprotect", "escritorio remoto")):
            return TOP9_CATEGORIES[3]
        if any(k in t for k in ("correo", "buzón", "buzon", "outlook")):
            return TOP9_CATEGORIES[8]
        if any(k in t for k in ("cuenta", "bloqueo", "contraseña", "password")):
            return TOP9_CATEGORIES[5]
        dist = self._load_train_distribution()
        return dist.most_common(1)[0][0] if dist else TOP9_CATEGORIES[0]
