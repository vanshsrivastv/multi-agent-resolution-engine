from unittest.mock import patch

from app.agents.billing import resolve_billing_ticket
from app.models.ticket import Ticket


def make_ticket(**overrides) -> Ticket:
    defaults = dict(
        ticket_id="t-1",
        status="triaged",
        created_at="2026-01-01T00:00:00Z",
        customer_email="user@example.com",
        subject="Refund please",
        message="Charge me back",
        category="billing",
        transaction_id="pay_123",
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def test_needs_human_when_no_transaction_id():
    result = resolve_billing_ticket(make_ticket(transaction_id=None))
    assert result.status == "needs_human"


def test_short_circuits_if_ticket_already_refunded():
    ticket = make_ticket(status="refunded", reply="already handled", refund_id="rfnd_1", refund_amount=500)

    with patch("app.agents.billing.get_payment") as mock_get:
        result = resolve_billing_ticket(ticket)

    mock_get.assert_not_called()
    assert result.status == "refunded"
    assert result.refund_id == "rfnd_1"


def test_needs_human_when_transaction_lookup_fails():
    with patch("app.agents.billing.get_payment", side_effect=Exception("not found")):
        result = resolve_billing_ticket(make_ticket())

    assert result.status == "needs_human"


def test_already_refunded_when_provider_says_so():
    fake_payment = {"id": "pay_123", "status": "refunded", "amount": 100000, "currency": "INR"}

    with patch("app.agents.billing.get_payment", return_value=fake_payment):
        with patch("app.agents.billing.refund_payment") as mock_refund:
            result = resolve_billing_ticket(make_ticket())

    mock_refund.assert_not_called()
    assert result.status == "already_refunded"


def test_needs_human_when_payment_not_captured():
    fake_payment = {"id": "pay_123", "status": "authorized", "amount": 100000, "currency": "INR"}

    with patch("app.agents.billing.get_payment", return_value=fake_payment):
        result = resolve_billing_ticket(make_ticket())

    assert result.status == "needs_human"


def test_refunds_successfully():
    fake_payment = {"id": "pay_123", "status": "captured", "amount": 100000, "currency": "INR"}
    fake_refund = {"id": "rfnd_1", "status": "processed"}

    with patch("app.agents.billing.get_payment", return_value=fake_payment):
        with patch("app.agents.billing.refund_payment", return_value=fake_refund):
            result = resolve_billing_ticket(make_ticket())

    assert result.status == "refunded"
    assert result.refund_id == "rfnd_1"
    assert result.amount == 100000


def test_needs_human_when_refund_api_fails():
    fake_payment = {"id": "pay_123", "status": "captured", "amount": 100000, "currency": "INR"}

    with patch("app.agents.billing.get_payment", return_value=fake_payment):
        with patch("app.agents.billing.refund_payment", side_effect=Exception("API timeout")):
            result = resolve_billing_ticket(make_ticket())

    assert result.status == "needs_human"
