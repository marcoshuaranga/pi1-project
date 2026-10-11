"""Sugerencia de categoría top-9 a partir de etiquetas gruesas de los expertos."""

import pytest

from pi_core.constants import FUERA_TOP9, TOP9_CATEGORIES
from pi_core.evaluation.golden_suggest import suggest_category

ALTA, BLOQUEO, VIGENCIA = TOP9_CATEGORIES[5], TOP9_CATEGORIES[6], TOP9_CATEGORIES[7]
NO_ACCEDE, HABILITACION = TOP9_CATEGORIES[3], TOP9_CATEGORIES[4]


@pytest.mark.parametrize(
    ("etiqueta", "titulo", "esperada"),
    [
        ("acceso a cuenta", "Cuenta de [NOMBRE] - ampliación de vigencia", VIGENCIA),
        ("acceso a cuenta", "Desbloquear cuenta de dominio", BLOQUEO),
        ("acceso a cuenta", "Cuenta de usuario - Habilitar cuenta de usuario", ALTA),
        ("vpn", "VPN Global Protect - no puede acceder", NO_ACCEDE),
        ("vpn", "Gestion de acceso al VPN y STD externo", HABILITACION),
        ("correo", "Buzón lleno", TOP9_CATEGORIES[8]),
        ("signnet", "No puede firmar documentos en el STD", TOP9_CATEGORIES[1]),
    ],
)
def test_suggest_category(etiqueta, titulo, esperada):
    cat, _, _ = suggest_category(etiqueta, titulo)
    assert cat == esperada


def test_vpn_ambiguo_no_adivina():
    cat, conf, _ = suggest_category("vpn", "Acceso al TELETRABAJO")
    assert cat is None or conf != "alta"


@pytest.mark.parametrize("etiqueta", ["monitor", "usb", "internet", "otros"])
def test_sin_equivalente_va_a_fuera_top9_y_no_a_cpu(etiqueta):
    cat, _, _ = suggest_category(etiqueta, "Movimiento de equipo de computo")
    assert cat == FUERA_TOP9
    assert cat != TOP9_CATEGORIES[2]
