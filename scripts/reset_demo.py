#!/usr/bin/env python3
"""Reset demo state to the initial clean Kyocera seed (pre-Escena 2).

Removes Kyocera KEDB articles in any estado (borrador / validado / obsoleto),
purges them from Chroma + Live Docs Markdown, then creates one fresh borrador
with ~142 tickets_fuente — ready for the sponsor session.

Usage (Docker):
  docker compose exec api python scripts/reset_demo.py

Usage (local, with env pointing at the same DB/Chroma):
  PYTHONPATH=. python scripts/reset_demo.py

Options:
  --no-chroma     skip Chroma KEDB cleanup
  --no-markdown   skip deleting Live Docs .md files
  --with-eval     also refresh evaluation_results.json (slow; needs OpenAI/embeddings)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_core.fixtures.kyocera_demo import reset_demo_state
from pi_core.storage.kedb_store.store import KedbStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset demo KEDB to initial seed")
    parser.add_argument("--no-chroma", action="store_true", help="Do not delete from Chroma")
    parser.add_argument(
        "--no-markdown", action="store_true", help="Do not delete Live Docs markdown"
    )
    parser.add_argument(
        "--with-eval",
        action="store_true",
        help="Also recompute C9 evaluation cache",
    )
    args = parser.parse_args()

    store = KedbStore()
    summary = reset_demo_state(
        store,
        clear_chroma=not args.no_chroma,
        clear_markdown=not args.no_markdown,
        refresh_fixture=True,
    )
    art = summary["articulo"]

    print("=== Demo reset complete ===")
    print(f"  Removed from SQLite : {summary['removed_db']} article(s)")
    if summary["removed_ids"]:
        print(f"  IDs                : {', '.join(summary['removed_ids'])}")
    print(f"  Chroma KEDB purged : {summary['chroma_deleted']} id(s)")
    print(f"  Markdown removed   : {summary['markdown_deleted']} file(s)")
    print(f"  Fresh borrador     : {art.articulo_id}")
    print(f"  Título             : {art.titulo}")
    print(f"  Estado             : {art.estado.value}")
    print(f"  tickets_fuente     : {len(art.tickets_fuente)}")
    print(f"  Pendientes totales : {summary['pendientes']}")

    try:
        from pi_core.enrich.reindex import reindex_kyocera_cluster

        n = reindex_kyocera_cluster(
            ticket_ids=list(summary["articulo"].tickets_fuente)
        )
        print(f"  Tickets enriquecidos: {n} (Chroma colección tickets)")
    except Exception as exc:
        print(f"  Aviso reindex Kyocera  : {exc}")

    if args.with_eval:
        from scripts.seed_demo import seed_evaluation, seed_golden_set_sample

        print("--- Refreshing evaluation cache ---")
        seed_golden_set_sample()
        seed_evaluation()

    print("Listo para Escena 2/3. Verifica: curl -s http://localhost:8000/kedb/pendientes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
