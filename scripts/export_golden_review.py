"""Exporta a Excel los tickets del golden set cuya etiqueta final difiere de la categoría de GLPI.

Uso:
    uv run python scripts/export_golden_review.py
Escribe data/processed/golden_annotation/revision_discrepancias_glpi.xlsx para que los expertos
confirmen o corrijan la etiqueta. Los tickets "Otros (fuera del top-9)" no se incluyen (por
definición no tienen categoría GLPI equivalente). No modifica el golden set.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

from pi_core.config import get_settings
from pi_core.constants import FUERA_TOP9, GOLDEN_CATEGORIES
from pi_core.evaluation.golden_set import ANNOTATION_DIR

OUT_FILE = "revision_discrepancias_glpi.xlsx"


def main() -> None:
    processed = Path(get_settings().data_processed_path)
    golden = json.loads((processed / "golden_set_sample.json").read_text(encoding="utf-8"))
    evals = {t["ticket_id"]: t for t in json.loads((processed / "tickets_eval.json").read_text(encoding="utf-8"))}

    rows = []
    for e in golden:
        gold, t = e["categoria_gold"], evals[e["ticket_id"]]
        if gold and gold != FUERA_TOP9 and gold != t["categoria_top9"]:
            rows.append((e["ticket_id"], t["titulo_anon"], t.get("solucion_anon") or "", gold, t["categoria_top9"]))
    rows.sort(key=lambda r: (r[3], r[1]))

    wb = Workbook()
    ws = wb.active
    ws.title = "revision"
    ws.append(["ticket_id", "titulo_anon", "solucion_anon", "categoria_golden_actual", "categoria_glpi", "categoria_confirmada (elegir de la lista)"])
    for r in rows:
        ws.append([*r, None])
    cats = wb.create_sheet("categorias")
    for c in GOLDEN_CATEGORIES:
        cats.append([c])
    cats.sheet_state = "hidden"
    dv = DataValidation(type="list", formula1=f"=categorias!$A$1:$A${len(GOLDEN_CATEGORIES)}", allow_blank=True)
    dv.add(f"F2:F{len(rows) + 1}")
    ws.add_data_validation(dv)
    for col, w in zip("ABCDEF", (14, 55, 55, 52, 52, 52), strict=True):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"

    out = processed / ANNOTATION_DIR / OUT_FILE
    wb.save(out)
    print(f"{len(rows)} tickets para revisar → {out}")


if __name__ == "__main__":
    main()
