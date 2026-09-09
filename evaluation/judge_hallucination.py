"""
LLM-as-a-judge: for every technical ticket the Tech Support Agent actually
resolved (real Groq + real Qdrant, no mocks), a second, independent Groq
call grades whether the agent's reply is fully grounded in the source
document it cited, or whether it invented anything not present there.

This is a different check than evaluation/run_evaluation.py's category/
status accuracy - a reply can be sent to the right customer with the right
status and still contain a hallucinated detail. This is what actually
catches that.
"""

import json
import pathlib

from app.agents.tech_support import resolve_technical_ticket
from app.llm import ask
from app.models.ticket import Ticket

KB_DIR = pathlib.Path(__file__).resolve().parent.parent / "knowledge_base"
RESULTS_PATH = pathlib.Path(__file__).resolve().parent / "judge_results.json"

JUDGE_SYSTEM_PROMPT = """You are a strict fact-checker grading a support agent's reply.

You will be given a source document and a reply the agent sent to a customer.
Your only job: does the reply state anything as fact that is not supported by
the source document? Paraphrasing, summarizing, and reasonable inference are
fine. Inventing steps, numbers, policies, or claims not in the document is not.

Respond with ONLY a JSON object in this exact shape, no other text:
{"grounded": true | false, "explanation": "<one short sentence citing the specific unsupported claim, or why it's fine>"}
"""

# Same technical cases the main evaluation uses to resolve tickets, kept
# small and separate here since this script's cost is one extra Groq call
# (the judge) per case on top of the normal pipeline run.
TECHNICAL_CASES = [
    ("Getting a 429 error", "I keep getting a 429 status code when calling your API, what does that mean?"),
    ("App won't open", "The app crashes immediately every time I try to open it after the last update."),
    ("Can't log in", "I'm entering the right password but it keeps saying login failed."),
    ("Forgot my password", "How do I reset my password? I don't see a reset option."),
    ("Data not syncing", "My data isn't syncing between my phone and laptop, what should I check?"),
    ("Setting up 2FA", "How do I turn on two-factor authentication for my account?"),
    ("500 error on checkout", "I get a 500 internal server error every time I try to check out."),
    ("Can't reset password", "The password reset email never arrives, I've tried three times."),
]


def judge_reply(reply: str, source_doc: str) -> dict:
    doc_text = (KB_DIR / f"{source_doc}.md").read_text(encoding="utf-8")
    user_message = f"Source document:\n{doc_text}\n\nAgent's reply to the customer:\n{reply}"
    raw = ask(system_prompt=JUDGE_SYSTEM_PROMPT, user_message=user_message)
    return json.loads(raw)


def main():
    results = []
    for i, (subject, message) in enumerate(TECHNICAL_CASES, start=1):
        ticket = Ticket(
            ticket_id=f"judge-{i}",
            status="triaged",
            created_at="2026-01-01T00:00:00Z",
            customer_email="eval@example.com",
            subject=subject,
            message=message,
            category="technical",
        )
        resolution = resolve_technical_ticket(ticket)

        if resolution.status != "resolved":
            print(f"[{i}/{len(TECHNICAL_CASES)}] SKIPPED - escalated instead of resolving ({subject!r})")
            results.append({"subject": subject, "status": resolution.status, "grounded": None})
            continue

        verdict = judge_reply(resolution.reply, resolution.source_doc)
        results.append({
            "subject": subject,
            "reply": resolution.reply,
            "source_doc": resolution.source_doc,
            "grounded": verdict["grounded"],
            "explanation": verdict["explanation"],
        })
        mark = "GROUNDED" if verdict["grounded"] else "HALLUCINATION FLAGGED"
        print(f"[{i}/{len(TECHNICAL_CASES)}] {mark} - {subject!r}: {verdict['explanation']}")

    judged = [r for r in results if r["grounded"] is not None]
    grounded_count = sum(r["grounded"] for r in judged)

    print("\n" + "=" * 60)
    if judged:
        print(f"Grounding rate: {grounded_count}/{len(judged)} ({grounded_count / len(judged):.0%})")
    skipped = len(results) - len(judged)
    if skipped:
        print(f"{skipped} case(s) escalated before generating a reply - nothing to judge, which is itself the safe outcome.")

    flagged = [r for r in judged if not r["grounded"]]
    if flagged:
        print(f"\n{len(flagged)} reply/replies flagged as ungrounded:")
        for r in flagged:
            print(f"  {r['subject']!r}: {r['explanation']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
