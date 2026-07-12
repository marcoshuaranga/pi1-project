"""Seed demo KEDB fixture, golden set samples, and evaluation cache."""

import json
import sys
import uuid
from pathlib import Path

# Allow `python scripts/seed_demo.py` inside Docker (script dir is on sys.path, not /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.fixtures.kyocera_demo import ensure_clean_demo_articulo
from app.storage.kedb_store.store import KedbStore


def seed_demo_kedb():
    """Idempotent Kyocera demo article (DEMO.md Escena 2): one clean borrador."""
    store = KedbStore()
    articulo, removed = ensure_clean_demo_articulo(store, refresh_fixture=True)
    if removed:
        print(f"Removed {removed} previous Kyocera borrador(es)")
    print(f"Demo KEDB article ready: {articulo.articulo_id}")
    print(f"  estado={articulo.estado.value}  titulo={articulo.titulo}")
    print(f"  tickets_fuente={len(articulo.tickets_fuente)}")
    return articulo


def seed_golden_set_sample(n: int = 50):
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    eval_path = processed / "tickets_eval.json"
    if not eval_path.exists():
        print("No eval split found — run pipeline first")
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

    out = processed / "golden_set_sample.json"
    out.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Golden set sample: {len(golden)} entries → {out}")


def seed_evaluation(sample_size: int = 50):
    """Precompute C9 metrics cache for demo backup figures."""
    from app.evaluation.metrics import EvaluationFramework

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
