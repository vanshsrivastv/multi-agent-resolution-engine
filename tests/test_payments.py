from unittest.mock import MagicMock, patch

import pytest

from app.payments import create_order, get_order, get_payment, refund_payment


def test_create_order_returns_id(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_fake")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "fake_secret")

    fake_client = MagicMock()
    fake_client.order.create.return_value = {"id": "order_123"}

    with patch("app.payments.razorpay.Client", return_value=fake_client):
        result = create_order(amount=100000)

    assert result == "order_123"


def test_get_order_returns_status(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_fake")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "fake_secret")

    fake_client = MagicMock()
    fake_client.order.fetch.return_value = {
        "id": "order_123",
        "status": "created",
        "amount": 100000,
        "currency": "INR",
    }

    with patch("app.payments.razorpay.Client", return_value=fake_client):
        result = get_order("order_123")

    assert result == {"id": "order_123", "status": "created", "amount": 100000, "currency": "INR"}


def test_get_payment_returns_status(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_fake")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "fake_secret")

    fake_client = MagicMock()
    fake_client.payment.fetch.return_value = {
        "id": "pay_123",
        "status": "captured",
        "amount": 100000,
        "currency": "INR",
    }

    with patch("app.payments.razorpay.Client", return_value=fake_client):
        result = get_payment("pay_123")

    assert result == {"id": "pay_123", "status": "captured", "amount": 100000, "currency": "INR"}


def test_refund_payment_returns_status(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_fake")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "fake_secret")

    fake_client = MagicMock()
    fake_client.payment.fetch.return_value = {"id": "pay_123", "amount": 100000}
    fake_client.payment.refund.return_value = {"id": "rfnd_123", "status": "processed"}

    with patch("app.payments.razorpay.Client", return_value=fake_client):
        result = refund_payment("pay_123")

    fake_client.payment.refund.assert_called_once_with("pay_123", {"amount": 100000})
    assert result == {"id": "rfnd_123", "status": "processed"}


def test_raises_clear_error_when_key_missing(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="RAZORPAY_KEY_ID"):
        create_order(amount=100000)
