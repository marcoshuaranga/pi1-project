"""In-memory ticket store for session state."""

from app.schemas import TicketResponse

_ticket_store: dict[str, TicketResponse] = {}


def save_ticket(response: TicketResponse) -> None:
    _ticket_store[response.ticket_id] = response


def get_ticket(ticket_id: str) -> TicketResponse | None:
    return _ticket_store.get(ticket_id)
