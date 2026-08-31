from typing import Literal

from pydantic import BaseModel

from app.models.ticket import Ticket
from app.payments import get_payment, refund_payment


class BillingResult(BaseModel):
    status: Literal["refunded", "already_refunded", "needs_human"]
    reply: str | None = None
    refund_id: str | None = None
    amount: int | None = None
    reason: str | None = None


def resolve_billing_ticket(ticket: Ticket) -> BillingResult:
    if not ticket.transaction_id:
        return BillingResult(status="needs_human", reason="ticket has no transaction_id")

    # Idempotency, layer 1: don't even call the payment API if we already
    # recorded this ticket as resolved.
    if ticket.status in ("refunded", "already_refunded"):
        return BillingResult(
            status=ticket.status,
            reply=ticket.reply,
            refund_id=ticket.refund_id,
            amount=ticket.refund_amount,
        )

    try:
        payment = get_payment(ticket.transaction_id)
    except Exception as e:
        return BillingResult(status="needs_human", reason=f"could not fetch transaction: {e}")

    # Idempotency, layer 2: trust the payment provider's own record over
    # ours, in case our ticket state and Razorpay's state ever disagree.
    if payment["status"] == "refunded":
        return BillingResult(
            status="already_refunded",
            reply="This payment was already refunded previously — no further action needed.",
            amount=payment["amount"],
        )

    if payment["status"] != "captured":
        return BillingResult(
            status="needs_human",
            reason=f"payment is not in a refundable state (status: {payment['status']})",
        )

    try:
        refund = refund_payment(ticket.transaction_id)
    except Exception as e:
        return BillingResult(status="needs_human", reason=f"refund failed: {e}")

    amount_display = payment["amount"] / 100
    return BillingResult(
        status="refunded",
        reply=f"Your payment of Rs.{amount_display:.2f} has been refunded. Refund reference: {refund['id']}.",
        refund_id=refund["id"],
        amount=payment["amount"],
    )
