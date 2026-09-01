from unittest.mock import MagicMock, patch

import httpx
import pytest
from groq import APIConnectionError, AuthenticationError

from app.llm import ask


def test_ask_returns_text_from_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")

    fake_message = MagicMock()
    fake_message.content = "hello from groq"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("app.llm.Groq", return_value=fake_client):
        result = ask(system_prompt="be helpful", user_message="hi")

    assert result == "hello from groq"


def test_ask_raises_clear_error_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ask(system_prompt="be helpful", user_message="hi")


def test_ask_retries_transient_error_then_succeeds(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")

    fake_message = MagicMock()
    fake_message.content = "recovered"
    fake_choice = MagicMock()
    fake_choice.message = fake_message
    fake_response = MagicMock()
    fake_response.choices = [fake_choice]

    fake_request = httpx.Request("POST", "https://api.groq.com/v1/chat/completions")
    connection_error = APIConnectionError(request=fake_request)

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = [connection_error, fake_response]

    with patch("app.llm.Groq", return_value=fake_client):
        result = ask(system_prompt="be helpful", user_message="hi")

    assert result == "recovered"
    assert fake_client.chat.completions.create.call_count == 2


def test_ask_does_not_retry_permanent_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")

    fake_request = httpx.Request("POST", "https://api.groq.com/v1/chat/completions")
    fake_http_response = httpx.Response(401, request=fake_request)
    auth_error = AuthenticationError("bad key", response=fake_http_response, body=None)

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = auth_error

    with patch("app.llm.Groq", return_value=fake_client):
        with pytest.raises(AuthenticationError):
            ask(system_prompt="be helpful", user_message="hi")

    assert fake_client.chat.completions.create.call_count == 1
