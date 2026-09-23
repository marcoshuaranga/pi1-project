"""Persistent ticket session store (SQLite via KedbStore)."""

from pi_api.deps import get_kedb_store
from pi_core.schemas import TicketResponse, TicketStatusResponse


def create_pending_ticket(ticket_id: str) -> None:
    get_kedb_store().create_pending_ticket_session(ticket_id)


def save_ticket(response: TicketResponse) -> None:
    get_kedb_store().save_ticket_session(response)


def fail_ticket(ticket_id: str, error: str) -> None:
    get_kedb_store().fail_ticket_session(ticket_id, error)


def get_ticket(ticket_id: str) -> TicketStatusResponse | None:
    return get_kedb_store().get_ticket_session(ticket_id)
