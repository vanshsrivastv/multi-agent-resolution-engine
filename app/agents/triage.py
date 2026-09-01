import json
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.llm import ask
from app.models.ticket import Ticket
from app.retry import with_retries

Category = Literal["billing", "technical", "general"]

SYSTEM_PROMPT = """You classify customer support tickets into exactly one category.

Categories:
- billing: refunds, charges, payments, subscriptions, invoices
- technical: errors, bugs, features not working, login issues
- general: anything else, including vague or unclear requests

Respond with ONLY a JSON object in this exact shape, no other text:
{"category": "billing" | "technical" | "general", "confidence": <number 0 to 1>, "reasoning": "<one short sentence>"}
"""


class TriageResult(BaseModel):
    category: Category
    confidence: float
    reasoning: str


class TriageError(Exception):
    """The LLM's response could not be parsed into a valid TriageResult."""


def _ask_and_parse(ticket: Ticket) -> TriageResult:
    user_message = f"Subject: {ticket.subject}\n\nMessage: {ticket.message}"
    raw = ask(system_prompt=SYSTEM_PROMPT, user_message=user_message)

    try:
        data = json.loads(raw)
        return TriageResult(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise TriageError(f"could not parse triage response: {raw!r}") from e


def classify_ticket(ticket: Ticket) -> TriageResult:
    # A malformed response is worth retrying (a fresh sample may well
    # parse fine) - this is separate from ask()'s own network-level
    # retries, which happen underneath this on every attempt too.
    return with_retries(lambda: _ask_and_parse(ticket), (TriageError,))
