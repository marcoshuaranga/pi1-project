"""Unit tests for resolution enrichment (demo-quality indexed text)."""

from pi_core.enrich.resolutions import enrich_resolution, is_thin_resolution
from pi_core.fixtures.kyocera_demo import DEMO_ARTICLE_TEMPLATE, build_demo_articulo


def test_thin_generic_kyocera_stub():
    stub = "Se configuró impresora predeterminada y se validó con hoja de prueba."
    assert is_thin_resolution(stub)


def test_enrich_kyocera_produces_long_runbook():
    result = enrich_resolution(
        titulo="Configuración de impresora Kyocera 7003",
        solucion="Se configuró impresora predeterminada.",
        categoria="Impresora Multifuncional",
        ticket_id="96044",
    )
    assert result.enriched is True
    assert result.domain == "kyocera"
    assert len(result.solucion) > 400
    assert "Kyocera" in result.solucion or "7003" in result.solucion
    assert "prueba" in result.solucion.lower()
    assert "driver" in result.solucion.lower() or "TCP/IP" in result.solucion


def test_enrich_kyocera_variants_differ_by_ticket_id():
    a = enrich_resolution(
        titulo="Configuración de impresora Kyocera 7003",
        solucion="ok",
        ticket_id="96044",
    )
    b = enrich_resolution(
        titulo="Configuración de impresora Kyocera 7003",
        solucion="ok",
        ticket_id="95984",
    )
    assert a.solucion != b.solucion


def test_keep_already_rich_non_kyocera():
    rich = (
        "1. Revisar logs del servicio X en el servidor de sede.\n"
        "2. Reiniciar el servicio y validar healthcheck HTTP 200.\n"
        "3. Verificar balanceador y certificados TLS vigentes.\n"
        "4. Confirmar con el usuario acceso al portal misional.\n"
        "5. Documentar versión desplegada y rollback plan.\n"
        "Resultado: servicio estabilizado tras reinicio controlado."
    )
    result = enrich_resolution(
        titulo="Portal lento en sede",
        solucion=rich,
        ticket_id="1",
    )
    assert result.enriched is False
    assert result.solucion == rich.strip()


def test_demo_article_template_is_operational():
    sol = DEMO_ARTICLE_TEMPLATE["solucion"]
    assert len(sol) > 400
    assert "TCP/IP" in sol or "driver" in sol.lower()
    art = build_demo_articulo(ticket_ids=["1", "2"], articulo_id="KEDB-ENRICH")
    assert len(art.solucion) > 400
