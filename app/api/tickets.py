from fastapi import APIRouter, HTTPException

from app import store
from app.agents.billing import resolve_billing_ticket
from app.agents.tech_support import resolve_technical_ticket
from app.agents.triage import TriageError, classify_ticket
from app.graph import ALREADY_HANDLED_STATUSES, run_pipeline
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


@router.post("/tickets/{ticket_id}/triage")
def triage_ticket(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    try:
        result = classify_ticket(ticket)
    except TriageError as e:
        raise HTTPException(status_code=502, detail=str(e))

    updated = ticket.model_copy(
        update={
            "category": result.category,
            "confidence": result.confidence,
            "status": "triaged",
        }
    )
    store.save(updated)
    return updated


@router.post("/tickets/{ticket_id}/tech-support")
def tech_support_ticket(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    if ticket.category != "technical":
        raise HTTPException(
            status_code=400,
            detail="ticket is not categorized as technical; run /triage first",
        )

    result = resolve_technical_ticket(ticket)

    updated = ticket.model_copy(
        update={
            "status": result.status,
            "reply": result.reply,
            "resolved_via": result.source_doc,
            "match_score": result.match_score,
        }
    )
    store.save(updated)
    return updated


@router.post("/tickets/{ticket_id}/process")
def process_ticket(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")

    # Already resolved, or already paused waiting on a human - don't
    # re-run the pipeline (would waste an LLM call, or confuse the graph's
    # paused state for a ticket already sitting at an interrupt).
    if ticket.status in ALREADY_HANDLED_STATUSES:
        return ticket

    final_ticket = run_pipeline(ticket)
    store.save(final_ticket)
    return final_ticket


@router.post("/tickets/{ticket_id}/billing")
def billing_ticket(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    if ticket.category != "billing":
        raise HTTPException(
            status_code=400,
            detail="ticket is not categorized as billing; run /triage first",
        )

    result = resolve_billing_ticket(ticket)

    updated = ticket.model_copy(
        update={
            "status": result.status,
            "reply": result.reply,
            "refund_id": result.refund_id,
            "refund_amount": result.amount,
        }
    )
    store.save(updated)
    return updated
