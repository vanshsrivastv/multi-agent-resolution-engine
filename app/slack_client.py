import os

from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()


def _client() -> WebClient:
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not set. Add it to your .env file.")
    return WebClient(token=token)


def send_escalation(ticket_id: str, subject: str, category: str | None, reason: str) -> None:
    channel = os.getenv("SLACK_CHANNEL")
    if not channel:
        raise RuntimeError("SLACK_CHANNEL is not set. Add it to your .env file.")

    _client().chat_postMessage(
        channel=channel,
        text=f"Ticket needs review: {subject}",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Ticket needs human review*\n"
                        f"*Subject:* {subject}\n"
                        f"*Category:* {category or 'unknown'}\n"
                        f"*Reason:* {reason}\n"
                        f"*Ticket ID:* `{ticket_id}`"
                    ),
                },
            },
            {
                "type": "actions",
                "block_id": f"ticket_actions_{ticket_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "action_id": "approve_ticket",
                        "value": ticket_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "action_id": "reject_ticket",
                        "value": ticket_id,
                    },
                ],
            },
        ],
    )
