"""HU11 — calificación de utilidad del artículo (upsert) sin romper HU12 (nueva solución)."""

import sqlite3

import pytest

from pi_core.config import Settings
from pi_core.storage.kedb_store.store import KedbStore


@pytest.fixture
def store(tmp_path):
    return KedbStore(
        Settings(kedb_db_path=str(tmp_path / "k.db"), kedb_docs_path=str(tmp_path / "a"))
    )


def _filas(store, **where):
    sql = "SELECT * FROM ticket_feedback"
    if where:
        sql += " WHERE " + " AND ".join(f"{k} = ?" for k in where)
    with store._conn() as conn:
        return conn.execute(sql, list(where.values())).fetchall()


def test_primera_calificacion_se_registra(store):  # CA1
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)

    filas = _filas(store)
    assert len(filas) == 1
    assert (filas[0]["ticket_id"], filas[0]["articulo_id"], filas[0]["util"]) == ("T-1", "KEDB-A", 1)


def test_recalificacion_actualiza_y_no_duplica(store):  # CA2
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)
    store.save_feedback("T-1", articulo_id="KEDB-A", util=False)
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)

    filas = _filas(store, ticket_id="T-1", articulo_id="KEDB-A")
    assert len(filas) == 1
    assert filas[0]["util"] == 1


def test_recalificacion_a_no_util_queda_en_cero(store):
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)
    store.save_feedback("T-1", articulo_id="KEDB-A", util=False)

    assert _filas(store)[0]["util"] == 0


def test_articulos_o_tickets_distintos_son_calificaciones_independientes(store):
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)
    store.save_feedback("T-1", articulo_id="KEDB-B", util=False)
    store.save_feedback("T-2", articulo_id="KEDB-A", util=False)

    assert len(_filas(store)) == 3


def test_nueva_solucion_no_se_ve_afectada_por_el_upsert(store):  # HU12 sigue intacta
    store.save_feedback("T-1", nueva_solucion="Reiniciar el spooler de impresión")
    store.save_feedback("T-1", nueva_solucion="Reiniciar el spooler de impresión")
    store.save_feedback("T-1", articulo_id="KEDB-A", util=True)

    assert len(_filas(store, ticket_id="T-1")) == 3
    assert len([f for f in _filas(store) if f["nueva_solucion"]]) == 2


def test_migracion_deduplica_bases_previas_y_conserva_la_ultima(tmp_path):
    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE ticket_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL,"
        " articulo_id TEXT, util INTEGER, nueva_solucion TEXT, created_at TEXT NOT NULL)"
    )
    for util in (1, 0):
        conn.execute(
            "INSERT INTO ticket_feedback (ticket_id, articulo_id, util, created_at) VALUES ('T-1','KEDB-A',?,'x')",
            (util,),
        )
    conn.commit()
    conn.close()

    store = KedbStore(Settings(kedb_db_path=str(db), kedb_docs_path=str(tmp_path / "a")))

    filas = _filas(store)
    assert len(filas) == 1
    assert filas[0]["util"] == 0
