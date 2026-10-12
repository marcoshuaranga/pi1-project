"""C9 — Evaluation framework."""

import json
import logging
import random
from datetime import UTC, datetime
from pathlib import Path

from sklearn.metrics import f1_score

from pi_core.agents.classifier.agent import ClassifierAgent
from pi_core.agents.rag.agent import RAGAgent
from pi_core.config import get_settings
from pi_core.constants import FUERA_TOP9

logger = logging.getLogger(__name__)


class EvaluationFramework:
    def __init__(self):
        self.settings = get_settings()
        self.classifier = ClassifierAgent()
        self.rag = RAGAgent()
        self.processed = Path(self.settings.data_processed_path)

    def run_evaluation(self, sample_size: int = 100) -> dict:
        eval_path = self.processed / "tickets_eval.json"
        if not eval_path.exists():
            return {
                "f1_macro": 0.0,
                "recall_at_5": 0.0,
                "muestra": 0,
                "kappa": None,
                "tipo_evidencia": "proxy",
                "fuente": "tickets_eval.json",
                "metodo": "Sin datos de evaluación disponibles",
                "dataset": "tickets_eval",
                "fecha_calculo": datetime.now(UTC).isoformat(),
            }

        data = json.loads(eval_path.read_text(encoding="utf-8"))
        random.seed(self.settings.random_seed)
        sample = random.sample(data, min(sample_size, len(data)))

        y_true = []
        y_pred = []
        recall_hits = 0

        for ticket in sample:
            texto = ticket.get("titulo_anon", "")
            true_cat = ticket.get("categoria_top9", "")
            if not texto or not true_cat:
                continue
            result = self.classifier.classify(texto)
            y_true.append(true_cat)
            y_pred.append(result["categoria"])

            soluciones = self.rag.retrieve(texto, true_cat)
            ticket_id = ticket.get("ticket_id", "")
            found = any(s.articulo_o_ticket_id == ticket_id for s in soluciones)
            if found:
                recall_hits += 1

        n = len(y_true)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0) if n else 0.0
        recall = recall_hits / n if n else 0.0

        result = {
            "f1_macro": round(f1, 4),
            "recall_at_5": round(recall, 4),
            "muestra": n,
            "kappa": None,
            "tipo_evidencia": "proxy",
            "fuente": "tickets_eval.json",
            "metodo": "Recall@5 por coincidencia del ticket fuente",
            "dataset": "tickets_eval",
            "fecha_calculo": datetime.now(UTC).isoformat(),
        }
        out = self.processed / "evaluation_results.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    def _retrieve_con_y_sin_propio(self, texto: str, ticket_id: str, k: int = 5):
        """Top-k tal cual (incluye al propio ticket) y top-k sin él, con una sola consulta."""
        previo = self.rag.top_k
        self.rag.top_k = k + 1
        try:
            todas = self.rag.retrieve(texto)
        finally:
            self.rag.top_k = previo
        sin_propio = [s for s in todas if s.articulo_o_ticket_id != ticket_id][:k]
        return todas[:k], sin_propio

    def run_golden_evaluation(self) -> dict:
        """C9 sobre golden_set_sample.json (200 tickets, doble etiquetado) en vez de
        la muestra aleatoria de tickets_eval.json — ver packages/core/src/pi_core/evaluation/golden_set.py.
        """
        golden_path = self.processed / "golden_set_sample.json"
        if not golden_path.exists():
            return {
                "f1_macro": 0.0,
                "recall_at_5": 0.0,
                "muestra": 0,
                "kappa": None,
                "tipo_evidencia": "proxy",
                "fuente": "golden_set_sample.json",
                "metodo": "Sin datos de evaluación disponibles",
                "dataset": "golden_set",
                "fecha_calculo": datetime.now(UTC).isoformat(),
            }

        golden = json.loads(golden_path.read_text(encoding="utf-8"))

        eval_path = self.processed / "tickets_eval.json"
        tickets_by_id = {}
        if eval_path.exists():
            for t in json.loads(eval_path.read_text(encoding="utf-8")):
                tickets_by_id[t["ticket_id"]] = t

        y_true = []
        y_pred = []
        recall_hits = 0
        recall_cat_hits = 0
        precision_cat_sum = 0.0
        fuera_top9 = 0
        errores_recuperacion = 0

        for entry in golden:
            gold_cat = entry.get("categoria_gold")
            ticket = tickets_by_id.get(entry.get("ticket_id"))
            if not gold_cat or not ticket:
                continue
            if gold_cat == FUERA_TOP9:
                fuera_top9 += 1
                continue
            texto = ticket.get("titulo_anon", "")
            if not texto:
                continue

            # Chroma (HNSW) devuelve error para algunas consultas; se omiten y se reportan
            # en vez de abortar toda la evaluación o mezclar un método de respaldo.
            try:
                result = self.classifier.classify(texto)
                soluciones, sin_propio = self._retrieve_con_y_sin_propio(texto, entry["ticket_id"])
            except Exception:
                logger.warning("Recuperación falló para ticket %s; se omite", entry["ticket_id"], exc_info=True)
                errores_recuperacion += 1
                continue
            y_true.append(gold_cat)
            y_pred.append(result["categoria"])

            found = any(s.articulo_o_ticket_id == entry["ticket_id"] for s in soluciones)
            if found:
                recall_hits += 1

            # Semántico (proxy): lo recuperado, sin contar el propio ticket, es de la misma categoría.
            mismas = [s for s in sin_propio if s.categoria == gold_cat]
            if mismas:
                recall_cat_hits += 1
            precision_cat_sum += len(mismas) / len(sin_propio) if sin_propio else 0.0

        n = len(y_true)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0) if n else 0.0
        recall = recall_hits / n if n else 0.0
        recall_cat = recall_cat_hits / n if n else 0.0
        precision_cat = precision_cat_sum / n if n else 0.0

        kappa_path = self.processed / "golden_set_kappa.json"
        kappa = json.loads(kappa_path.read_text(encoding="utf-8")).get("kappa") if kappa_path.exists() else None

        result = {
            "f1_macro": round(f1, 4),
            "recall_at_5": round(recall, 4),
            "recall_at_5_categoria": round(recall_cat, 4),
            "precision_at_5_categoria": round(precision_cat, 4),
            "muestra": n,
            "fuera_top9_excluidos": fuera_top9,
            "errores_recuperacion": errores_recuperacion,
            "kappa": kappa,
            "tipo_evidencia": "proxy",
            "fuente": "golden_set_sample.json",
            "metodo": (
                "Recall@5 por coincidencia del ticket fuente; Recall@5 semántico por categoría "
                "(sin contar el propio ticket); Kappa interanotador"
            ),
            "dataset": "golden_set",
            "fecha_calculo": datetime.now(UTC).isoformat(),
        }
        out = self.processed / "evaluation_results_golden.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
