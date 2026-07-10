"""Ticket assistance endpoints (HU01, HU04, HU06)."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator.graph import Orchestrator
from app.api.state import get_ticket, save_ticket
from app.schemas import CategoriaCorreccion, FeedbackRequest, TicketInput, TicketResponse
from app.storage.kedb_store.store import KedbStore

router = APIRouter(prefix="/tickets", tags=["tickets"])


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


@lru_cache
def get_kedb_store() -> KedbStore:
    return KedbStore()


@router.post("", response_model=TicketResponse)
async def create_ticket(body: TicketInput) -> TicketResponse:
    """HU01 + HU04 + HU06 — classify, prioritize, retrieve solutions."""
    response = get_orchestrator().process_ticket(body.texto)
    save_ticket(response)
    return response


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_status(ticket_id: str) -> TicketResponse:
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.patch("/{ticket_id}/categoria")
async def correct_categoria(ticket_id: str, body: CategoriaCorreccion):
    """HU03 — operator category correction."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    get_kedb_store().save_categoria_correccion(ticket_id, ticket.categoria, body.categoria)
    ticket.categoria = body.categoria
    save_ticket(ticket)
    return {"ticket_id": ticket_id, "categoria": body.categoria}


@router.post("/{ticket_id}/resolucion")
async def register_resolution(ticket_id: str, body: dict):
    """Register applied solution — candidate for next KEDB batch."""
    ticket = get_ticket(ticket_id)
    if not ticket:
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
