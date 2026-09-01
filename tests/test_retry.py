from unittest.mock import MagicMock

import pytest

from app.retry import with_retries


class TransientError(Exception):
    pass


class PermanentError(Exception):
    pass


def test_returns_result_on_first_success():
    fn = MagicMock(return_value="ok")
    assert with_retries(fn, (TransientError,)) == "ok"
    assert fn.call_count == 1


def test_retries_transient_then_succeeds():
    fn = MagicMock(side_effect=[TransientError(), "ok"])
    assert with_retries(fn, (TransientError,), base_delay=0.01) == "ok"
    assert fn.call_count == 2


def test_raises_after_exhausting_max_attempts():
    fn = MagicMock(side_effect=TransientError("still failing"))
    with pytest.raises(TransientError):
        with_retries(fn, (TransientError,), max_attempts=3, base_delay=0.01)
    assert fn.call_count == 3


def test_does_not_retry_non_transient_exception():
    fn = MagicMock(side_effect=PermanentError("won't fix itself"))
    with pytest.raises(PermanentError):
        with_retries(fn, (TransientError,), base_delay=0.01)
    assert fn.call_count == 1
