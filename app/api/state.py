"""Persistent ticket session store (SQLite via KedbStore)."""

from functools import lru_cache

from app.schemas import TicketResponse
from app.storage.kedb_store.store import KedbStore


@lru_cache
def _store() -> KedbStore:
    return KedbStore()


def save_ticket(response: TicketResponse) -> None:
    _store().save_ticket_session(response)


def get_ticket(ticket_id: str) -> TicketResponse | None:
    return _store().get_ticket_session(ticket_id)
