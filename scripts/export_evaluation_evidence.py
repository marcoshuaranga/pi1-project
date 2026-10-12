"""Evidencia versionada de la evaluación del golden set (C9).

Corre `EvaluationFramework.run_golden_evaluation()` y emite por stdout un JSON con las métricas
más la trazabilidad necesaria para citarlas: hash del commit evaluado, fecha, tamaño de muestra,
semilla y `tipo_evidencia`. Recall@5 exacto (ticket fuente recuperado) y Recall@5 por categoría
(proxy semántico) van por separado.

Necesita Chroma/LiteLLM, así que se ejecuta dentro del contenedor `api` (ver docs/evidence/sprint3/README.md):
el hash del commit se pasa por la variable GIT_COMMIT porque el contenedor no tiene git.
"""

import json
import os
import subprocess
import sys
from datetime import UTC, datetime

from pi_core.config import get_settings
from pi_core.evaluation.metrics import EvaluationFramework


def _commit() -> tuple[str, bool]:
    commit = os.environ.get("GIT_COMMIT")
    dirty = os.environ.get("GIT_DIRTY", "0") == "1"
    if commit:
        return commit, dirty
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    return commit, dirty


def main() -> None:
    commit, dirty = _commit()
    settings = get_settings()
    r = EvaluationFramework().run_golden_evaluation()

    evidencia = {
        "commit_evaluado": commit,
        "arbol_limpio": not dirty,
        "fecha_calculo": r["fecha_calculo"],
        "fecha_exportacion": datetime.now(UTC).isoformat(),
        "dataset": r["dataset"],
        "fuente": r["fuente"],
        "muestra": r["muestra"],
        "muestra_esperada": 185,
        "fuera_top9_excluidos": r["fuera_top9_excluidos"],
        "errores_recuperacion": r["errores_recuperacion"],
        "semilla": settings.random_seed,
        "nota_semilla": (
            "La evaluación del golden set no muestrea: recorre todo golden_set_sample.json. "
            "La semilla (random_seed) solo gobernó el muestreo estratificado del golden set y "
            "la evaluación sobre tickets_eval.json."
        ),
        "tipo_evidencia": r["tipo_evidencia"],
        "metodo": r["metodo"],
        "f1_macro": r["f1_macro"],
        "kappa": r["kappa"],
        "recall_at_5": {
            "exacto": r["recall_at_5"],
            "por_categoria": r["recall_at_5_categoria"],
            "precision_at_5_por_categoria": r["precision_at_5_categoria"],
        },
        "juicio_experto": {k: v for k, v in r.items() if k.endswith("_experto") or "experto_" in k or k == "kappa_relevancia"},
    }
    json.dump(evidencia, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
