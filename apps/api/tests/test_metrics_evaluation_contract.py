"""Metric evidence metadata contract tests."""

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pi_core.config import Settings
from pi_core.schemas import MetricasEvaluacion


def test_evaluation_response_preserves_evidence_context(api_client, monkeypatch, tmp_path):
    (tmp_path / "evaluation_results.json").write_text(
        json.dumps(
            {
                "f1_macro": 0.81,
                "recall_at_5": 0.42,
                "kappa": None,
                "muestra": 100,
                "tipo_evidencia": "proxy",
                "fuente": "tickets_eval.json",
                "metodo": "Recall@5 por coincidencia del ticket fuente",
                "dataset": "tickets_eval",
                "fecha_calculo": "2026-09-23T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "pi_api.routers.metrics.get_settings",
        lambda: Settings(data_processed_path=str(tmp_path)),
    )

    response = api_client.get("/metrics/evaluacion")

    assert response.status_code == 200
    assert response.json()["tipo_evidencia"] == "proxy"
    assert response.json()["fuente"] == "tickets_eval.json"
    assert response.json()["metodo"] == "Recall@5 por coincidencia del ticket fuente"
    assert response.json()["dataset"] == "tickets_eval"


def test_metric_schema_defaults_evidence_context_for_legacy_cache():
    data = MetricasEvaluacion(
        f1_macro=0.8,
        recall_at_5=0.85,
        fecha_calculo=datetime.now(UTC),
        muestra_tickets=200,
    ).model_dump()

    assert data["tipo_evidencia"] == "proxy"
    assert data["fuente"] is None
    assert data["metodo"] is None
    assert data["dataset"] is None


def test_golden_evaluation_response_identifies_dataset(api_client, monkeypatch, tmp_path):
    (tmp_path / "evaluation_results_golden.json").write_text(
        json.dumps(
            {
                "f1_macro": 0.82,
                "recall_at_5": 0.44,
                "kappa": 0.71,
                "muestra": 200,
                "tipo_evidencia": "proxy",
                "fuente": "golden_set_sample.json",
                "metodo": "Recall@5 por coincidencia del ticket fuente",
                "dataset": "golden_set",
                "fecha_calculo": "2026-09-23T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "pi_api.routers.metrics.get_settings",
        lambda: Settings(data_processed_path=str(tmp_path)),
    )

    response = api_client.get("/metrics/evaluacion-golden")

    assert response.status_code == 200
    assert response.json()["dataset"] == "golden_set"
    assert response.json()["kappa"] == 0.71

def test_legacy_cache_without_evidence_fields_is_not_reported_as_measured(
    api_client, monkeypatch, tmp_path
):
    (tmp_path / "evaluation_results.json").write_text(
        json.dumps({"f1_macro": 0.8, "recall_at_5": 0.85, "muestra": 200}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "pi_api.routers.metrics.get_settings",
        lambda: Settings(data_processed_path=str(tmp_path)),
    )

    body = api_client.get("/metrics/evaluacion").json()

    assert body["tipo_evidencia"] == "proxy"
    assert body["dataset"] == "tickets_eval"


@pytest.mark.parametrize(
    ("path", "dataset"),
    [("/metrics/evaluacion", "tickets_eval"), ("/metrics/evaluacion-golden", "golden_set")],
)
def test_missing_cache_reports_empty_proxy_not_measured_zeroes(
    api_client, monkeypatch, tmp_path, path, dataset
):
    monkeypatch.setattr(
        "pi_api.routers.metrics.get_settings",
        lambda: Settings(data_processed_path=str(tmp_path)),
    )

    body = api_client.get(path).json()

    assert body["muestra_tickets"] == 0
    assert body["tipo_evidencia"] == "proxy"
    assert body["dataset"] == dataset
    assert "Sin resultados" in body["metodo"]


def test_unknown_evidence_kind_is_rejected():
    with pytest.raises(ValidationError):
        MetricasEvaluacion(
            f1_macro=0.8,
            recall_at_5=0.8,
            fecha_calculo=datetime.now(UTC),
            muestra_tickets=1,
            tipo_evidencia="verificado",
        )
