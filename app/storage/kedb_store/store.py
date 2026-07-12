"""KEDB article persistence (SQLite)."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas import KedbArticulo, KedbArticuloUpdate, KedbEstado, TicketResponse


class KedbStore:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.db_path = Path(self.settings.kedb_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kedb_articulos (
                    articulo_id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    categoria TEXT NOT NULL,
                    sintoma TEXT NOT NULL,
                    causa TEXT NOT NULL,
                    solucion TEXT NOT NULL,
                    tickets_fuente TEXT NOT NULL,
                    fecha_generacion TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    estado TEXT NOT NULL DEFAULT 'borrador',
                    calidad_experta REAL,
                    aplicable_a TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    articulo_id TEXT,
                    util INTEGER,
                    nueva_solucion TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categoria_correcciones (
                    ticket_id TEXT PRIMARY KEY,
                    categoria_original TEXT,
                    categoria_corregida TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_sessions (
                    ticket_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _row_to_articulo(self, row: sqlite3.Row) -> KedbArticulo:
        return KedbArticulo(
            articulo_id=row["articulo_id"],
            titulo=row["titulo"],
            categoria=row["categoria"],
            sintoma=row["sintoma"],
            causa=row["causa"],
            solucion=row["solucion"],
            tickets_fuente=json.loads(row["tickets_fuente"]),
            fecha_generacion=datetime.fromisoformat(row["fecha_generacion"]),
            version=row["version"],
            estado=KedbEstado(row["estado"]),
            calidad_experta=row["calidad_experta"],
            aplicable_a=row["aplicable_a"],
        )

    def create(self, articulo: KedbArticulo) -> KedbArticulo:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO kedb_articulos
                (articulo_id, titulo, categoria, sintoma, causa, solucion,
                 tickets_fuente, fecha_generacion, version, estado, calidad_experta, aplicable_a)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    articulo.articulo_id,
                    articulo.titulo,
                    articulo.categoria,
                    articulo.sintoma,
                    articulo.causa,
                    articulo.solucion,
                    json.dumps(articulo.tickets_fuente),
                    articulo.fecha_generacion.isoformat(),
                    articulo.version,
                    articulo.estado.value,
                    articulo.calidad_experta,
                    articulo.aplicable_a,
                ),
            )
        return articulo

    def delete(self, articulo_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM kedb_articulos WHERE articulo_id = ?", (articulo_id,)
            )
        return cur.rowcount > 0

    def get(self, articulo_id: str) -> KedbArticulo | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM kedb_articulos WHERE articulo_id = ?", (articulo_id,)
            ).fetchone()
        return self._row_to_articulo(row) if row else None

    def list_all(
        self, estado: KedbEstado | None = None, categoria: str | None = None
    ) -> list[KedbArticulo]:
        query = "SELECT * FROM kedb_articulos WHERE 1=1"
        params: list[str] = []
        if estado:
            query += " AND estado = ?"
            params.append(estado.value)
        if categoria:
            query += " AND categoria LIKE ?"
            params.append(f"%{categoria}%")
        query += " ORDER BY fecha_generacion DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_articulo(r) for r in rows]

    def update(self, articulo_id: str, data: KedbArticuloUpdate) -> KedbArticulo | None:
        existing = self.get(articulo_id)
        if not existing:
            return None
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return existing
        if "estado" in updates and updates["estado"] is not None:
            updates["estado"] = updates["estado"].value
        # Bump version when content fields change (not only estado transitions)
        content_keys = {"titulo", "sintoma", "causa", "solucion", "aplicable_a"}
        if content_keys & set(updates.keys()):
            updates["version"] = int(existing.version) + 1
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [articulo_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE kedb_articulos SET {set_clause} WHERE articulo_id = ?", values)
        return self.get(articulo_id)

    def export_all_markdown(self, solo_validados: bool = True) -> int:
        """Publish Markdown projection. By default only validated articles (live docs)."""
        from app.storage.kedb_store.markdown import write_markdown

        articulos = (
            self.list_all(estado=KedbEstado.VALIDADO) if solo_validados else self.list_all()
        )
        for articulo in articulos:
            write_markdown(articulo, self.settings)
        return len(articulos)

    def publish_markdown(self, articulo: KedbArticulo) -> None:
        """Write Markdown only for validated articles (docs projection)."""
        from app.storage.kedb_store.markdown import write_markdown

        if articulo.estado == KedbEstado.VALIDADO:
            write_markdown(articulo, self.settings)

    def pendientes(self) -> list[KedbArticulo]:
        return self.list_all(estado=KedbEstado.BORRADOR)

    def save_feedback(
        self,
        ticket_id: str,
        articulo_id: str | None = None,
        util: bool | None = None,
        nueva_solucion: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO ticket_feedback (ticket_id, articulo_id, util, nueva_solucion, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    articulo_id,
                    int(util) if util is not None else None,
                    nueva_solucion,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def save_categoria_correccion(
        self, ticket_id: str, categoria_original: str, categoria_corregida: str
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO categoria_correcciones
                (ticket_id, categoria_original, categoria_corregida, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    categoria_original,
                    categoria_corregida,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def save_ticket_session(self, response: TicketResponse) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ticket_sessions (ticket_id, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (
                    response.ticket_id,
                    response.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get_ticket_session(self, ticket_id: str) -> TicketResponse | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM ticket_sessions WHERE ticket_id = ?", (ticket_id,)
            ).fetchone()
        if not row:
            return None
        return TicketResponse.model_validate_json(row["payload"])


def new_articulo_id() -> str:
    return f"KEDB-{uuid.uuid4().hex[:12].upper()}"
