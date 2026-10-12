"""CLI — C9: juicio experto de relevancia de las soluciones sugeridas (Recall@5 "solución útil").

Uso:
    # `sample` consulta Chroma: córrelo donde Chroma sea alcanzable (p. ej. dentro del contenedor worker)
    uv run python scripts/build_relevance_set.py sample [--n 30]
    # ... 2 expertos llenan data/processed/golden_annotation/relevancia_experto{1,2}.xlsx, a ciegas ...
    uv run python scripts/build_relevance_set.py score
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_core.config import get_settings
from pi_core.evaluation.golden_set import ANNOTATION_DIR
from pi_core.evaluation.relevance import (
    EXPERT1_FILE,
    EXPERT2_FILE,
    POOL_FILE,
    build_relevance_pool,
    score_relevance,
)


def cmd_sample(args: argparse.Namespace) -> None:
    from pi_core.agents.rag.agent import RAGAgent

    settings = get_settings()
    processed = Path(settings.data_processed_path)
    seed = args.seed if args.seed is not None else settings.random_seed
    items = build_relevance_pool(processed, RAGAgent(), n=args.n, seed=seed)
    print(f"Pool: {processed / POOL_FILE} ({len(items)} tickets x 5 soluciones = {len(items) * 5} juicios por experto)")
    for f in (EXPERT1_FILE, EXPERT2_FILE):
        print(f"  {processed / ANNOTATION_DIR / f}")
    print("Cuando ambas estén llenas: uv run python scripts/build_relevance_set.py score")


def cmd_score(_args: argparse.Namespace) -> None:
    result = score_relevance(Path(get_settings().data_processed_path))
    print(f"Recall@5 experto (ambos Sí): {result['recall_at_5_experto']}  laxo (alguno Sí): {result['recall_at_5_experto_laxo']}")
    print(f"Precisión@5 experto: {result['precision_at_5_experto']}  Kappa relevancia: {result['kappa_relevancia']}")
    print(f"Por experto: {result['por_experto']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample", help="Recuperar soluciones y generar las planillas de relevancia")
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_sample)
    sub.add_parser("score", help="Leer planillas llenas y calcular Recall@5 experto").set_defaults(func=cmd_score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
