"""HU15 — filtros del tablero del coordinador: rango de fechas, estado vacío y rango inválido."""

from datetime import datetime

import pytest

from pi_core.schemas import KedbArticulo


@pytest.fixture
def articulos(monkeypatch, store_aislado):
    monkeypatch.setattr("pi_api.routers.metrics.get_store", lambda: store_aislado)
    for idx, (dia, categoria) in enumerate(
        [("2026-09-01", "Impresoras"), ("2026-09-15", "Impresoras"), ("2026-10-01", "VPN")]
    ):
        store_aislado.create(
            KedbArticulo(
                articulo_id=f"KEDB-F{idx}",
                titulo=f"Artículo {idx}",
                categoria=categoria,
                sintoma="s",
                causa="c",
                solucion="x",
                fecha_generacion=datetime.fromisoformat(f"{dia}T10:00:00"),
            )
        )
    return store_aislado


def _total(res):
    return res.json()["cobertura_kedb"]["total_articulos"]


def test_sin_filtros_cuenta_todo(api_client, articulos):  # CA1
    res = api_client.get("/metrics/dashboard")
    assert res.status_code == 200
    assert _total(res) == 3
    assert res.json()["sin_datos"] is False


def test_filtra_por_rango_de_fechas_inclusivo(api_client, articulos):  # CA1
    res = api_client.get("/metrics/dashboard", params={"desde": "2026-09-15", "hasta": "2026-10-01"})
    assert _total(res) == 2
    assert res.json()["filtro_desde"] == "2026-09-15"


def test_filtra_por_categoria_y_fecha(api_client, articulos):  # CA1
    res = api_client.get(
        "/metrics/dashboard", params={"categoria": "Impresoras", "desde": "2026-09-10"}
    )
    assert _total(res) == 1


def test_filtro_sin_datos_marca_estado_vacio(api_client, articulos):  # CA2
    res = api_client.get("/metrics/dashboard", params={"desde": "2027-01-01"})
    assert res.status_code == 200
    assert _total(res) == 0
    assert res.json()["sin_datos"] is True


def test_rango_invalido_se_rechaza(api_client, articulos):  # CA3
    res = api_client.get("/metrics/dashboard", params={"desde": "2026-10-01", "hasta": "2026-09-01"})
    assert res.status_code == 422
    assert "inicio" in res.json()["detail"]
