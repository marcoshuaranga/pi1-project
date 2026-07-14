"""C2 — Ingestion: normalize, split, embed, load ChromaDB."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.config import Settings, get_settings
from app.pipeline.anonymize.anonymizer import Anonymizer
from app.pipeline.enrich.reindex import CACHE_SUFFIX
from app.pipeline.enrich.resolutions import SOLUCION_META_MAX, enrich_resolution
from app.pipeline.ingest.normalize import (
    assign_split,
    extract_sample,
    load_glpi_excel,
    parse_date,
)
from app.schemas import Ticket
from app.services.embeddings import EmbeddingService
from app.storage.vector_db.client import get_tickets_collection


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        for col_lower, col_orig in cols_lower.items():
            if cand in col_lower:
                return col_orig
    return None


class IngestionPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.anonymizer = Anonymizer()
        # Pipeline may use disk cache for resume; still skip if file is multi-GB.
        self.embedder = EmbeddingService(self.settings, load_disk_cache=True)
        self.output_dir = Path(self.settings.data_processed_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_extract_sample(self, raw_path: str) -> pd.DataFrame:
        df = load_glpi_excel(raw_path)
        sample = extract_sample(df)
        out = self.output_dir / "sample_raw.parquet"
        sample.to_parquet(out, index=False)
        return sample

    def run_anonymize(self, sample_path: str | None = None) -> pd.DataFrame:
        path = Path(sample_path or self.output_dir / "sample_raw.parquet")
        df = pd.read_parquet(path)
        anon_titles = []
        anon_solutions = []
        for _, row in df.iterrows():
            anon_titles.append(self.anonymizer.anonymize(str(row.get("_titulo", ""))).text)
            anon_solutions.append(self.anonymizer.anonymize(str(row.get("_solucion", ""))).text)
        df["_titulo_anon"] = anon_titles
        df["_solucion_anon"] = anon_solutions
        out = self.output_dir / "sample_anonymized.parquet"
        df.to_parquet(out, index=False)
        return df

    def run_ingest(self, anon_path: str | None = None) -> list[Ticket]:
        path = Path(anon_path or self.output_dir / "sample_anonymized.parquet")
        df = pd.read_parquet(path)

        fecha_col = _find_column(df, ["fecha", "apertura", "cierre", "date"])
        tickets: list[Ticket] = []
        records = []

        for _, row in df.iterrows():
            fecha = parse_date(row[fecha_col]) if fecha_col and fecha_col in df.columns else None
            split = assign_split(fecha)
            sol = str(row.get("_solucion_anon", ""))
            ticket = Ticket(
                ticket_id=str(row["_ticket_id"]),
                fecha_apertura=fecha,
                categoria=row.get("_categoria_top9"),
                categoria_top9=row.get("_categoria_top9"),
                titulo_anon=str(row.get("_titulo_anon", "")),
                solucion_anon=sol,
                tiene_solucion=len(sol) > 10,
                longitud_solucion=len(sol),
                estado="cerrado",
                split=split,
            )
            tickets.append(ticket)
            records.append(ticket.model_dump(mode="json"))

        # Save canonical JSON splits
        for split_name in ("train", "eval", "holdout"):
            split_data = [t for t in records if t.get("split") == split_name]
            (self.output_dir / f"tickets_{split_name}.json").write_text(
                json.dumps(split_data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

        (self.output_dir / "tickets_all.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return tickets

    def run_embeddings(self, tickets: list[Ticket] | None = None) -> int:
        if tickets is None:
            data = json.loads((self.output_dir / "tickets_all.json").read_text(encoding="utf-8"))
            tickets = [Ticket(**t) for t in data]

        collection = get_tickets_collection(self.settings)
        texts = []
        ids = []
        metadatas = []
        cache_keys = []
        enriched_count = 0
        for t in tickets:
            titulo = t.titulo_anon or ""
            titulo_l = titulo.lower()
            is_kyocera_cluster = "kyocera" in titulo_l or "7003" in titulo_l
            if not t.tiene_solucion and not is_kyocera_cluster:
                continue
            enriched = enrich_resolution(
                titulo=titulo,
                solucion=t.solucion_anon,
                categoria=t.categoria_top9,
                ticket_id=t.ticket_id,
                force=is_kyocera_cluster and not t.tiene_solucion,
            )
            solucion = enriched.solucion[:SOLUCION_META_MAX]
            if enriched.enriched:
                enriched_count += 1
            text = f"{titulo}\n{solucion}"
            texts.append(text)
            ids.append(t.ticket_id)
            cache_keys.append(
                f"{t.ticket_id}:{CACHE_SUFFIX}" if enriched.enriched else t.ticket_id
            )
            metadatas.append(
                {
                    "categoria": t.categoria_top9 or "",
                    "split": t.split or "train",
                    "titulo": titulo[:500],
                    "solucion": solucion,
                    "tipo": "ticket",
                    "enriched": "true" if enriched.enriched else "false",
                    "enrich_domain": enriched.domain or "",
                }
            )

        batch_size = self.settings.batch_size
        total = 0
        total_batches = (len(texts) + batch_size - 1) // batch_size
        print(f"Resoluciones enriquecidas para índice: {enriched_count}/{len(texts)}")
        for i in range(0, len(texts), batch_size):
            batch_num = i // batch_size + 1
            batch_texts = texts[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            batch_meta = metadatas[i : i + batch_size]
            batch_keys = cache_keys[i : i + batch_size]
            print(f"Embeddings lote {batch_num}/{total_batches} ({len(batch_ids)} tickets)...")
            vectors = self.embedder.embed_batch(batch_texts, cache_keys=batch_keys)
            collection.upsert(
                ids=batch_ids,
                embeddings=vectors,
                documents=batch_texts,
                metadatas=batch_meta,
            )
            total += len(batch_ids)
            print(f"  → {total}/{len(texts)} indexados en ChromaDB")

        manifest = {
            "total_embedded": total,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": self.settings.embedding_provider,
            "model": self.settings.embedding_model,
        }
        (self.output_dir / "embeddings_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        return total

    def run_full(self, raw_path: str) -> dict:
        self.run_extract_sample(raw_path)
        self.run_anonymize()
        tickets = self.run_ingest()
        count = self.run_embeddings(tickets)
        return {"tickets": len(tickets), "embedded": count}
