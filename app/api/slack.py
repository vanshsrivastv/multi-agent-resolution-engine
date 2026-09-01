import json
import os

from fastapi import APIRouter, HTTPException, Request
from slack_sdk.signature import SignatureVerifier

from app import store
from app.graph import resume_pipeline

router = APIRouter()


def _verifier() -> SignatureVerifier:
    secret = os.getenv("SLACK_SIGNING_SECRET")
    if not secret:
        raise RuntimeError("SLACK_SIGNING_SECRET is not set. Add it to your .env file.")
    return SignatureVerifier(secret)


@router.post("/slack/actions")
async def slack_actions(request: Request):
    body = await request.body()

    if not _verifier().is_valid_request(body, request.headers):
        raise HTTPException(status_code=401, detail="invalid Slack signature")

    form = await request.form()
    payload = json.loads(form["payload"])
    action = payload["actions"][0]

    ticket_id = action["value"]
    decision = "approve" if action["action_id"] == "approve_ticket" else "reject"

    ticket = resume_pipeline(ticket_id, decision)
    store.save(ticket)

    # replace_original swaps the message's own content (including removing
    # the buttons) instead of just posting a confirmation alongside them -
    # without it, the buttons stay clickable forever even after resolution.
    return {
        "replace_original": True,
        "text": f"Ticket `{ticket_id}` marked *{ticket.status}*.",
    }
