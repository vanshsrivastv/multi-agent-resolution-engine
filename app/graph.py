from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from app.agents.billing import resolve_billing_ticket
from app.agents.tech_support import resolve_technical_ticket
from app.agents.triage import TriageError, classify_ticket
from app.models.ticket import Ticket
from app.slack_client import send_escalation

CONFIDENCE_THRESHOLD = 0.90

# A ticket in any of these states has already been through the pipeline to
# some conclusion (including "waiting on a human") - /process should not
# re-run it from scratch.
ALREADY_HANDLED_STATUSES = {
    "resolved",
    "refunded",
    "already_refunded",
    "needs_human",
    "resolved_by_human",
    "rejected",
}

# Lives for the lifetime of the running process. A paused ticket's state is
# lost if the server restarts before a human responds - a real deployment
# would use a persistent checkpointer (e.g. Postgres) instead.
_CHECKPOINTER = InMemorySaver(
    serde=JsonPlusSerializer(allowed_msgpack_modules=[("app.models.ticket", "Ticket")])
)


class GraphState(TypedDict):
    ticket: Ticket


def triage_node(state: GraphState) -> dict:
    ticket = state["ticket"]
    try:
        result = classify_ticket(ticket)
    except TriageError:
        # Leave category/confidence as None - route_after_triage sends
        # low/missing confidence to escalate, so this needs no special case.
        return {"ticket": ticket.model_copy(update={"status": "triaged"})}

    updated = ticket.model_copy(
        update={
            "category": result.category,
            "confidence": result.confidence,
            "status": "triaged",
        }
    )
    return {"ticket": updated}


def tech_support_node(state: GraphState) -> dict:
    ticket = state["ticket"]
    result = resolve_technical_ticket(ticket)
    updated = ticket.model_copy(
        update={
            "status": result.status,
            "reply": result.reply,
            "resolved_via": result.source_doc,
            "match_score": result.match_score,
        }
    )
    return {"ticket": updated}


def billing_node(state: GraphState) -> dict:
    ticket = state["ticket"]
    result = resolve_billing_ticket(ticket)
    updated = ticket.model_copy(
        update={
            "status": result.status,
            "reply": result.reply,
            "refund_id": result.refund_id,
            "refund_amount": result.amount,
        }
    )
    return {"ticket": updated}


def _escalation_reason(ticket: Ticket) -> str:
    if ticket.category is None:
        return "triage could not classify this ticket"
    if ticket.confidence is not None and ticket.confidence < CONFIDENCE_THRESHOLD:
        return f"triage confidence too low ({ticket.confidence:.0%})"
    if ticket.category == "general":
        return "no automated agent handles general tickets"
    return "the assigned agent could not resolve this automatically"


def escalate_node(state: GraphState) -> dict:
    ticket = state["ticket"]
    reason = _escalation_reason(ticket)

    try:
        send_escalation(ticket_id=ticket.ticket_id, subject=ticket.subject, category=ticket.category, reason=reason)
    except Exception:
        # A failed Slack notification must not stop the ticket from being
        # correctly marked as needing a human - it just means whoever is
        # reviewing needs_human tickets won't hear about it via Slack.
        pass

    decision = interrupt({"ticket_id": ticket.ticket_id, "reason": reason})

    final_status = "resolved_by_human" if decision == "approve" else "rejected"
    return {"ticket": ticket.model_copy(update={"status": final_status})}


def route_after_triage(state: GraphState) -> str:
    ticket = state["ticket"]
    if ticket.confidence is None or ticket.confidence < CONFIDENCE_THRESHOLD:
        return "escalate"
    if ticket.category == "technical":
        return "tech_support"
    if ticket.category == "billing":
        return "billing"
    return "escalate"


def route_after_resolution(state: GraphState) -> str:
    return "escalate" if state["ticket"].status == "needs_human" else "end"


def build_graph():
    builder = StateGraph(GraphState)
    builder.add_node("triage", triage_node)
    builder.add_node("tech_support", tech_support_node)
    builder.add_node("billing", billing_node)
    builder.add_node("escalate", escalate_node)

    builder.set_entry_point("triage")
    builder.add_conditional_edges(
        "triage",
        route_after_triage,
        {"tech_support": "tech_support", "billing": "billing", "escalate": "escalate"},
    )
    builder.add_conditional_edges("tech_support", route_after_resolution, {"escalate": "escalate", "end": END})
    builder.add_conditional_edges("billing", route_after_resolution, {"escalate": "escalate", "end": END})
    builder.add_edge("escalate", END)

    return builder.compile(checkpointer=_CHECKPOINTER)


def run_pipeline(ticket: Ticket) -> Ticket:
    graph = build_graph()
    config = {"configurable": {"thread_id": ticket.ticket_id}}
    result = graph.invoke({"ticket": ticket}, config=config)

    if "__interrupt__" in result:
        return result["ticket"].model_copy(update={"status": "needs_human"})
    return result["ticket"]


def resume_pipeline(ticket_id: str, decision: str) -> Ticket:
    graph = build_graph()
    config = {"configurable": {"thread_id": ticket_id}}
    result = graph.invoke(Command(resume=decision), config=config)
    return result["ticket"]
