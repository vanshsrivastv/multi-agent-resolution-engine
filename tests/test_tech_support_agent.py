from unittest.mock import patch

from app.agents.tech_support import resolve_technical_ticket
from app.models.ticket import Ticket


def make_ticket(subject="App crashes", message="It closes right after opening") -> Ticket:
    return Ticket(
        ticket_id="t-1",
        status="triaged",
        created_at="2026-01-01T00:00:00Z",
        customer_email="user@example.com",
        subject=subject,
        message=message,
        category="technical",
    )


def test_resolves_when_match_is_strong():
    fake_results = [{"source": "app_crash_on_startup", "text": "restart the device", "score": 0.8}]
    with patch("app.agents.tech_support.search", return_value=fake_results):
        with patch("app.agents.tech_support.ask", return_value="Try restarting your device."):
            result = resolve_technical_ticket(make_ticket())

    assert result.status == "resolved"
    assert result.reply == "Try restarting your device."
    assert result.source_doc == "app_crash_on_startup"


def test_needs_human_when_match_is_weak():
    fake_results = [{"source": "unrelated_doc", "text": "...", "score": 0.2}]
    with patch("app.agents.tech_support.search", return_value=fake_results):
        result = resolve_technical_ticket(make_ticket())

    assert result.status == "needs_human"
    assert result.reply is None


def test_needs_human_when_no_results():
    with patch("app.agents.tech_support.search", return_value=[]):
        result = resolve_technical_ticket(make_ticket())

    assert result.status == "needs_human"
    assert result.match_score is None
