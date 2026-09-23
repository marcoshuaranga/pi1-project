"""CLI — C9 golden set: muestreo estratificado + doble anotación ciega (opción B).

Uso:
    uv run python scripts/build_golden_set.py sample
    # ... 2 expertos llenan data/processed/golden_annotation/experto{1,2}.xlsx, a ciegas ...
    uv run python scripts/build_golden_set.py score
"""

import argparse
import sys
from pathlib import Path

# Allow `python scripts/build_golden_set.py` inside Docker (script dir is on sys.path, not /app)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_core.config import get_settings
from pi_core.evaluation.golden_set import (
    ANNOTATION_DIR,
    EXPERT1_FILE,
    EXPERT2_FILE,
    build_pool,
    score_and_merge,
)


def cmd_sample(args: argparse.Namespace) -> None:
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    seed = args.seed if args.seed is not None else settings.random_seed

    build_pool(processed, seed, n=args.n, n_kappa=args.n_kappa)

    print(f"Pool: {processed / 'golden_pool.json'} ({args.n} tickets, {args.n_kappa} con doble anotación)")
    print("Planillas para llenar A CIEGAS (sin ver categoria_top9 ni la respuesta del otro experto):")
    print(f"  Experto 1 (todos, {args.n} tickets):        {processed / ANNOTATION_DIR / EXPERT1_FILE}")
    print(f"  Experto 2 (solo doble anotación, {args.n_kappa}): {processed / ANNOTATION_DIR / EXPERT2_FILE}")
    print("Cuando ambas planillas estén llenas: uv run python scripts/build_golden_set.py score")


def cmd_score(_args: argparse.Namespace) -> None:
    settings = get_settings()
    processed = Path(settings.data_processed_path)
    result = score_and_merge(processed)

    print(f"Kappa inter-anotador (n={result['n_doble_anotado']}): {result['kappa']}")
    print(f"Golden set: {result['golden_path']} ({result['n_total']} entradas)")
    if result["n_arbitraje_pendiente"]:
        print(
            f"AVISO: {result['n_arbitraje_pendiente']} tickets con desacuerdo quedaron con "
            "categoria_gold=null (necesita_arbitraje=true) — resuélvelos a mano (tercer árbitro "
            "o discusión) editando golden_set_sample.json antes de evaluar sobre el golden set."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_sample = sub.add_parser("sample", help="Muestreo estratificado + exportar planillas de anotación")
    p_sample.add_argument("--n", type=int, default=200)
    p_sample.add_argument("--n-kappa", type=int, default=30)
    p_sample.add_argument("--seed", type=int, default=None)
    p_sample.set_defaults(func=cmd_sample)

    p_score = sub.add_parser("score", help="Leer planillas llenas, calcular Kappa y escribir golden_set_sample.json")
    p_score.set_defaults(func=cmd_score)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
