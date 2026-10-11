"""Normaliza las etiquetas en texto libre de los expertos a GOLDEN_CATEGORIES.

Uso:
    uv run python scripts/normalize_golden_labels.py
    uv run python scripts/build_golden_set.py score

Lee SIEMPRE las planillas originales de golden_annotation/originales/ (se respaldan la primera
vez) y reescribe experto1.xlsx / experto2.xlsx con la categoría sugerida por
pi_core.evaluation.golden_suggest. Cada fila conserva la etiqueta original del experto y el origen
de la categoría (directa / sugerida-alta|media|baja / pendiente-revision) para poder auditarlo.
Reporta el Kappa sobre las etiquetas originales (el que reflejan los expertos) además del normalizado.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from sklearn.metrics import cohen_kappa_score

from pi_core.config import get_settings
from pi_core.constants import GOLDEN_CATEGORIES, TOP9_CATEGORIES
from pi_core.evaluation.golden_set import ANNOTATION_DIR, EXPERT1_FILE, EXPERT2_FILE
from pi_core.evaluation.golden_suggest import suggest_category

# Sin pistas en título ni solución: se asigna la más frecuente del par y queda marcado para revisión.
_FALLBACK_PENDIENTE = TOP9_CATEGORIES[3]


def _origen(etiqueta: str, confianza: str, pendiente: bool) -> str:
    if pendiente:
        return "pendiente-revision"
    return "directa" if confianza == "alta" and etiqueta in ("correo", "impresora", "cpu", "std", "aplicaciones") else (
        f"sugerida-{confianza}"
    )


def _normalize(src: Path, dst: Path, evals: dict) -> dict[str, str]:
    wb = load_workbook(src)
    ws = wb["anotacion"]
    ws.cell(row=1, column=4, value="etiqueta_original_experto")
    ws.cell(row=1, column=5, value="origen_categoria")
    raw: dict[str, str] = {}
    for row in range(2, ws.max_row + 1):
        tid = str(ws.cell(row=row, column=1).value)
        etiqueta = str(ws.cell(row=row, column=3).value).strip()
        raw[tid] = etiqueta
        sol = evals.get(tid, {}).get("solucion_anon") or ""
        cat, conf, _ = suggest_category(etiqueta, str(ws.cell(row=row, column=2).value), sol)
        pendiente = cat is None
        ws.cell(row=row, column=3, value=cat or _FALLBACK_PENDIENTE)
        ws.cell(row=row, column=4, value=etiqueta)
        ws.cell(row=row, column=5, value=_origen(etiqueta, conf, pendiente))

    cats = wb["categorias"]
    cats.delete_rows(1, cats.max_row)
    for c in GOLDEN_CATEGORIES:
        cats.append([c])
    dv = DataValidation(type="list", formula1=f"=categorias!$A$1:$A${len(GOLDEN_CATEGORIES)}", allow_blank=True)
    dv.add(f"C2:C{ws.max_row}")
    ws.add_data_validation(dv)
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 20
    wb.save(dst)
    return raw


def main() -> None:
    processed = Path(get_settings().data_processed_path)
    ann = processed / ANNOTATION_DIR
    orig = ann / "originales"
    orig.mkdir(exist_ok=True)
    for name in (EXPERT1_FILE, EXPERT2_FILE):
        if not (orig / name).exists():
            shutil.copy2(ann / name, orig / name)

    evals = {
        t["ticket_id"]: t for t in json.loads((processed / "tickets_eval.json").read_text(encoding="utf-8"))
    }
    raw1 = _normalize(orig / EXPERT1_FILE, ann / EXPERT1_FILE, evals)
    raw2 = _normalize(orig / EXPERT2_FILE, ann / EXPERT2_FILE, evals)

    ids = list(raw2)
    k_raw = cohen_kappa_score([raw1[t] for t in ids], [raw2[t] for t in ids])
    agree = sum(raw1[t] == raw2[t] for t in ids)
    print(f"Kappa sobre etiquetas ORIGINALES de los expertos (n={len(ids)}): {k_raw:.4f}  acuerdo {agree}/{len(ids)}")
    print(f"Planillas normalizadas en {ann} (originales respaldadas en {orig})")


if __name__ == "__main__":
    main()
