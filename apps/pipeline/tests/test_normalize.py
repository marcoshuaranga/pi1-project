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


def test_normalize_category_cuenta_de_usuario_subcategorias():
    # "Cuenta de usuario" está contenido en las 3 subcategorías; Bloqueo/Vigencia no deben colapsar a Alta.
    assert normalize_category("Cuenta de usuario > Alta") == "Cuenta de usuario > Alta"
    assert normalize_category("Cuenta de usuario > Bloqueo") == "Cuenta de usuario > Bloqueo"
    assert normalize_category("Cuenta de usuario > Vigencia") == "Cuenta de usuario > Vigencia"
    assert normalize_category("Cuenta de usuario") == "Cuenta de usuario > Alta"
