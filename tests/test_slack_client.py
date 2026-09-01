from unittest.mock import MagicMock, patch

import pytest

from app.slack_client import send_escalation


def test_send_escalation_posts_message_with_buttons(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    monkeypatch.setenv("SLACK_CHANNEL", "#support-escalations")

    fake_client = MagicMock()
    with patch("app.slack_client.WebClient", return_value=fake_client):
        send_escalation(ticket_id="t-1", subject="App crashes", category="technical", reason="no doc match")

    fake_client.chat_postMessage.assert_called_once()
    call_kwargs = fake_client.chat_postMessage.call_args.kwargs
    assert call_kwargs["channel"] == "#support-escalations"

    actions_block = call_kwargs["blocks"][1]
    action_ids = [el["action_id"] for el in actions_block["elements"]]
    values = [el["value"] for el in actions_block["elements"]]
    assert "approve_ticket" in action_ids
    assert "reject_ticket" in action_ids
    assert values == ["t-1", "t-1"]


def test_raises_clear_error_when_token_missing(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.setenv("SLACK_CHANNEL", "#support-escalations")

    with pytest.raises(RuntimeError, match="SLACK_BOT_TOKEN"):
        send_escalation(ticket_id="t-1", subject="x", category=None, reason="y")


def test_raises_clear_error_when_channel_missing(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    monkeypatch.delenv("SLACK_CHANNEL", raising=False)

    with pytest.raises(RuntimeError, match="SLACK_CHANNEL"):
        send_escalation(ticket_id="t-1", subject="x", category=None, reason="y")
