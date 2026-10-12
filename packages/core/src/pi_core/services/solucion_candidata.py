"""HU12 — nueva solución del Operador registrada como candidata a artículo KEDB.

Decisión: la candidata entra como `KedbArticulo` en `borrador` con el ticket como única fuente
(`tickets_fuente=[ticket_id]`). Así pasa por la validación del Experto (constitución I): hasta que
un humano la aprueba no se indexa ni se publica, y la trazabilidad N:1 se cumple con N=1 (HU09).
Antes de registrar se compara contra los artículos KEDB existentes con el retriever del Agente RAG.
"""

from datetime import UTC, datetime
from typing import Protocol

from pi_core.config import get_settings
from pi_core.schemas import KedbArticulo, KedbEstado, SolucionSugerida
from pi_core.storage.kedb_store.store import KedbStore, new_articulo_id

SOLUCION_MIN_CHARS = 20


class _Buscador(Protocol):
    def search_kedb(self, query: str, top_k: int = 10) -> list[SolucionSugerida]: ...


class SolucionInvalida(ValueError):
    """Faltan campos obligatorios o no cumplen el mínimo."""


class PosibleDuplicado(Exception):
    """Hay un artículo KEDB muy similar; hace falta confirmación explícita para guardar igual."""

    def __init__(self, similares: list[SolucionSugerida]):
        self.similares = similares
        super().__init__("Posible duplicado de un artículo KEDB existente")


def validar_solucion(solucion: str | None) -> str:
    texto = (solucion or "").strip()
    if not texto:
        raise SolucionInvalida("Falta la solución: describa los pasos aplicados.")
    if len(texto) < SOLUCION_MIN_CHARS:
        raise SolucionInvalida(
            f"La solución es muy corta ({len(texto)} caracteres); "
            f"escriba al menos {SOLUCION_MIN_CHARS}."
        )
    return texto


def registrar_solucion_candidata(
    store: KedbStore,
    buscador: _Buscador,
    *,
    ticket_id: str,
    categoria: str,
    solucion: str | None,
    confirmar_duplicado: bool = False,
) -> KedbArticulo:
    texto = validar_solucion(solucion)
    if not confirmar_duplicado:
        umbral = get_settings().umbral_duplicado_kedb
        similares = [s for s in buscador.search_kedb(texto, top_k=3) if s.score >= umbral]
        if similares:
            raise PosibleDuplicado(similares)

    articulo = store.create(
        KedbArticulo(
            articulo_id=new_articulo_id(),
            titulo=f"Solución del operador — {categoria.split('>')[-1].strip()}",
            categoria=categoria,
            sintoma=f"Pendiente de redacción por el Experto (ticket {ticket_id}).",
            causa="Pendiente de determinar por el Experto.",
            solucion=texto,
            tickets_fuente=[ticket_id],
            fecha_generacion=datetime.now(UTC),
            estado=KedbEstado.BORRADOR,
        )
    )
    store.save_feedback(ticket_id, nueva_solucion=texto)
    return articulo
