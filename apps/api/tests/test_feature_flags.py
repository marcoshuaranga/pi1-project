"""Feature flags funcionales (ADR-0011): endpoint de config y guardias 404 con el flag apagado."""

import pytest

from pi_core.feature_flags import FeatureFlags, flag_enabled, get_flags

FLAGS = (
    "e02_busqueda_kedb",
    "e03_generacion_kedb",
    "e03_ciclo_vida",
    "e04_nueva_solucion",
    "e05_tablero_coordinador",
)


@pytest.fixture
def apagar(monkeypatch):
    """Apaga flags por entorno (como en producción) y limpia la caché al terminar."""

    def _apagar(*nombres):
        for nombre in nombres:
            monkeypatch.setenv(f"FEATURE_{nombre.upper()}", "false")
        get_flags.cache_clear()

    yield _apagar
    monkeypatch.undo()
    get_flags.cache_clear()


def test_todos_los_flags_encendidos_por_defecto(api_client):
    res = api_client.get("/config/features")
    assert res.status_code == 200
    assert res.json() == dict.fromkeys(FLAGS, True)


def test_nombre_de_flag_desconocido_falla_rapido():
    with pytest.raises(KeyError):
        flag_enabled("e99_inexistente")
    assert set(FeatureFlags.model_fields) == set(FLAGS)


def test_config_refleja_flags_apagados(api_client, apagar):
    apagar("e05_tablero_coordinador")
    flags = api_client.get("/config/features").json()
    assert flags["e05_tablero_coordinador"] is False
    assert flags["e02_busqueda_kedb"] is True


@pytest.mark.parametrize(
    ("flag", "metodo", "url"),
    [
        ("e02_busqueda_kedb", "get", "/kedb/buscar?q=impresora"),
        ("e03_generacion_kedb", "post", "/kedb/generate"),
        ("e03_ciclo_vida", "patch", "/kedb/articulos/KEDB-X/ciclo-vida"),
        ("e04_nueva_solucion", "post", "/tickets/T-X/feedback"),
        ("e05_tablero_coordinador", "get", "/metrics/dashboard"),
    ],
)
def test_flag_apagado_responde_404_feature_deshabilitada(api_client, apagar, flag, metodo, url):
    apagar(flag)
    kwargs = {"json": {"nueva_solucion": "x" * 40}} if metodo == "post" and "feedback" in url else {}
    res = getattr(api_client, metodo)(url, **kwargs)
    assert res.status_code == 404
    assert res.json()["detail"] == "feature_deshabilitada"


def test_resolucion_deprecada_tambien_respeta_hu12(api_client, apagar):
    apagar("e04_nueva_solucion")
    res = api_client.post("/tickets/T-X/resolucion", json={"solucion": "x" * 40})
    assert res.status_code == 404
    assert res.json()["detail"] == "feature_deshabilitada"


def test_utilidad_hu11_sigue_activa_con_hu12_apagada(api_client, store_aislado, apagar):
    apagar("e04_nueva_solucion")
    res = api_client.post("/tickets/T-X/feedback", json={"articulo_id": "KEDB-1", "util": True})
    assert res.status_code == 200


def test_validacion_hu10_sigue_activa_con_ciclo_vida_apagado(api_client, apagar):
    apagar("e03_ciclo_vida")
    res = api_client.patch("/kedb/articulos/NO-EXISTE", json={"estado": "validado"})
    assert res.status_code == 404
    assert res.json()["detail"] != "feature_deshabilitada"
