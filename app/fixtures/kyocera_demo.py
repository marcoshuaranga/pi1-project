"""Kyocera demo cluster — single source for seed / seed-demo / generate_demo_fixture."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.schemas import KedbArticulo, KedbEstado
from app.storage.kedb_store.store import new_articulo_id

logger = logging.getLogger(__name__)

CLUSTER_TITLE = "Configuración de impresora Kyocera 7003"
TITLE_MATCH = "configuración de impresora kyocera 7003"

# Fixture resolution: packaged copy → /data/fixtures mount → repo data/fixtures.
_PACKAGE_FIXTURE = Path(__file__).resolve().parent / "kyocera_demo_tickets.json"
_DATA_FIXTURE = Path("/data/fixtures/kyocera_demo_tickets.json")
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_FIXTURE = _REPO_ROOT / "data" / "fixtures" / "kyocera_demo_tickets.json"


def _fixture_candidates() -> list[Path]:
    return [_DATA_FIXTURE, _PACKAGE_FIXTURE, _REPO_FIXTURE]

DEMO_ARTICLE_TEMPLATE = {
    "titulo": "Configuración de impresora Kyocera TaskAlfa 7003i",
    "categoria": (
        "Equipos Informáticos > Equipo de impresión y escaneo > Impresora Multifuncional"
    ),
    "sintoma": (
        "El usuario no puede imprimir o requiere configurar la impresora "
        "multifuncional Kyocera 7003 en su equipo."
    ),
    "causa": (
        "Impresora predeterminada no configurada correctamente, "
        "o driver de la Kyocera 7003 no instalado."
    ),
    "solucion": (
        "1. Instalar/verificar el driver de la impresora Kyocera 7003.\n"
        "2. Configurar la impresora como predeterminada.\n"
        "3. Validar con hoja de prueba."
    ),
    "aplicable_a": "Impresoras Kyocera TaskAlfa 7003i en sedes MTC",
}

# Known IDs cited in DEMO.md / PRD (used to seed the versioned fixture).
_DEMO_MD_IDS = [
    "96044",
    "95984",
    "95645",
    "95439",
    "94922",
    "94595",
    "94571",
    "77962",
    "77975",
    "74359",
]


def _default_cluster_ids(target: int = 142) -> list[str]:
    """Deterministic ~142 IDs around the DEMO.md examples for offline demo."""
    ids = list(_DEMO_MD_IDS)
    seen = set(ids)
    ranges = [
        range(74360, 74450),
        range(77900, 77962),
        range(94500, 94571),
        range(94572, 94600),
        range(94900, 94922),
        range(94923, 95000),
        range(95400, 95439),
        range(95440, 95500),
        range(95600, 95645),
        range(95646, 95700),
        range(95900, 95984),
        range(95985, 96044),
        range(96045, 96150),
    ]
    for r in ranges:
        for n in r:
            s = str(n)
            if s not in seen:
                ids.append(s)
                seen.add(s)
            if len(ids) >= target:
                return ids[:target]
    return ids[:target]


def _resolve_fixture_path(path: Path | None = None) -> Path | None:
    if path is not None:
        return path if path.exists() else None
    for candidate in _fixture_candidates():
        if candidate.exists():
            return candidate
    return None


def _read_fixture_file(path: Path | None = None) -> list[str]:
    fixture = _resolve_fixture_path(path)
    if fixture is None:
        return []
    try:
        data = json.loads(fixture.read_text(encoding="utf-8"))
        ids = data.get("ticket_ids") or []
        return [str(i) for i in ids if i]
    except (OSError, json.JSONDecodeError):
        logger.warning("No se pudo leer fixture Kyocera en %s", fixture)
        return []


def _extract_from_processed(processed_dir: Path) -> list[str]:
    """Pull ticket_ids whose title matches the Kyocera 7003 config cluster."""
    tickets_path = processed_dir / "tickets_all.json"
    if not tickets_path.exists():
        # Prefer lighter splits if full dump is missing
        for name in ("tickets_train.json", "tickets_eval.json"):
            alt = processed_dir / name
            if alt.exists():
                tickets_path = alt
                break
        else:
            return []

    try:
        tickets = json.loads(tickets_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Error leyendo %s", tickets_path)
        return []

    matched: list[str] = []
    for t in tickets:
        titulo = (t.get("titulo_anon") or t.get("titulo") or "").lower()
        if TITLE_MATCH in titulo:
            tid = t.get("ticket_id")
            if tid:
                matched.append(str(tid))
    # Stable unique order
    seen: set[str] = set()
    unique: list[str] = []
    for tid in matched:
        if tid not in seen:
            seen.add(tid)
            unique.append(tid)
    return unique


def _write_fixture(ids: list[str], path: Path | None = None) -> None:
    targets = [path] if path is not None else [_DATA_FIXTURE, _REPO_FIXTURE, _PACKAGE_FIXTURE]
    payload = {
        "cluster_title": CLUSTER_TITLE,
        "ticket_ids": ids,
        "count": len(ids),
        "note": (
            "Prefer extract from tickets_all.json after pipeline full; "
            "this file is the offline fallback for DEMO Escena 2."
        ),
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    for fixture in targets:
        if fixture is None:
            continue
        try:
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text(text, encoding="utf-8")
            return
        except OSError:
            continue
    logger.warning("No se pudo actualizar ningún fixture Kyocera")


def load_kyocera_ticket_ids(
    *,
    refresh_fixture: bool = False,
    processed_path: str | Path | None = None,
    fixture_path: Path | None = None,
) -> list[str]:
    """Return ticket IDs for the Kyocera demo cluster.

    Prefer processed extract (≥5 matches); else versioned fixture; else defaults.
    """
    settings = get_settings()
    processed = Path(processed_path or settings.data_processed_path)
    extracted = _extract_from_processed(processed)
    if len(extracted) >= 5:
        if refresh_fixture:
            _write_fixture(extracted, fixture_path)
        logger.info("Kyocera cluster: %s tickets from processed data", len(extracted))
        return extracted

    fixture_ids = _read_fixture_file(fixture_path)
    if len(fixture_ids) >= 5:
        logger.info("Kyocera cluster: %s tickets from fixture file", len(fixture_ids))
        return fixture_ids

    defaults = _default_cluster_ids(142)
    _write_fixture(defaults, fixture_path)
    logger.info("Kyocera cluster: %s tickets from built-in defaults", len(defaults))
    return defaults


def build_demo_articulo(
    *,
    ticket_ids: list[str] | None = None,
    articulo_id: str | None = None,
) -> KedbArticulo:
    """Build the Kyocera borrador article used by seed paths."""
    ids = ticket_ids if ticket_ids is not None else load_kyocera_ticket_ids()
    return KedbArticulo(
        articulo_id=articulo_id or new_articulo_id(),
        titulo=DEMO_ARTICLE_TEMPLATE["titulo"],
        categoria=DEMO_ARTICLE_TEMPLATE["categoria"],
        sintoma=DEMO_ARTICLE_TEMPLATE["sintoma"],
        causa=DEMO_ARTICLE_TEMPLATE["causa"],
        solucion=DEMO_ARTICLE_TEMPLATE["solucion"],
        tickets_fuente=ids,
        fecha_generacion=datetime.now(timezone.utc),
        estado=KedbEstado.BORRADOR,
        aplicable_a=DEMO_ARTICLE_TEMPLATE["aplicable_a"],
    )


def _is_demo_kyocera_articulo(articulo: KedbArticulo) -> bool:
    """Match demo Kyocera articles in any estado (seed, edits, approved practice)."""
    titulo = (articulo.titulo or "").lower()
    return (
        "kyocera" in titulo
        or "7003" in titulo
        or titulo.startswith("test edit")
        or DEMO_ARTICLE_TEMPLATE["titulo"].lower() in titulo
    )


def _is_demo_kyocera_borrador(articulo: KedbArticulo) -> bool:
    """Match demo Kyocera drafts only."""
    return articulo.estado == KedbEstado.BORRADOR and _is_demo_kyocera_articulo(articulo)


def ensure_clean_demo_articulo(
    store,
    *,
    ticket_ids: list[str] | None = None,
    refresh_fixture: bool = True,
) -> tuple[KedbArticulo, int]:
    """Idempotent demo seed: remove Kyocera borradores, create one fresh article.

    Returns (articulo, removed_count).
    """
    ids = (
        ticket_ids
        if ticket_ids is not None
        else load_kyocera_ticket_ids(refresh_fixture=refresh_fixture)
    )
    removed = 0
    for art in store.pendientes():
        if _is_demo_kyocera_borrador(art):
            if store.delete(art.articulo_id):
                removed += 1
                logger.info(
                    "Removed demo borrador %s (%s)", art.articulo_id, art.titulo[:60]
                )

    articulo = build_demo_articulo(ticket_ids=ids)
    store.create(articulo)
    return articulo, removed


def reset_demo_state(
    store,
    *,
    clear_chroma: bool = True,
    clear_markdown: bool = True,
    refresh_fixture: bool = True,
) -> dict:
    """Full demo reset: remove all Kyocera KEDB rows (any estado), purge RAG/docs, re-seed.

    Returns a summary dict for the CLI.
    """
    from app.config import get_settings
    from app.storage.kedb_store.markdown import docs_dir

    settings = get_settings()
    to_remove = [a for a in store.list_all() if _is_demo_kyocera_articulo(a)]
    removed_ids = [a.articulo_id for a in to_remove]
    removed_db = 0
    for art in to_remove:
        if store.delete(art.articulo_id):
            removed_db += 1

    chroma_deleted = 0
    if clear_chroma and removed_ids:
        try:
            from app.storage.vector_db.client import get_kedb_collection

            col = get_kedb_collection(settings)
            col.delete(ids=removed_ids)
            chroma_deleted = len(removed_ids)
        except Exception:
            logger.exception("No se pudo limpiar Chroma KEDB; se continúa con el seed")

    md_deleted = 0
    if clear_markdown and removed_ids:
        root = docs_dir(settings)
        for aid in removed_ids:
            for path in root.glob(f"{aid}*"):
                try:
                    path.unlink(missing_ok=True)
                    md_deleted += 1
                except OSError:
                    logger.warning("No se pudo borrar %s", path)

    articulo, _ = ensure_clean_demo_articulo(
        store, refresh_fixture=refresh_fixture
    )
    # ensure_clean also removes borradores; we already cleared all Kyocera — count is fine
    return {
        "removed_db": removed_db,
        "removed_ids": removed_ids,
        "chroma_deleted": chroma_deleted,
        "markdown_deleted": md_deleted,
        "articulo": articulo,
        "pendientes": len(store.pendientes()),
    }
