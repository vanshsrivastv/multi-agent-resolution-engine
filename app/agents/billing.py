from typing import Literal

import requests
from pydantic import BaseModel
from razorpay.errors import GatewayError, ServerError

from app.models.ticket import Ticket
from app.payments import get_payment, refund_payment
from app.retry import with_retries

# BadRequestError (invalid transaction id, insufficient balance, wrong
# payment state, etc.) is deliberately NOT here - it's permanent, retrying
# the same request will not change the outcome.
PAYMENT_TRANSIENT = (ServerError, GatewayError, requests.Timeout, requests.ConnectionError)


class BillingResult(BaseModel):
    status: Literal["refunded", "already_refunded", "needs_human"]
    reply: str | None = None
    refund_id: str | None = None
    amount: int | None = None
    reason: str | None = None


def _refund_with_timeout_safe_retry(transaction_id: str) -> dict:
    try:
        return refund_payment(transaction_id)
    except PAYMENT_TRANSIENT:
        # We don't know whether the refund actually went through before the
        # connection/timeout failure - never blindly retry a refund. Check
        # the provider's own record first.
        current = get_payment(transaction_id)
        if current["status"] == "refunded":
            # It succeeded despite the failure on our end. We don't have
            # the refund object from that original call, so refund_id is
            # left unknown here rather than guessed.
            return {"id": None, "status": "processed"}
        # Confirmed no refund happened yet - now it's safe to try once more.
        return refund_payment(transaction_id)


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
        payment = with_retries(lambda: get_payment(ticket.transaction_id), PAYMENT_TRANSIENT)
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
        refund = _refund_with_timeout_safe_retry(ticket.transaction_id)
    except Exception as e:
        return BillingResult(status="needs_human", reason=f"refund failed: {e}")

    amount_display = payment["amount"] / 100
    reference_note = f" Refund reference: {refund['id']}." if refund["id"] else ""
    return BillingResult(
        status="refunded",
        reply=f"Your payment of Rs.{amount_display:.2f} has been refunded.{reference_note}",
        refund_id=refund["id"],
        amount=payment["amount"],
    )
