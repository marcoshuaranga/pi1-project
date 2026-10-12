"""HU11 — POST /tickets/{id}/feedback: re-calificar actualiza, no duplica."""


def _utilidad(store):
    with store._conn() as conn:
        return conn.execute("SELECT articulo_id, util FROM ticket_feedback").fetchall()


def test_calificar_dos_veces_el_mismo_articulo_deja_una_sola_fila(api_client, store_aislado):
    url = "/tickets/T-HU11/feedback"

    assert api_client.post(url, json={"articulo_id": "KEDB-A", "util": True}).status_code == 200
    assert api_client.post(url, json={"articulo_id": "KEDB-A", "util": False}).status_code == 200

    filas = _utilidad(store_aislado)
    assert [(f["articulo_id"], f["util"]) for f in filas] == [("KEDB-A", 0)]
