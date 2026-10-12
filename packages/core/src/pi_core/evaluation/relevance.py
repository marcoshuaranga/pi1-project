"""C9 — Juicio experto de relevancia de las soluciones sugeridas (Recall@5 "solución útil").

Complementa el Recall@5 por ID y el semántico por categoría (proxies, ver metrics.py): dos expertos
juzgan, a ciegas y por separado, si cada una de las 5 soluciones que recupera el sistema para un
ticket del golden set serviría para resolverlo. No ven el ranking, el score ni la categoría de lo
recuperado, y el orden de las filas se baraja distinto para cada experto.

Flujo:
    1. `build_relevance_pool()` (necesita Chroma) → relevance_pool.json + 2 planillas .xlsx
    2. Los expertos marcan "Sí" / "No" en la columna "util"
    3. `score_relevance()` → relevance_results.json (Recall@5 / Precisión@5 experto, acuerdo)
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from sklearn.metrics import cohen_kappa_score

from pi_core.constants import FUERA_TOP9
from pi_core.evaluation.golden_set import ANNOTATION_DIR, GOLDEN_FILE

POOL_FILE = "relevance_pool.json"
RESULTS_FILE = "relevance_results.json"
EXPERT1_FILE = "relevancia_experto1.xlsx"
EXPERT2_FILE = "relevancia_experto2.xlsx"

_UTIL_HEADER = "util (Sí / No)"
_SHEET = "relevancia"
_OPCIONES = ("Sí", "No")
_TEXT_MAX = 1500


class _Retriever(Protocol):
    def retrieve(
        self, texto: str, categoria: str | None = None, excluir_ids: set[str] | None = None
    ) -> list[Any]: ...


def build_relevance_pool(
    processed: Path, rag: _Retriever, n: int = 30, k: int = 5, seed: int = 42
) -> list[dict[str, Any]]:
    """Recupera las k soluciones por ticket (sin el propio ticket) y escribe pool + planillas."""
    golden = json.loads((processed / GOLDEN_FILE).read_text(encoding="utf-8"))
    evals = {t["ticket_id"]: t for t in json.loads((processed / "tickets_eval.json").read_text(encoding="utf-8"))}

    elegibles = [e for e in golden if e["categoria_gold"] and e["categoria_gold"] != FUERA_TOP9]
    # Primero los de doble anotación: los mismos que ya conocen los dos expertos.
    elegibles.sort(key=lambda e: (not e["doble_anotacion"], e["ticket_id"]))

    items: list[dict[str, Any]] = []
    for e in elegibles:
        if len(items) >= n:
            break
        t = evals[e["ticket_id"]]
        try:
            candidatas = rag.retrieve(t["titulo_anon"], excluir_ids={e["ticket_id"]})[:k]
        except Exception:
            continue
        if len(candidatas) < k:
            continue
        items.append(
            {
                "ticket_id": e["ticket_id"],
                "titulo": t["titulo_anon"],
                "solucion_real": (t.get("solucion_anon") or "")[:_TEXT_MAX],
                "candidatas": [
                    {
                        "item_id": f"{e['ticket_id']}#{rank}",
                        "rank": rank,
                        "id": s.articulo_o_ticket_id,
                        "tipo": s.tipo,
                        "titulo": s.titulo or "",
                        "solucion": (s.solucion or "")[:_TEXT_MAX],
                        "score": s.score,
                    }
                    for rank, s in enumerate(candidatas, start=1)
                ],
            }
        )

    (processed / POOL_FILE).write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    ann_dir = processed / ANNOTATION_DIR
    ann_dir.mkdir(parents=True, exist_ok=True)
    _workbook(items, shuffle_seed=seed).save(ann_dir / EXPERT1_FILE)
    _workbook(items, shuffle_seed=seed + 1).save(ann_dir / EXPERT2_FILE)
    return items


def _workbook(items: list[dict[str, Any]], shuffle_seed: int) -> Workbook:
    filas = [
        (c["item_id"], it["titulo"], it["solucion_real"], c["titulo"], c["solucion"])
        for it in items
        for c in it["candidatas"]
    ]
    random.Random(shuffle_seed).shuffle(filas)

    wb = Workbook()
    ws = wb.active
    ws.title = _SHEET
    ws.append(
        ["item_id", "ticket (título)", "resolución real del ticket (referencia)",
         "solución sugerida: título", "solución sugerida: texto", _UTIL_HEADER]
    )
    for f in filas:
        ws.append([*f, None])

    opciones = wb.create_sheet("opciones")
    for o in _OPCIONES:
        opciones.append([o])
    opciones.sheet_state = "hidden"
    dv = DataValidation(type="list", formula1=f"=opciones!$A$1:$A${len(_OPCIONES)}", allow_blank=True)
    dv.error = "Responde Sí o No"
    dv.add(f"F2:F{len(filas) + 1}")
    ws.add_data_validation(dv)
    for col, w in zip("ABCDEF", (14, 45, 55, 40, 70, 16), strict=True):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    return wb


def _read_judgments(path: Path) -> dict[str, bool]:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró la planilla llena: {path}")
    ws = load_workbook(path, data_only=True)[_SHEET]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    try:
        id_col, util_col = header.index("item_id"), header.index(_UTIL_HEADER)
    except ValueError as exc:
        raise ValueError(f"{path}: encabezados inesperados {header}") from exc

    out: dict[str, bool] = {}
    for row in rows:
        if row[id_col] is None:
            continue
        valor = str(row[util_col]).strip().lower() if row[util_col] is not None else ""
        if valor in ("sí", "si"):
            out[str(row[id_col])] = True
        elif valor == "no":
            out[str(row[id_col])] = False
        else:
            raise ValueError(f"{path}: respuesta inválida '{row[util_col]}' en {row[id_col]} (usa Sí o No)")
    return out


def _metricas(items: list[dict[str, Any]], util: dict[str, bool]) -> dict[str, float]:
    hits = sum(any(util[c["item_id"]] for c in it["candidatas"]) for it in items)
    positivos = sum(util[c["item_id"]] for it in items for c in it["candidatas"])
    total = sum(len(it["candidatas"]) for it in items)
    return {"recall_at_5": round(hits / len(items), 4), "precision_at_5": round(positivos / total, 4)}


def score_relevance(processed: Path) -> dict[str, Any]:
    """Lee las 2 planillas llenas y calcula Recall@5 / Precisión@5 por experto y conservador."""
    pool_path = processed / POOL_FILE
    if not pool_path.exists():
        raise FileNotFoundError(f"No se encontró {pool_path}; corre `sample` primero")
    items = json.loads(pool_path.read_text(encoding="utf-8"))
    esperados = {c["item_id"] for it in items for c in it["candidatas"]}

    ann = processed / ANNOTATION_DIR
    j1, j2 = _read_judgments(ann / EXPERT1_FILE), _read_judgments(ann / EXPERT2_FILE)
    for nombre, j in (("Experto 1", j1), ("Experto 2", j2)):
        faltan = sorted(esperados - j.keys())
        if faltan:
            raise ValueError(f"{nombre}: faltan {len(faltan)} juicios sin responder: {faltan[:5]}")

    ids = sorted(esperados)
    kappa = cohen_kappa_score([j1[i] for i in ids], [j2[i] for i in ids]) if len(set(j1.values()) | set(j2.values())) > 1 else None
    ambos = {i: j1[i] and j2[i] for i in ids}  # criterio conservador: útil solo si ambos dicen Sí
    cualquiera = {i: j1[i] or j2[i] for i in ids}

    result = {
        "n_tickets": len(items),
        "n_juicios": len(ids),
        "recall_at_5_experto": _metricas(items, ambos)["recall_at_5"],
        "precision_at_5_experto": _metricas(items, ambos)["precision_at_5"],
        "recall_at_5_experto_laxo": _metricas(items, cualquiera)["recall_at_5"],
        "por_experto": {"experto1": _metricas(items, j1), "experto2": _metricas(items, j2)},
        "kappa_relevancia": round(kappa, 4) if kappa is not None else None,
        "acuerdo_relevancia": round(sum(j1[i] == j2[i] for i in ids) / len(ids), 4),
        "criterio": "util = ambos expertos responden Sí (recall_at_5_experto_laxo: al menos uno)",
        "fecha_calculo": datetime.now(UTC).isoformat(),
    }
    (processed / RESULTS_FILE).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
