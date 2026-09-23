"""Persistent ticket session store (SQLite via KedbStore)."""

from functools import lru_cache

from app.schemas import TicketResponse, TicketStatusResponse
from app.storage.kedb_store.store import KedbStore


@lru_cache
def _store() -> KedbStore:
    return KedbStore()


def create_pending_ticket(ticket_id: str) -> None:
    _store().create_pending_ticket_session(ticket_id)


def save_ticket(response: TicketResponse) -> None:
    _store().save_ticket_session(response)


def fail_ticket(ticket_id: str, error: str) -> None:
    _store().fail_ticket_session(ticket_id, error)


def get_ticket(ticket_id: str) -> TicketStatusResponse | None:
    return _store().get_ticket_session(ticket_id)
