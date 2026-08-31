from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, EmailStr


class TicketCreate(BaseModel):
    customer_email: EmailStr
    subject: str
    message: str
    transaction_id: str | None = None


class Ticket(TicketCreate):
    ticket_id: str
    status: str
    created_at: datetime
    category: str | None = None
    confidence: float | None = None
    reply: str | None = None
    resolved_via: str | None = None
    match_score: float | None = None
    refund_id: str | None = None
    refund_amount: int | None = None

    @classmethod
    def from_create(cls, data: TicketCreate) -> "Ticket":
        return cls(
            ticket_id=str(uuid4()),
            status="received",
            created_at=datetime.now(timezone.utc),
            **data.model_dump(),
        )
