"""Unit tests for the GLPI normalization helpers used by the batch ingest."""

from datetime import datetime

from pi_pipeline.ingest.normalize import assign_split, clean_html, normalize_category


def test_normalize_category_impresora():
    cat = normalize_category("Equipos Informáticos > Impresora Multifuncional")
    assert cat is not None
    assert "Impresora" in cat


def test_clean_html():
    assert clean_html("<p>Hola <b>mundo</b></p>") == "Hola mundo"


def test_assign_split_train():
    assert assign_split(datetime(2024, 6, 1)) == "train"


def test_assign_split_eval():
    assert assign_split(datetime(2025, 7, 1)) == "eval"


def test_assign_split_holdout():
    assert assign_split(datetime(2025, 10, 15)) == "holdout"
