# tests/unit/test_saml_user_sync.py
"""Unit test for SAML callback user synchronization.
Ensures that when a user logs in via SAML and their role or organization_id differs
from the stored values, the `update_user` method on the `UserStore` is invoked and
the returned JWT reflects the updated attributes.
"""

import json
from unittest import mock
import pytest
from fastapi.testclient import TestClient

from cherenkov.web.api import app  # FastAPI app definition
from cherenkov.web.auth.store import UserStore
from cherenkov.enterprise.saml import SAMLAssertion, SAMLServiceProvider

client = TestClient(app)

@pytest.fixture()
def mock_sp(monkeypatch):
    """Replace the real SAMLServiceProvider with a mock that returns a crafted assertion."""
    mock_sp_instance = mock.create_autospec(SAMLServiceProvider, instance=True)
    # Build an assertion with known values
    assertion = SAMLAssertion(
        name_id="test-user",
        email="test@example.com",
        attributes={
            "organization_id": ["org-123"],
            "role": ["admin"],
        },
    )
    mock_sp_instance.is_enabled.return_value = True
    mock_sp_instance.process_response.return_value = assertion
    # Patch the constructor to return our mock instance
    monkeypatch.setattr("cherenkov.web.auth.routes.SAMLServiceProvider", lambda: mock_sp_instance)
    return mock_sp_instance

def test_saml_callback_syncs_user(monkeypatch, mock_sp):
    # Use an in‑memory SQLite DB to avoid polluting the real DB
    monkeypatch.setattr("cherenkov.web.auth.store._db_path", lambda: ":memory:")
    # Ensure the singleton is reset
    monkeypatch.setattr("cherenkov.web.auth.store._store", None)
    # Initialise a fresh store
    store = UserStore()
    # Create a user with mismatched attributes
    store.create("test-user", password="pwd", role="viewer", organization_id="old-org")
    # Patch the global store getter to return our custom store
    monkeypatch.setattr("cherenkov.web.auth.routes.get_user_store", lambda: store)
    # Spy on update_user
    spy = mock.spy(store, "update_user")

    # Perform the SAML callback POST request
    response = client.post(
        "/api/v1/auth/saml/callback",
        data={"SAMLResponse": "dummy", "RelayState": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    # The JWT payload should now contain the updated role and organization_id
    assert payload["role"] == "admin"
    assert payload["organization_id"] == "org-123"
    # Verify that update_user was called exactly once with the new values
    spy.assert_called_once_with("test-user", role=mock.ANY, organization_id=mock.ANY)
