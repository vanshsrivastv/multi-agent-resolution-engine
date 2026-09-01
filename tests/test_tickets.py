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


def test_process_endpoint_runs_full_pipeline():
    created = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "App crashes",
            "message": "It closes right after opening.",
        },
    ).json()

    fake_triage = TriageResult(category="technical", confidence=0.97, reasoning="crash")
    fake_resolution = TechSupportResult(
        status="resolved", reply="Try restarting.", source_doc="doc1", match_score=0.8
    )
    with patch("app.graph.classify_ticket", return_value=fake_triage):
        with patch("app.graph.resolve_technical_ticket", return_value=fake_resolution):
            response = client.post(f"/tickets/{created['ticket_id']}/process")

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "technical"
    assert body["status"] == "resolved"
    assert body["reply"] == "Try restarting."


def test_process_endpoint_unknown_ticket_returns_404():
    response = client.post("/tickets/does-not-exist/process")
    assert response.status_code == 404


def test_process_endpoint_pauses_for_human_review():
    created = client.post(
        "/tickets",
        json={"customer_email": "user@example.com", "subject": "hmm", "message": "not sure what"},
    ).json()

    fake_triage = TriageResult(category="general", confidence=0.4, reasoning="unclear")
    with patch("app.graph.classify_ticket", return_value=fake_triage):
        with patch("app.graph.send_escalation"):
            response = client.post(f"/tickets/{created['ticket_id']}/process")

    assert response.status_code == 200
    assert response.json()["status"] == "needs_human"


def test_process_endpoint_does_not_rerun_already_handled_ticket():
    created = client.post(
        "/tickets",
        json={"customer_email": "user@example.com", "subject": "App crashes", "message": "closes on open"},
    ).json()

    fake_triage = TriageResult(category="technical", confidence=0.97, reasoning="crash")
    fake_resolution = TechSupportResult(status="resolved", reply="Try restarting.", source_doc="doc1", match_score=0.8)
    with patch("app.graph.classify_ticket", return_value=fake_triage) as mock_triage:
        with patch("app.graph.resolve_technical_ticket", return_value=fake_resolution):
            first = client.post(f"/tickets/{created['ticket_id']}/process")
            second = client.post(f"/tickets/{created['ticket_id']}/process")

    assert first.json()["status"] == "resolved"
    assert second.json() == first.json()
    assert mock_triage.call_count == 1  # second call didn't re-run the pipeline


def test_slack_actions_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")

    response = client.post(
        "/slack/actions",
        data={"payload": "{}"},
        headers={"X-Slack-Signature": "v0=bogus", "X-Slack-Request-Timestamp": "1700000000"},
    )
    assert response.status_code == 401


def test_slack_actions_approve_resumes_ticket(monkeypatch):
    import json as _json
    import time
    from urllib.parse import urlencode

    from slack_sdk.signature import SignatureVerifier

    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")

    created = client.post(
        "/tickets",
        json={"customer_email": "user@example.com", "subject": "hmm", "message": "not sure what"},
    ).json()

    fake_triage = TriageResult(category="general", confidence=0.4, reasoning="unclear")
    with patch("app.graph.classify_ticket", return_value=fake_triage):
        with patch("app.graph.send_escalation"):
            client.post(f"/tickets/{created['ticket_id']}/process")

    slack_payload = _json.dumps(
        {"actions": [{"action_id": "approve_ticket", "value": created["ticket_id"]}]}
    )
    # Sign the EXACT bytes that will be sent - urlencode() first, then sign
    # that string, rather than signing a hand-built approximation of it.
    body = urlencode({"payload": slack_payload})
    timestamp = str(int(time.time()))
    verifier = SignatureVerifier("test-secret")
    signature = verifier.generate_signature(timestamp=timestamp, body=body)

    response = client.post(
        "/slack/actions",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Signature": signature,
            "X-Slack-Request-Timestamp": timestamp,
        },
    )

    assert response.status_code == 200
    assert response.json()["replace_original"] is True
    fetched = client.get(f"/tickets/{created['ticket_id']}")
    assert fetched.json()["status"] == "resolved_by_human"
