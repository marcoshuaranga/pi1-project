"""Seed demo KEDB fixture, golden set samples, and evaluation cache."""

import json
import sys
import uuid
from pathlib import Path

# Allow `python scripts/seed_demo.py` inside Docker (script dir is on sys.path, not /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_core.config import get_settings
from pi_core.fixtures.kyocera_demo import ensure_clean_demo_articulo
from pi_core.storage.kedb_store.store import KedbStore


def seed_demo_kedb():
    """Idempotent Kyocera demo article (DEMO.md Escena 2): one clean borrador."""
    store = KedbStore()
    articulo, removed = ensure_clean_demo_articulo(store, refresh_fixture=True)
    if removed:
        print(f"Removed {removed} previous Kyocera borrador(es)")
    print(f"Demo KEDB article ready: {articulo.articulo_id}")
    print(f"  estado={articulo.estado.value}  titulo={articulo.titulo}")
    print(f"  tickets_fuente={len(articulo.tickets_fuente)}")

    try:
        from pi_core.enrich.reindex import reindex_kyocera_cluster

        n = reindex_kyocera_cluster(ticket_ids=list(articulo.tickets_fuente))
        print(f"  tickets Chroma enriquecidos: {n}")
    except Exception as exc:
        print(f"  aviso: no se pudo reindexar resoluciones Kyocera ({exc})")
    return articulo


def seed_golden_set_sample(n: int = 50):
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    eval_path = processed / "tickets_eval.json"
    if not eval_path.exists():
        print("No eval split found — run pipeline first")
        return

    out = processed / "golden_set_sample.json"
    if out.exists() and any(
        e.get("doble_anotacion") is not None for e in json.loads(out.read_text(encoding="utf-8"))
    ):
        print(f"Golden set real (doble anotación) ya existe en {out} — no se sobrescribe con el stub")
        return

    tickets = json.loads(eval_path.read_text(encoding="utf-8"))
    golden = []
    for t in tickets[:n]:
        golden.append(
            {
                "golden_id": str(uuid.uuid4()),
                "ticket_id": t["ticket_id"],
                "categoria_experto1": t.get("categoria_top9"),
                "categoria_sistema": None,
                "split": "eval",
            }
        )

    out.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Golden set sample: {len(golden)} entries → {out}")


def seed_evaluation(sample_size: int = 50):
    """Precompute C9 metrics cache for demo backup figures."""
    from pi_core.evaluation.metrics import EvaluationFramework

    settings = get_settings()
    processed = Path(settings.data_processed_path)
    eval_path = processed / "tickets_eval.json"
    if not eval_path.exists():
        print("No eval split found — skip evaluation (run pipeline first)")
        return None

    try:
        result = EvaluationFramework().run_evaluation(sample_size=sample_size)
        print(
            f"Evaluation cache: f1={result.get('f1_macro')} "
            f"recall@5={result.get('recall_at_5')} "
            f"muestra={result.get('muestra')} → {processed / 'evaluation_results.json'}"
        )
        return result
    except Exception as exc:
        print(f"Evaluation skipped ({exc})")
        return None


if __name__ == "__main__":
    seed_demo_kedb()
    seed_golden_set_sample()
    seed_evaluation()
