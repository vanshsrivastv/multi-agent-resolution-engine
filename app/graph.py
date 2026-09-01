from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.billing import resolve_billing_ticket
from app.agents.tech_support import resolve_technical_ticket
from app.agents.triage import TriageError, classify_ticket
from app.models.ticket import Ticket

CONFIDENCE_THRESHOLD = 0.90


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


def escalate_node(state: GraphState) -> dict:
    updated = state["ticket"].model_copy(update={"status": "needs_human"})
    return {"ticket": updated}


def route_after_triage(state: GraphState) -> str:
    ticket = state["ticket"]
    if ticket.confidence is None or ticket.confidence < CONFIDENCE_THRESHOLD:
        return "escalate"
    if ticket.category == "technical":
        return "tech_support"
    if ticket.category == "billing":
        return "billing"
    return "escalate"


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
    builder.add_edge("tech_support", END)
    builder.add_edge("billing", END)
    builder.add_edge("escalate", END)

    return builder.compile()


def run_pipeline(ticket: Ticket) -> Ticket:
    graph = build_graph()
    final_state = graph.invoke({"ticket": ticket})
    return final_state["ticket"]
