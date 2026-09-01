from typing import Literal

from pydantic import BaseModel

from app.llm import ask
from app.models.ticket import Ticket
from app.rag.search import search

MATCH_THRESHOLD = 0.5

SYSTEM_PROMPT = """You are a technical support assistant replying to a customer.

Use ONLY the information in the provided documentation to answer. Do not
invent steps that are not in the documentation. If the documentation does
not actually answer the customer's question, say plainly that you don't
have enough information and that a team member will follow up.

Keep the reply concise and friendly, written directly to the customer."""


class TechSupportResult(BaseModel):
    status: Literal["resolved", "needs_human"]
    reply: str | None = None
    source_doc: str | None = None
    match_score: float | None = None


def resolve_technical_ticket(ticket: Ticket) -> TechSupportResult:
    query = f"{ticket.subject}\n{ticket.message}"

    try:
        results = search(query, top_k=1)
    except Exception:
        # search()/ask() already retry transient failures internally; if we
        # get here, retries were exhausted or the failure was permanent.
        return TechSupportResult(status="needs_human")

    if not results or results[0]["score"] < MATCH_THRESHOLD:
        return TechSupportResult(
            status="needs_human",
            match_score=results[0]["score"] if results else None,
        )

    top = results[0]
    user_message = (
        f"Customer subject: {ticket.subject}\n"
        f"Customer message: {ticket.message}\n\n"
        f"Documentation:\n{top['text']}"
    )

    try:
        reply = ask(system_prompt=SYSTEM_PROMPT, user_message=user_message)
    except Exception:
        return TechSupportResult(status="needs_human", match_score=top["score"])

    return TechSupportResult(
        status="resolved",
        reply=reply,
        source_doc=top["source"],
        match_score=top["score"],
    )
