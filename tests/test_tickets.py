from unittest.mock import patch

from fastapi.testclient import TestClient

from app.agents.billing import BillingResult
from app.agents.tech_support import TechSupportResult
from app.agents.triage import TriageResult
from app.main import app

client = TestClient(app)


def test_create_and_fetch_ticket():
    response = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "Can't log in",
            "message": "I get an error every time I try to sign in.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert "ticket_id" in body

    fetched = client.get(f"/tickets/{body['ticket_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["subject"] == "Can't log in"


def test_get_unknown_ticket_returns_404():
    response = client.get("/tickets/does-not-exist")
    assert response.status_code == 404


def test_create_ticket_missing_field_returns_422():
    response = client.post(
        "/tickets",
        json={"customer_email": "user@example.com", "subject": "Missing message"},
    )
    assert response.status_code == 422


def test_create_ticket_invalid_email_returns_422():
    response = client.post(
        "/tickets",
        json={
            "customer_email": "not-an-email",
            "subject": "Test",
            "message": "Test message",
        },
    )
    assert response.status_code == 422


def test_triage_endpoint_updates_ticket():
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "Refund please",
            "message": "I was charged twice.",
        },
    ).json()

    fake_result = TriageResult(category="billing", confidence=0.92, reasoning="mentions charge")
    with patch("app.api.tickets.classify_ticket", return_value=fake_result):
        response = client.post(f"/tickets/{created['ticket_id']}/triage")

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "billing"
    assert body["confidence"] == 0.92
    assert body["status"] == "triaged"


def test_triage_endpoint_unknown_ticket_returns_404():
    response = client.post("/tickets/does-not-exist/triage")
    assert response.status_code == 404


def _create_technical_ticket() -> dict:
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "App crashes",
            "message": "It closes right after opening.",
        },
    ).json()

    fake_triage = TriageResult(category="technical", confidence=0.95, reasoning="mentions crash")
    with patch("app.api.tickets.classify_ticket", return_value=fake_triage):
        client.post(f"/tickets/{created['ticket_id']}/triage")

    return created


def test_tech_support_endpoint_resolves_with_good_match():
    created = _create_technical_ticket()

    fake_result = TechSupportResult(
        status="resolved", reply="Try restarting.", source_doc="app_crash_on_startup", match_score=0.8
    )
    with patch("app.api.tickets.resolve_technical_ticket", return_value=fake_result):
        response = client.post(f"/tickets/{created['ticket_id']}/tech-support")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["reply"] == "Try restarting."
    assert body["resolved_via"] == "app_crash_on_startup"


def test_tech_support_endpoint_rejects_non_technical_ticket():
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "Refund",
            "message": "Charge me back please.",
        },
    ).json()

    response = client.post(f"/tickets/{created['ticket_id']}/tech-support")
    assert response.status_code == 400


def test_tech_support_endpoint_unknown_ticket_returns_404():
    response = client.post("/tickets/does-not-exist/tech-support")
    assert response.status_code == 404


def _create_billing_ticket() -> dict:
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "Refund please",
            "message": "I was charged twice.",
            "transaction_id": "pay_123",
        },
    ).json()

    fake_triage = TriageResult(category="billing", confidence=0.95, reasoning="mentions charge")
    with patch("app.api.tickets.classify_ticket", return_value=fake_triage):
        client.post(f"/tickets/{created['ticket_id']}/triage")

    return created


def test_billing_endpoint_refunds_successfully():
    created = _create_billing_ticket()

    fake_result = BillingResult(status="refunded", reply="Refunded.", refund_id="rfnd_1", amount=100000)
    with patch("app.api.tickets.resolve_billing_ticket", return_value=fake_result):
        response = client.post(f"/tickets/{created['ticket_id']}/billing")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "refunded"
    assert body["refund_id"] == "rfnd_1"
    assert body["refund_amount"] == 100000


def test_billing_endpoint_rejects_non_billing_ticket():
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "App crashes",
            "message": "It closes right after opening.",
        },
    ).json()

    response = client.post(f"/tickets/{created['ticket_id']}/billing")
    assert response.status_code == 400


def test_billing_endpoint_unknown_ticket_returns_404():
    response = client.post("/tickets/does-not-exist/billing")
    assert response.status_code == 404
