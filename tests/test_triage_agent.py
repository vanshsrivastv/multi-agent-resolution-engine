from unittest.mock import patch

import pytest

from app.agents.triage import TriageError, classify_ticket
from app.models.ticket import Ticket


def make_ticket(subject="Refund request", message="I want my money back") -> Ticket:
    return Ticket(
        ticket_id="t-1",
        status="received",
        created_at="2026-01-01T00:00:00Z",
        customer_email="user@example.com",
        subject=subject,
        message=message,
    )


def test_classify_ticket_parses_valid_response():
    fake_raw = '{"category": "billing", "confidence": 0.95, "reasoning": "mentions refund"}'
    with patch("app.agents.triage.ask", return_value=fake_raw):
        result = classify_ticket(make_ticket())

    assert result.category == "billing"
    assert result.confidence == 0.95


def test_classify_ticket_raises_on_malformed_json():
    with patch("app.agents.triage.ask", return_value="not json at all"):
        with pytest.raises(TriageError):
            classify_ticket(make_ticket())


def test_classify_ticket_raises_on_invalid_category():
    fake_raw = '{"category": "shipping", "confidence": 0.9, "reasoning": "n/a"}'
    with patch("app.agents.triage.ask", return_value=fake_raw):
        with pytest.raises(TriageError):
            classify_ticket(make_ticket())
