"""PRD §7.1 DoD: PII residual = 0 sobre una muestra de tickets.

The real 500-ticket GLPI sample is raw PII and is deliberately never
committed to this repo (see README: "nunca commitear el xlsx crudo"), so
this test builds a synthetic corpus of the same shape and scale instead. It
is a proxy for the PRD's acceptance criterion, not a replacement for running
the real anonymization pipeline against the actual historical export.
"""

import random
import re

import pytest

from app.pipeline.anonymize.anonymizer import PII_PATTERNS, Anonymizer

SAMPLE_SIZE = 500

_NOMBRES = [
    "Juan Pérez", "María Gonzales", "Carlos Quispe", "Ana Torres", "Luis Mamani",
    "Rosa Huamán", "Pedro Vargas", "Carmen Flores", "Jorge Rojas", "Lucía Cárdenas",
    "Miguel Salazar", "Patricia Ramos", "Fernando Chávez", "Elena Paredes", "Diego Ríos",
]
_DOMINIOS = ["mtc.gob.pe", "gmail.com", "hotmail.com", "outlook.com"]
_CUERPOS = [
    "no puede acceder al sistema desde su equipo",
    "reporta que la impresora {kw} no responde",
    "solicita reinicio de su cuenta de VPN GlobalProtect",
    "necesita configuración de correo en su laptop",
    "indica que el buzón está lleno y no recibe correos",
]
_KEYWORDS = ["Kyocera", "TASKalfa", "multifuncional"]


def _random_dni(rng: random.Random) -> str:
    return str(rng.randint(10_000_000, 99_999_999))


def _random_ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def _random_phone(rng: random.Random) -> str:
    return f"9{rng.randint(10, 99)}{rng.randint(100, 999)}{rng.randint(1000, 9999)}"


def _build_corpus(n: int) -> list[str]:
    rng = random.Random(42)
    tickets = []
    for i in range(n):
        nombre = rng.choice(_NOMBRES)
        email_local = nombre.lower().replace(" ", ".")
        email = f"{email_local}@{rng.choice(_DOMINIOS)}"
        dni = _random_dni(rng)
        ip = _random_ip(rng)
        telefono = _random_phone(rng)
        cuerpo = rng.choice(_CUERPOS).format(kw=rng.choice(_KEYWORDS))
        texto = (
            f"Ticket {i}: Buen día, soy {nombre}, DNI {dni}, correo {email}. "
            f"Mi equipo con IP {ip} {cuerpo}. Pueden llamarme al {telefono}. "
            f"Coordinado con MTC / OITSI. Gracias."
        )
        tickets.append((texto, nombre))
    return tickets


@pytest.fixture(scope="module")
def anonymizer() -> Anonymizer:
    return Anonymizer()


@pytest.fixture(scope="module")
def corpus() -> list[tuple[str, str]]:
    return _build_corpus(SAMPLE_SIZE)


def test_regex_pii_fully_scrubbed_on_500_ticket_sample(anonymizer, corpus):
    """Emails, DNIs, IPs, phone numbers — always testable, no spaCy model needed."""
    residual: list[tuple[int, str, str]] = []
    for i, (texto, _nombre) in enumerate(corpus):
        result = anonymizer.anonymize(texto)
        for pattern, _token in PII_PATTERNS:
            for match in re.finditer(pattern, result.text):
                residual.append((i, pattern, match.group()))

    assert residual == [], f"PII residual encontrado en {len(residual)} coincidencias (criterio PRD: 0)"


def test_ner_names_scrubbed_on_500_ticket_sample(anonymizer, corpus):
    """Person names via spaCy NER — skips if es_core_news_lg isn't installed."""
    if anonymizer.nlp is None:
        pytest.skip(
            "spaCy es_core_news_lg no está instalado en este entorno "
            "(el Dockerfile lo instala; ver ADR-0008). Sin el modelo, la "
            "anonimización de nombres propios no se puede verificar aquí."
        )

    leaked: list[tuple[int, str]] = []
    for i, (texto, nombre) in enumerate(corpus):
        result = anonymizer.anonymize(texto)
        if nombre in result.text:
            leaked.append((i, nombre))

    assert leaked == [], f"Nombres sin anonimizar en {len(leaked)}/{SAMPLE_SIZE} tickets (criterio PRD: 0)"


def test_mtc_public_entities_are_not_anonymized(anonymizer, corpus):
    """The MTC-entity exclusion dictionary shouldn't over-scrub public institution names."""
    for texto, _nombre in corpus[:50]:
        result = anonymizer.anonymize(texto)
        assert "MTC" in result.text
        assert "OITSI" in result.text
