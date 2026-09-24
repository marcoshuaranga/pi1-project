"""Anonymizer smoke tests (regex PII scrubbing; no spaCy model required)."""

from pi_core.anonymize.anonymizer import Anonymizer


def test_anonymizer_email():
    anon = Anonymizer()
    result = anon.anonymize("Contactar a juan.perez@mtc.gob.pe por el ticket")
    assert "[CORREO]" in result.text
    assert "juan.perez" not in result.text


def test_anonymizer_dni():
    anon = Anonymizer()
    result = anon.anonymize("DNI del solicitante: 12345678")
    assert "[DNI]" in result.text
