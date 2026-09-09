"""
50 hand-written, unambiguously billing-shaped messages, run through the
real Triage Agent (real Groq, no mocks). Reports what fraction actually
landed in the billing category with confidence above the routing threshold
(0.90) - i.e. what fraction would have actually reached the Billing Agent
in production, not just "classified as billing" on paper.
"""

import json
import pathlib

from app.agents.triage import classify_ticket
from app.graph import CONFIDENCE_THRESHOLD
from app.models.ticket import Ticket

RESULTS_PATH = pathlib.Path(__file__).resolve().parent / "billing_routing_results.json"

MESSAGES = [
    "I was charged twice for the same order, please refund the extra charge.",
    "Where is my refund? It's been a week since I asked for one.",
    "I want to cancel my subscription and get my money back.",
    "You charged my card but I never received the product.",
    "Please refund this transaction, I ordered by mistake.",
    "My invoice shows the wrong amount, can you fix the billing?",
    "I need a receipt for my last payment.",
    "The subscription renewed automatically and I want a refund.",
    "I was billed for a plan I already cancelled.",
    "Can you refund my payment from last Tuesday?",
    "There's an unauthorized charge on my card from your company.",
    "I paid but the order still shows as unpaid, what happened to my money?",
    "I'd like to dispute a charge on my account.",
    "My credit card was charged the wrong amount.",
    "Requesting a refund for a duplicate transaction.",
    "I cancelled within the refund window, please process my refund.",
    "Why was I charged a late fee, I paid on time?",
    "I need my payment reversed, I was double billed.",
    "Please issue a refund, the item never shipped.",
    "This charge on my statement doesn't match what I agreed to pay.",
    "I want my subscription fee back, I never used the service.",
    "Refund request: order was cancelled before it shipped.",
    "My payment failed but money was still deducted from my account.",
    "I was charged in the wrong currency, please correct and refund the difference.",
    "Can you check why my refund hasn't shown up in my bank account yet?",
    "I'm being billed monthly but I only signed up for a one-time purchase.",
    "Please refund my last payment, I switched to a different plan.",
    "There's a billing error - I was charged $50 instead of $5.",
    "I want to know why I was charged after I cancelled my account.",
    "Refund needed: the coupon code didn't apply and I overpaid.",
    "My card statement shows two charges for one order, please refund one.",
    "I paid for premium but got downgraded, I want a partial refund.",
    "Please reverse the charge, this was a fraudulent transaction on my card.",
    "I need a refund because the payment was made in error.",
    "Why do I see a pending charge that I never authorized?",
    "Requesting a refund for the annual plan I no longer want.",
    "I was charged after my free trial should have ended without payment.",
    "Please refund the difference, I was overcharged on shipping.",
    "My payment method was charged twice due to a checkout glitch.",
    "I cancelled my order immediately, please refund the full amount.",
    "The refund I was promised hasn't reached my account after 10 days.",
    "I want a refund for a payment made to the wrong account.",
    "Billing question: why is my card being charged more than my listed plan price?",
    "I need to get a refund processed for an accidental purchase.",
    "This transaction on my card statement is not something I made, please refund it.",
    "I paid for a service that was never activated, please refund me.",
    "Can you refund me since I was charged before my trial ended?",
    "I want a chargeback reversed and a refund issued to my original payment method.",
    "Please refund my last invoice, I was billed for an add-on I never selected.",
    "I need help getting my money back for a payment that failed to go through correctly.",
]


def main():
    results = []
    for i, message in enumerate(MESSAGES, start=1):
        ticket = Ticket(
            ticket_id=f"routing-{i}",
            status="received",
            created_at="2026-01-01T00:00:00Z",
            customer_email="eval@example.com",
            subject="Billing",
            message=message,
        )
        result = classify_ticket(ticket)
        would_route_to_billing = result.category == "billing" and result.confidence >= CONFIDENCE_THRESHOLD
        results.append({
            "message": message,
            "category": result.category,
            "confidence": result.confidence,
            "would_route_to_billing": would_route_to_billing,
        })
        mark = "OK" if would_route_to_billing else "MISROUTED"
        print(f"[{i}/{len(MESSAGES)}] {mark} - category={result.category} confidence={result.confidence:.2f}")

    correct = sum(r["would_route_to_billing"] for r in results)
    print("\n" + "=" * 60)
    print(f"Billing routing precision: {correct}/{len(results)} ({correct / len(results):.0%})")

    misrouted = [r for r in results if not r["would_route_to_billing"]]
    if misrouted:
        print(f"\n{len(misrouted)} message(s) did not route to billing:")
        for r in misrouted:
            print(f"  {r['message']!r} -> category={r['category']} confidence={r['confidence']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
