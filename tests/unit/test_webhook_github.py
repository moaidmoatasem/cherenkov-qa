import pytest
from fastapi.testclient import TestClient
from cherenkov.web.api import app

client = TestClient(app)

def test_github_webhook_ping():
    # Simulate a GitHub ping event
    response = client.post(
        "/api/v1/webhooks/github/events",
        headers={"X-GitHub-Event": "ping"},
        json={"zen": "Non-blocking is better than blocking."}
    )
    # The current implementation returns 200 for missing signature to not break while migrating
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
