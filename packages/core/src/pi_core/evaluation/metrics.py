"""C9 — Evaluation framework."""

import json
import random
from datetime import UTC, datetime
from pathlib import Path

from sklearn.metrics import f1_score

from pi_core.agents.classifier.agent import ClassifierAgent
from pi_core.agents.rag.agent import RAGAgent
from pi_core.config import get_settings


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
            "fecha_calculo": datetime.now(UTC).isoformat(),
        }
        out = self.processed / "evaluation_results.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
