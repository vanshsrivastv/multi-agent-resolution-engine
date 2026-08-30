from fastapi import APIRouter, HTTPException

from app import store
from app.models.ticket import Ticket, TicketCreate

router = APIRouter()


@router.post("/tickets", status_code=201)
def create_ticket(data: TicketCreate) -> Ticket:
    ticket = Ticket.from_create(data)
    store.save(ticket)
    return ticket


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return ticket
