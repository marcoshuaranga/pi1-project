"""Unit tests for KEDB clustering without bulk Chroma embedding dumps."""

from __future__ import annotations

import numpy as np


class FakeCollection:
    def __init__(self, n: int = 120, dim: int = 8):
        self.ids = [f"T{i}" for i in range(n)]
        rng = np.random.default_rng(0)
        # Two tight blobs → HDBSCAN should find clusters
        a = rng.normal(0.0, 0.05, size=(n // 2, dim))
        b = rng.normal(3.0, 0.05, size=(n - n // 2, dim))
        self.embeds = np.vstack([a, b]).astype(np.float32)
        self.metas = []
        for i, tid in enumerate(self.ids):
            title = "Configuración Kyocera 7003" if i < n // 2 else "Sin acceso VPN GlobalProtect"
            self.metas.append(
                {
                    "titulo": title,
                    "solucion": f"pasos largos de resolución para {tid} " * 5,
                    "categoria": "Impresora" if i < n // 2 else "VPN",
                }
            )

    def get(self, ids=None, include=None, limit=None, offset=None):
        include = include or []
        if ids is None:
            start = offset or 0
            end = len(self.ids) if limit is None else start + limit
            sel = list(range(start, min(end, len(self.ids))))
        else:
            index = {tid: i for i, tid in enumerate(self.ids)}
            sel = [index[i] for i in ids if i in index]

        out = {"ids": [self.ids[i] for i in sel]}
        if "metadatas" in include:
            out["metadatas"] = [self.metas[i] for i in sel]
        if "embeddings" in include:
            out["embeddings"] = [self.embeds[i].tolist() for i in sel]
        return out


def test_cluster_tickets_uses_sample_and_finds_clusters(monkeypatch):
    from pi_core.agents.kedb_generator import agent as kedb_mod

    fake = FakeCollection(120)

    class FakeStore:
        def create(self, articulo):
            return articulo

    monkeypatch.setattr(kedb_mod, "get_tickets_collection", lambda settings=None: fake)
    monkeypatch.setattr(kedb_mod, "KedbStore", lambda settings=None: FakeStore())
    monkeypatch.setattr(kedb_mod, "get_chat_model", lambda settings=None: object())

    gen = kedb_mod.KedbGeneratorAgent()
    gen.max_samples = 80
    gen.fetch_batch = 16
    clusters = gen.cluster_tickets(min_cluster_size=5)
    assert len(clusters) >= 1
    assert all(c["size"] >= 5 for c in clusters)


def test_metadata_keyword_clusters_no_embeddings(monkeypatch):
    from pi_core.agents.kedb_generator import agent as kedb_mod

    fake = FakeCollection(40)

    class FakeStore:
        def create(self, articulo):
            return articulo

    monkeypatch.setattr(kedb_mod, "get_tickets_collection", lambda settings=None: fake)
    monkeypatch.setattr(kedb_mod, "KedbStore", lambda settings=None: FakeStore())
    monkeypatch.setattr(kedb_mod, "get_chat_model", lambda settings=None: object())

    gen = kedb_mod.KedbGeneratorAgent()
    clusters = gen._metadata_keyword_clusters(min_size=5)
    keys = {c.get("keyword") for c in clusters}
    assert "kyocera" in keys
    assert "vpn" in keys or "globalprotect" in keys
