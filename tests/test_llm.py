from unittest.mock import MagicMock, patch

import pytest

from app.llm import ask


def test_ask_returns_text_from_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

    fake_text_block = MagicMock()
    fake_text_block.text = "hello from claude"
    fake_response = MagicMock()
    fake_response.content = [fake_text_block]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    with patch("app.llm.Anthropic", return_value=fake_client):
        result = ask(system_prompt="be helpful", user_message="hi")

    assert result == "hello from claude"


def test_ask_raises_clear_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ask(system_prompt="be helpful", user_message="hi")
