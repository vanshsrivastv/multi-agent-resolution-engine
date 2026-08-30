from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_fetch_ticket():
    response = client.post(
        "/tickets",
        json={
            "customer_email": "user@example.com",
            "subject": "Can't log in",
            "message": "I get an error every time I try to sign in.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert "ticket_id" in body

    fetched = client.get(f"/tickets/{body['ticket_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["subject"] == "Can't log in"


def test_get_unknown_ticket_returns_404():
    response = client.get("/tickets/does-not-exist")
    assert response.status_code == 404


def test_create_ticket_missing_field_returns_422():
    response = client.post(
        "/tickets",
        json={"customer_email": "user@example.com", "subject": "Missing message"},
    )
    assert response.status_code == 422


def test_create_ticket_invalid_email_returns_422():
    response = client.post(
        "/tickets",
        json={
            "customer_email": "not-an-email",
            "subject": "Test",
            "message": "Test message",
        },
    )
    assert response.status_code == 422
