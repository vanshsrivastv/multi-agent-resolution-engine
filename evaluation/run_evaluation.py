"""
Runs the ground-truth dataset (evaluation/dataset.json) through the real
pipeline (real Groq, Qdrant, Razorpay - no mocks) and reports actual
measured accuracy numbers, not a claimed one.

Requires: Qdrant running (docker), .env fully configured (Groq + Razorpay).
Does NOT create or refund any real payment - billing cases only read
existing, already-known-state transactions, so this is safe to rerun.
"""

import json
import pathlib
import time
from unittest.mock import patch

from app.graph import run_pipeline
from app.models.ticket import Ticket, TicketCreate

# Most cases here are designed to hit needs_human, which normally sends a
# real Slack notification. Evaluation is testing classification/routing
# correctness (Groq, Qdrant, Razorpay stay real) - it should not spam a
# real Slack channel with ~20 notifications every run, so this one
# notification side-effect is mocked out.
_SLACK_PATCH = patch("app.graph.send_escalation")

DATASET_PATH = pathlib.Path(__file__).resolve().parent / "dataset.json"
RESULTS_PATH = pathlib.Path(__file__).resolve().parent / "results.json"


def load_dataset() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def run_one(case: dict) -> dict:
    ticket = Ticket.from_create(
        TicketCreate(
            customer_email="eval@example.com",
            subject=case["subject"],
            message=case["message"],
            transaction_id=case.get("transaction_id"),
        )
    )

    start = time.time()
    result = run_pipeline(ticket)
    latency = time.time() - start

    expected_category = case.get("expected_category")
    category_correct = expected_category is None or result.category == expected_category
    status_correct = result.status == case["expected_status"]

    return {
        "id": case["id"],
        "subject": case["subject"],
        "expected_category": expected_category,
        "actual_category": result.category,
        "confidence": result.confidence,
        "expected_status": case["expected_status"],
        "actual_status": result.status,
        "category_correct": category_correct,
        "status_correct": status_correct,
        "latency_seconds": round(latency, 2),
    }


def main():
    dataset = load_dataset()
    results = []

    with _SLACK_PATCH:
        for i, case in enumerate(dataset, start=1):
            print(f"[{i}/{len(dataset)}] {case['id']}: {case['subject']!r}...", end=" ", flush=True)
            result = run_one(case)
            status_mark = "OK" if result["status_correct"] else "FAIL"
            print(f"{result['actual_status']} ({status_mark})")
            results.append(result)

    total = len(results)
    status_correct_count = sum(r["status_correct"] for r in results)

    category_checked = [r for r in results if r["expected_category"] is not None]
    category_correct_count = sum(r["category_correct"] for r in category_checked)

    avg_latency = sum(r["latency_seconds"] for r in results) / total

    print("\n" + "=" * 60)
    print(f"Status accuracy:   {status_correct_count}/{total} ({status_correct_count / total:.0%})")
    if category_checked:
        print(
            f"Category accuracy: {category_correct_count}/{len(category_checked)} "
            f"({category_correct_count / len(category_checked):.0%}) "
            f"[{total - len(category_checked)} cases had no expected category - ambiguous by design]"
        )
    print(f"Average latency:   {avg_latency:.2f}s per ticket")

    failures = [r for r in results if not r["status_correct"] or not r["category_correct"]]
    if failures:
        print(f"\n{len(failures)} case(s) did not match expectations:")
        for r in failures:
            print(
                f"  {r['id']}: expected category={r['expected_category']!r} status={r['expected_status']!r}, "
                f"got category={r['actual_category']!r} status={r['actual_status']!r} "
                f"(confidence={r['confidence']})"
            )
    else:
        print("\nAll cases matched expectations.")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
