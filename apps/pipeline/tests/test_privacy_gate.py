"""Privacy gate tests for the historical ingestion boundary."""

import pandas as pd
import pytest

from pi_pipeline.ingest.pipeline import IngestionPipeline


class LeakingAnonymizer:
    def anonymize(self, text: str):
        from pi_core.anonymize.anonymizer import AnonymizationResult

        return AnonymizationResult(text=f"{text} correo leak@example.com")


class CleanAnonymizer:
    def anonymize(self, text: str):
        from pi_core.anonymize.anonymizer import AnonymizationResult

        return AnonymizationResult(text=f"{text} [CORREO]")


def _pipeline(monkeypatch, tmp_path, anonymizer):
    pipeline = object.__new__(IngestionPipeline)
    pipeline.anonymizer = anonymizer
    pipeline.output_dir = tmp_path
    monkeypatch.setattr(
        "pi_pipeline.ingest.pipeline.pd.read_parquet",
        lambda _path: pd.DataFrame([{"_titulo": "VPN", "_solucion": "Revisar acceso"}]),
    )
    return pipeline


def test_anonymize_blocks_residual_pii_before_writing(monkeypatch, tmp_path):
    pipeline = _pipeline(monkeypatch, tmp_path, LeakingAnonymizer())

    with pytest.raises(ValueError, match="PII residual"):
        pipeline.run_anonymize()

    assert not (tmp_path / "sample_anonymized.parquet").exists()


def test_anonymize_writes_only_after_privacy_gate(monkeypatch, tmp_path):
    pipeline = _pipeline(monkeypatch, tmp_path, CleanAnonymizer())

    result = pipeline.run_anonymize()

    assert result["_titulo_anon"].tolist() == ["VPN [CORREO]"]
    assert (tmp_path / "sample_anonymized.parquet").exists()


def test_full_pipeline_orders_anonymize_before_ingest_and_embeddings(tmp_path):
    pipeline = object.__new__(IngestionPipeline)
    pipeline.order = []
    pipeline.run_extract_sample = lambda _raw: pipeline.order.append("extract")
    pipeline.run_anonymize = lambda: pipeline.order.append("anonymize")
    pipeline.run_ingest = lambda: pipeline.order.append("ingest") or ["ticket"]
    pipeline.run_embeddings = lambda tickets: pipeline.order.append("embed") or 1

    result = pipeline.run_full("raw.xlsx")

    assert pipeline.order == ["extract", "anonymize", "ingest", "embed"]
    assert result == {"tickets": 1, "embedded": 1}

def test_ingest_blocks_stale_parquet_with_residual_pii(monkeypatch, tmp_path):
    """A parquet written before the gate existed must not reach splits or embeddings."""
    pipeline = object.__new__(IngestionPipeline)
    pipeline.output_dir = tmp_path
    monkeypatch.setattr(
        "pi_pipeline.ingest.pipeline.pd.read_parquet",
        lambda _path: pd.DataFrame(
            [
                {
                    "_ticket_id": "1",
                    "_titulo_anon": "VPN",
                    "_solucion_anon": "Escribir a soporte@empresa.pe para reiniciar",
                }
            ]
        ),
    )

    with pytest.raises(ValueError, match="PII residual"):
        pipeline.run_ingest()

    assert not list(tmp_path.glob("tickets_*.json"))
