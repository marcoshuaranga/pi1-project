"""C9 golden set (opción B): muestreo estratificado + doble anotación ciega + Kappa.

Cubre solo la lógica pura de pi_core.evaluation.golden_set (sin ClassifierAgent/RAGAgent
en vivo) — ver EvaluationFramework.run_golden_evaluation para el consumo real.
"""

import json

import pytest
from openpyxl import load_workbook

from pi_core.constants import TOP9_CATEGORIES
from pi_core.evaluation.golden_set import (
    _CATEGORIA_HEADER,
    ANNOTATION_DIR,
    EXPERT1_FILE,
    EXPERT2_FILE,
    _read_annotations,
    _stratified_quota,
    build_pool,
    sample_golden_pool,
    score_and_merge,
)

CAT_A, CAT_B, CAT_C = TOP9_CATEGORIES[0], TOP9_CATEGORIES[1], TOP9_CATEGORIES[2]


def _write_tickets_eval(processed, counts: dict[str, int]):
    tickets = []
    i = 0
    for cat, n in counts.items():
        for _ in range(n):
            tickets.append(
                {
                    "ticket_id": f"T{i}",
                    "categoria_top9": cat,
                    "titulo_anon": f"ticket {i} sobre {cat}",
                    "solucion_anon": "solución anonimizada",
                }
            )
            i += 1
    (processed / "tickets_eval.json").write_text(json.dumps(tickets), encoding="utf-8")
    return tickets


def test_stratified_quota_sums_to_n_and_respects_capacity():
    counts = {CAT_A: 50, CAT_B: 30, CAT_C: 5}
    quota = _stratified_quota(counts, 20)

    assert sum(quota.values()) == 20
    for cat, q in quota.items():
        assert q <= counts[cat]


def test_stratified_quota_returns_all_when_pool_smaller_than_n():
    counts = {CAT_A: 3, CAT_B: 2}
    quota = _stratified_quota(counts, 20)
    assert quota == counts


def test_sample_golden_pool_is_stratified_and_deterministic(tmp_path):
    _write_tickets_eval(tmp_path, {CAT_A: 60, CAT_B: 30, CAT_C: 10})

    pool1 = sample_golden_pool(tmp_path, seed=42, n=20, n_kappa=5)
    pool2 = sample_golden_pool(tmp_path, seed=42, n=20, n_kappa=5)

    assert len(pool1) == 20
    assert [e["ticket_id"] for e in pool1] == [e["ticket_id"] for e in pool2]
    assert sum(e["doble_anotacion"] for e in pool1) == 5
    # Categoría original nunca debe filtrarse a lo que ven los expertos.
    assert all("categoria_top9" in e for e in pool1)

    cats_present = {e["categoria_top9"] for e in pool1}
    assert cats_present == {CAT_A, CAT_B, CAT_C}


def test_sample_golden_pool_missing_eval_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        sample_golden_pool(tmp_path, seed=1, n=10, n_kappa=2)


def test_build_pool_exports_blind_workbooks(tmp_path):
    _write_tickets_eval(tmp_path, {CAT_A: 20, CAT_B: 20})

    entries = build_pool(tmp_path, seed=7, n=10, n_kappa=3)
    assert (tmp_path / "golden_pool.json").exists()

    wb1_path = tmp_path / ANNOTATION_DIR / EXPERT1_FILE
    wb2_path = tmp_path / ANNOTATION_DIR / EXPERT2_FILE
    assert wb1_path.exists()
    assert wb2_path.exists()

    wb1 = load_workbook(wb1_path)
    ws1 = wb1["anotacion"]
    header = [c.value for c in next(ws1.iter_rows(min_row=1, max_row=1))]
    assert header == ["ticket_id", "titulo_anon", _CATEGORIA_HEADER]
    # 10 filas de datos + encabezado, sin exponer categoria_top9 al experto.
    assert ws1.max_row == 11
    assert "categoria_top9" not in header

    wb2 = load_workbook(wb2_path)
    assert wb2["anotacion"].max_row == 4  # 3 tickets de doble anotación + encabezado

    kappa_ids_wb2 = {row[0] for row in wb2["anotacion"].iter_rows(min_row=2, values_only=True)}
    kappa_ids_pool = {e["ticket_id"] for e in entries if e["doble_anotacion"]}
    assert kappa_ids_wb2 == kappa_ids_pool


def _fill_workbook(path, answers: dict[str, str]):
    wb = load_workbook(path)
    ws = wb["anotacion"]
    for row in ws.iter_rows(min_row=2):
        ticket_id = row[0].value
        if ticket_id in answers:
            row[2].value = answers[ticket_id]
    wb.save(path)


def test_score_and_merge_computes_kappa_and_flags_disagreement(tmp_path):
    _write_tickets_eval(tmp_path, {CAT_A: 20, CAT_B: 20})
    entries = build_pool(tmp_path, seed=3, n=10, n_kappa=4)
    kappa_ids = [e["ticket_id"] for e in entries if e["doble_anotacion"]]
    assert len(kappa_ids) == 4

    # Experto 1 etiqueta todo con la categoría real (simulando un etiquetador perfecto).
    truth = {e["ticket_id"]: e["categoria_top9"] for e in entries}
    _fill_workbook(tmp_path / ANNOTATION_DIR / EXPERT1_FILE, truth)

    # Experto 2 solo etiqueta el subconjunto de doble anotación, y discrepa en uno.
    experto2 = {tid: truth[tid] for tid in kappa_ids}
    disagreement_id = kappa_ids[0]
    other_cat = CAT_B if truth[disagreement_id] == CAT_A else CAT_A
    experto2[disagreement_id] = other_cat
    _fill_workbook(tmp_path / ANNOTATION_DIR / EXPERT2_FILE, experto2)

    result = score_and_merge(tmp_path)

    assert result["n_total"] == 10
    assert result["n_doble_anotado"] == 4
    assert result["n_arbitraje_pendiente"] == 1
    assert result["kappa"] is not None and result["kappa"] < 1.0

    golden = json.loads((tmp_path / "golden_set_sample.json").read_text(encoding="utf-8"))
    by_id = {e["ticket_id"]: e for e in golden}

    disagreed = by_id[disagreement_id]
    assert disagreed["necesita_arbitraje"] is True
    assert disagreed["categoria_gold"] is None
    assert disagreed["acuerdo"] is False

    agreed_kappa_id = next(tid for tid in kappa_ids if tid != disagreement_id)
    agreed = by_id[agreed_kappa_id]
    assert agreed["acuerdo"] is True
    assert agreed["categoria_gold"] == truth[agreed_kappa_id]

    single = next(e for e in golden if not e["doble_anotacion"])
    assert single["categoria_gold"] == single["categoria_experto1"]
    assert single["categoria_experto2"] is None


def test_score_and_merge_raises_on_incomplete_annotation(tmp_path):
    _write_tickets_eval(tmp_path, {CAT_A: 20, CAT_B: 20})
    entries = build_pool(tmp_path, seed=5, n=6, n_kappa=2)

    # Deja la planilla del experto 1 vacía (sin llenar ninguna categoría).
    with pytest.raises(ValueError, match="Experto 1"):
        score_and_merge(tmp_path)

    truth = {e["ticket_id"]: e["categoria_top9"] for e in entries}
    _fill_workbook(tmp_path / ANNOTATION_DIR / EXPERT1_FILE, truth)

    # Experto 1 completo, experto 2 sigue vacío -> debe fallar por el subconjunto Kappa.
    with pytest.raises(ValueError, match="Experto 2"):
        score_and_merge(tmp_path)


def test_read_annotations_rejects_invalid_category(tmp_path):
    _write_tickets_eval(tmp_path, {CAT_A: 5})
    build_pool(tmp_path, seed=1, n=5, n_kappa=1)

    path = tmp_path / ANNOTATION_DIR / EXPERT1_FILE
    wb = load_workbook(path)
    ws = wb["anotacion"]
    for row in ws.iter_rows(min_row=2, max_row=2):
        row[2].value = "Categoría inventada que no existe"
    wb.save(path)

    with pytest.raises(ValueError, match="no es una categoría top-9 válida"):
        _read_annotations(path)
