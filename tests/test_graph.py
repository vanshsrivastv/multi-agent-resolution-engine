from unittest.mock import patch

from app.agents.billing import BillingResult
from app.agents.tech_support import TechSupportResult
from app.agents.triage import TriageError, TriageResult
from app.graph import route_after_triage, run_pipeline
from app.models.ticket import Ticket


def make_ticket(**overrides) -> Ticket:
    defaults = dict(
        ticket_id="t-1",
        status="received",
        created_at="2026-01-01T00:00:00Z",
        customer_email="user@example.com",
        subject="Test",
        message="Test message",
    )
    defaults.update(overrides)
    return Ticket(**defaults)


def test_route_after_triage_low_confidence_escalates():
    ticket = make_ticket(category="technical", confidence=0.5)
    assert route_after_triage({"ticket": ticket}) == "escalate"


def test_route_after_triage_missing_confidence_escalates():
    ticket = make_ticket(category="technical", confidence=None)
    assert route_after_triage({"ticket": ticket}) == "escalate"


def test_route_after_triage_technical_routes_to_tech_support():
    ticket = make_ticket(category="technical", confidence=0.95)
    assert route_after_triage({"ticket": ticket}) == "tech_support"


def test_route_after_triage_billing_routes_to_billing():
    ticket = make_ticket(category="billing", confidence=0.95)
    assert route_after_triage({"ticket": ticket}) == "billing"


def test_route_after_triage_general_escalates():
    ticket = make_ticket(category="general", confidence=0.95)
    assert route_after_triage({"ticket": ticket}) == "escalate"


def test_pipeline_resolves_technical_ticket():
    ticket = make_ticket(subject="App crashes", message="closes on open", transaction_id=None)
    fake_triage = TriageResult(category="technical", confidence=0.97, reasoning="crash")
    fake_resolution = TechSupportResult(status="resolved", reply="Try restarting.", source_doc="doc1", match_score=0.8)

    with patch("app.graph.classify_ticket", return_value=fake_triage):
        with patch("app.graph.resolve_technical_ticket", return_value=fake_resolution):
            result = run_pipeline(ticket)

    assert result.category == "technical"
    assert result.status == "resolved"
    assert result.reply == "Try restarting."


def test_pipeline_resolves_billing_ticket():
    ticket = make_ticket(subject="Refund", message="charge me back", transaction_id="pay_123")
    fake_triage = TriageResult(category="billing", confidence=0.96, reasoning="refund")
    fake_resolution = BillingResult(status="refunded", reply="Refunded.", refund_id="rfnd_1", amount=1000)

    with patch("app.graph.classify_ticket", return_value=fake_triage):
        with patch("app.graph.resolve_billing_ticket", return_value=fake_resolution):
            result = run_pipeline(ticket)

    assert result.category == "billing"
    assert result.status == "refunded"
    assert result.refund_id == "rfnd_1"


def test_pipeline_escalates_low_confidence_ticket():
    ticket = make_ticket(subject="hmm", message="not sure what")
    fake_triage = TriageResult(category="general", confidence=0.4, reasoning="unclear")

    with patch("app.graph.classify_ticket", return_value=fake_triage):
        result = run_pipeline(ticket)

    assert result.status == "needs_human"
    assert result.reply is None


def test_pipeline_escalates_general_ticket_even_with_high_confidence():
    ticket = make_ticket(subject="Compliment", message="love the app")
    fake_triage = TriageResult(category="general", confidence=0.98, reasoning="feedback")

    with patch("app.graph.classify_ticket", return_value=fake_triage):
        result = run_pipeline(ticket)

    assert result.status == "needs_human"


def test_pipeline_escalates_when_triage_itself_fails():
    ticket = make_ticket()

    with patch("app.graph.classify_ticket", side_effect=TriageError("bad json")):
        result = run_pipeline(ticket)

    assert result.status == "needs_human"
    assert result.category is None
