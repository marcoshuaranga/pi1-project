"""Evidence semantics for target, measured, and proxy evaluation values."""

from datetime import UTC, datetime

from pi_core.schemas import MetricasEvaluacion


def test_evaluation_result_exposes_evidence_context():
    result = MetricasEvaluacion(
        f1_macro=0.82,
        recall_at_5=0.44,
        kappa=0.71,
        fecha_calculo=datetime.now(UTC),
        muestra_tickets=200,
        tipo_evidencia="proxy",
        fuente="golden_set_sample.json",
        metodo="Recall@5 por coincidencia del ticket fuente",
        dataset="golden_set",
    )

    assert result.tipo_evidencia == "proxy"
    assert result.fuente == "golden_set_sample.json"
    assert result.dataset == "golden_set"