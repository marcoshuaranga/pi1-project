"""Ticket assistance endpoints (HU01, HU04, HU06)."""

import asyncio

from fastapi import APIRouter, HTTPException

from pi_api.deps import get_kedb_store, get_orchestrator
from pi_api.state import get_ticket, save_ticket
from pi_core.constants import TOP9_CATEGORIES
from pi_core.schemas import (
    CategoriaCorreccion,
    FeedbackRequest,
    ResolucionRequest,
    TicketInput,
    TicketResponse,
    TicketStatusResponse,
)
from pi_core.services.solucion_candidata import (
    PosibleDuplicado,
    SolucionInvalida,
    registrar_solucion_candidata,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse)
async def create_ticket(body: TicketInput) -> TicketResponse:
    """HU01 + HU04 + HU06 — classify, prioritize, retrieve solutions."""
    response = await asyncio.to_thread(get_orchestrator().process_ticket, body.texto)
    save_ticket(response)
    return response


@router.get("/categorias", response_model=list[str])
async def list_categorias() -> list[str]:
    """HU03 — catálogo de categorías válidas (top-9) para la corrección del Operador."""
    return list(TOP9_CATEGORIES)


@router.get("/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: str) -> TicketStatusResponse:
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.patch("/{ticket_id}/categoria")
async def correct_categoria(ticket_id: str, body: CategoriaCorreccion):
    """HU03 — operator category correction."""
    ticket = get_ticket(ticket_id)
    if not ticket or not ticket.result:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if body.categoria not in TOP9_CATEGORIES:  # CA3
        raise HTTPException(
            status_code=422,
            detail="Categoría no válida. Seleccione una de las categorías del catálogo.",
        )
    if body.categoria == ticket.result.categoria:  # CA2: nada que registrar
        return {"ticket_id": ticket_id, "categoria": body.categoria, "cambio": False}
    get_kedb_store().save_categoria_correccion(ticket_id, ticket.result.categoria, body.categoria)
    ticket.result.categoria = body.categoria
    save_ticket(ticket.result)
    return {"ticket_id": ticket_id, "categoria": body.categoria, "cambio": True}


async def _registrar_nueva_solucion(
    ticket_id: str, solucion: str | None, confirmar_duplicado: bool
) -> dict:
    """HU12 — registra la solución como candidata KEDB (borrador); ver services/solucion_candidata."""
    ticket = get_ticket(ticket_id)
    if not ticket or not ticket.result:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    from pi_api.routers import kedb as kedb_router

    try:
        articulo = await asyncio.to_thread(
            registrar_solucion_candidata,
            get_kedb_store(),
            kedb_router.get_rag(),
            ticket_id=ticket_id,
            categoria=ticket.result.categoria,
            solucion=solucion,
            confirmar_duplicado=confirmar_duplicado,
        )
    except SolucionInvalida as e:  # CA2
        raise HTTPException(status_code=422, detail=str(e)) from e
    except PosibleDuplicado as e:  # CA3
        raise HTTPException(
            status_code=409,
            detail={
                "codigo": "posible_duplicado",
                "mensaje": "Ya existe un artículo KEDB muy similar. Confirme si desea guardar igual.",
                "similares": [s.model_dump() for s in e.similares],
            },
        ) from e
    return {"ticket_id": ticket_id, "status": "registrado", "articulo_id": articulo.articulo_id}


@router.post("/{ticket_id}/resolucion", deprecated=True)
async def register_resolution(ticket_id: str, body: ResolucionRequest):
    """DEPRECADO: usar POST /tickets/{id}/feedback con `nueva_solucion`. Misma lógica HU12."""
    return await _registrar_nueva_solucion(ticket_id, body.solucion, body.confirmar_duplicado)


@router.post("/{ticket_id}/feedback")
async def ticket_feedback(ticket_id: str, body: FeedbackRequest):
    """HU11 (utilidad, upsert) o HU12 (nueva solución candidata KEDB)."""
    if body.nueva_solucion is not None:
        return await _registrar_nueva_solucion(
            ticket_id, body.nueva_solucion, body.confirmar_duplicado
        )
    if body.articulo_id is None or body.util is None:
        raise HTTPException(
            status_code=422,
            detail="Indique articulo_id y util (calificación) o nueva_solucion.",
        )
    get_kedb_store().save_feedback(ticket_id, articulo_id=body.articulo_id, util=body.util)
    return {"ticket_id": ticket_id, "status": "ok"}
