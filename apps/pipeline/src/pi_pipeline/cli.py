"""Pipeline CLI for batch jobs (docker compose run pipeline ...)."""

import argparse
import sys
from pathlib import Path

from pi_core.config import get_settings
from pi_pipeline.ingest.pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(description="PI1 Data Pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("extract", help="Extract sample from raw xlsx")
    sub.add_parser("anonymize", help="Anonymize extracted sample")
    sub.add_parser("ingest", help="Normalize and create splits")
    sub.add_parser("embed", help="Generate embeddings in ChromaDB")
    sub.add_parser(
        "enrich-kyocera",
        help="Reindex Kyocera demo cluster with enriched resolutions",
    )
    sub.add_parser("full", help="Run full pipeline")

    args = parser.parse_args()
    settings = get_settings()
    pipeline = IngestionPipeline(settings)
    raw_path = Path("/data/raw/Tickets_Consolidados.xlsx")

    if not raw_path.exists():
        raw_path = Path("data/raw/Tickets_Consolidados.xlsx")

    if args.command == "extract":
        if not raw_path.exists():
            print(f"ERROR: No se encontró {raw_path}", file=sys.stderr)
            sys.exit(1)
        df = pipeline.run_extract_sample(str(raw_path))
        print(f"Sample extraída: {len(df)} tickets")

    elif args.command == "anonymize":
        df = pipeline.run_anonymize()
        print(f"Anonimizados: {len(df)} tickets")

    elif args.command == "ingest":
        tickets = pipeline.run_ingest()
        print(f"Ingestados: {len(tickets)} tickets")

    elif args.command == "embed":
        count = pipeline.run_embeddings()
        print(f"Embeddings generados: {count}")

    elif args.command == "enrich-kyocera":
        from pi_core.enrich.reindex import reindex_kyocera_cluster

        count = reindex_kyocera_cluster()
        print(f"Kyocera reindexado con resoluciones enriquecidas: {count}")

    elif args.command == "full":
        if not raw_path.exists():
            print(f"ERROR: No se encontró {raw_path}", file=sys.stderr)
            sys.exit(1)
        result = pipeline.run_full(str(raw_path))
        print(f"Pipeline completo: {result}")


if __name__ == "__main__":
    main()
