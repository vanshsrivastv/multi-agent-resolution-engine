import os

import razorpay
from dotenv import load_dotenv

load_dotenv()


def _client() -> razorpay.Client:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise RuntimeError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must both be set. Add them to your .env file."
        )
    return razorpay.Client(auth=(key_id, key_secret))


def create_order(amount: int, currency: str = "INR") -> str:
    order = _client().order.create(data={"amount": amount, "currency": currency})
    return order["id"]


def get_order(order_id: str) -> dict:
    order = _client().order.fetch(order_id)
    return {
        "id": order["id"],
        "status": order["status"],
        "amount": order["amount"],
        "currency": order["currency"],
    }


def get_payment(payment_id: str) -> dict:
    payment = _client().payment.fetch(payment_id)
    return {
        "id": payment["id"],
        "status": payment["status"],
        "amount": payment["amount"],
        "currency": payment["currency"],
    }


def refund_payment(payment_id: str) -> dict:
    refund = _client().payment.refund(payment_id, {})
    return {"id": refund["id"], "status": refund["status"]}


def create_payment_link(amount: int, description: str, currency: str = "INR") -> str:
    link = _client().payment_link.create(
        data={"amount": amount, "currency": currency, "description": description}
    )
    return link["short_url"]
