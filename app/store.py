from app.models.ticket import Ticket

_tickets: dict[str, Ticket] = {}


def save(ticket: Ticket) -> None:
    _tickets[ticket.ticket_id] = ticket


def get(ticket_id: str) -> Ticket | None:
    return _tickets.get(ticket_id)
