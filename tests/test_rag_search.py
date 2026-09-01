from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.http.exceptions import ResponseHandlingException

from app.rag.search import search


def _fake_point(source="doc1", text="some text", score=0.8):
    point = MagicMock()
    point.payload = {"source": source, "text": text}
    point.score = score
    return point


def test_search_returns_results_on_success():
    fake_client = MagicMock()
    fake_client.query_points.return_value.points = [_fake_point()]

    with patch("app.rag.search.get_client", return_value=fake_client):
        with patch("app.rag.search.embed", return_value=[[0.1, 0.2]]):
            results = search("some query")

    assert results[0]["source"] == "doc1"


def test_search_retries_transient_connection_error_then_succeeds():
    fake_client = MagicMock()
    connection_error = ResponseHandlingException(ConnectionError("refused"))
    fake_success = MagicMock()
    fake_success.points = [_fake_point()]
    fake_client.query_points.side_effect = [connection_error, fake_success]

    with patch("app.rag.search.get_client", return_value=fake_client):
        with patch("app.rag.search.embed", return_value=[[0.1, 0.2]]):
            results = search("some query")

    assert results[0]["source"] == "doc1"
    assert fake_client.query_points.call_count == 2


def test_search_does_not_retry_unrelated_errors():
    fake_client = MagicMock()
    fake_client.query_points.side_effect = ValueError("unexpected")

    with patch("app.rag.search.get_client", return_value=fake_client):
        with patch("app.rag.search.embed", return_value=[[0.1, 0.2]]):
            with pytest.raises(ValueError):
                search("some query")

    assert fake_client.query_points.call_count == 1
