"""Ticket assistance endpoints (HU01, HU04, HU06)."""

import asyncio

from fastapi import APIRouter, HTTPException

from pi_api.deps import get_kedb_store, get_orchestrator
from pi_api.state import get_ticket, save_ticket
from pi_core.schemas import (
    CategoriaCorreccion,
    FeedbackRequest,
    TicketInput,
    TicketResponse,
    TicketStatusResponse,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse)
async def create_ticket(body: TicketInput) -> TicketResponse:
    """HU01 + HU04 + HU06 — classify, prioritize, retrieve solutions."""
    response = await asyncio.to_thread(get_orchestrator().process_ticket, body.texto)
    save_ticket(response)
    return response


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
    get_kedb_store().save_categoria_correccion(ticket_id, ticket.result.categoria, body.categoria)
    ticket.result.categoria = body.categoria
    save_ticket(ticket.result)
    return {"ticket_id": ticket_id, "categoria": body.categoria}


@router.post("/{ticket_id}/resolucion")
async def register_resolution(ticket_id: str, body: dict):
    """Register applied solution — candidate for next KEDB batch."""
    ticket = get_ticket(ticket_id)
    if not ticket or not ticket.result:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    get_kedb_store().save_feedback(ticket_id, nueva_solucion=body.get("solucion", ""))
    return {"ticket_id": ticket_id, "status": "registrado"}


@router.post("/{ticket_id}/feedback")
async def ticket_feedback(ticket_id: str, body: FeedbackRequest):
    """HU11 + HU12 — utility feedback / new solution."""
    get_kedb_store().save_feedback(
        ticket_id,
        articulo_id=body.articulo_id,
        util=body.util,
        nueva_solucion=body.nueva_solucion,
    )
    return {"ticket_id": ticket_id, "status": "ok"}
