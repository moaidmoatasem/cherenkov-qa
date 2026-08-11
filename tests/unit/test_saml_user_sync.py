# tests/unit/test_saml_user_sync.py
"""Unit test for SAML callback user synchronization.

Ensures that when a user logs in via SAML and their role or organization_id differs
from the stored values, the `update_user` method on the `UserStore` is invoked and
the returned token response reflects the updated attributes.
"""

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from cherenkov.enterprise.saml import SAMLAssertion, SAMLServiceProvider
from cherenkov.web.api import app  # FastAPI app definition
from cherenkov.web.auth.models import Role
from cherenkov.web.auth.store import UserStore

client = TestClient(app)

# The callback keys the user off `assertion.email` (routes.py: `username = assertion.email`),
# not off `name_id` — the stored user must therefore be created under the email.
SSO_USERNAME = "test@example.com"


@pytest.fixture()
def mock_sp(monkeypatch):
    """Replace the real SAMLServiceProvider with a mock that returns a crafted assertion."""
    mock_sp_instance = mock.create_autospec(SAMLServiceProvider, instance=True)
    # Build an assertion with known values
    assertion = SAMLAssertion(
        name_id="test-user",
        email=SSO_USERNAME,
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


def test_saml_callback_syncs_user(monkeypatch, mock_sp, tmp_path):
    # Back the store with a throwaway on-disk DB. `:memory:` cannot be used here:
    # UserStore._connect() calls `self._path.parent.mkdir(...)`, so the path must be a real Path.
    store = UserStore(tmp_path / "auth.db")
    # Create the user with attributes that differ from what the IdP will assert
    store.create(SSO_USERNAME, password="pwd", role=Role.viewer, organization_id="old-org")
    # Patch the global store getter to return our custom store
    monkeypatch.setattr("cherenkov.web.auth.routes.get_user_store", lambda: store)

    # Spy on update_user while keeping the real behaviour (stdlib mock has no `spy` helper)
    with mock.patch.object(store, "update_user", wraps=store.update_user) as spy:
        response = client.post(
            "/api/v1/auth/saml/callback",
            data={"SAMLResponse": "dummy", "RelayState": ""},
        )

    assert response.status_code == 200
    payload = response.json()
    # The token response should now carry the updated role and organization_id
    assert payload["role"] == "admin"
    assert payload["organization_id"] == "org-123"
    # Verify that update_user was called exactly once with the IdP-asserted values
    spy.assert_called_once_with(SSO_USERNAME, role=Role.admin, organization_id="org-123")


def test_saml_callback_does_not_update_when_attributes_match(monkeypatch, mock_sp, tmp_path):
    """No drift means no write — the sync path must not fire on every login."""
    store = UserStore(tmp_path / "auth.db")
    store.create(SSO_USERNAME, password="pwd", role=Role.admin, organization_id="org-123")
    monkeypatch.setattr("cherenkov.web.auth.routes.get_user_store", lambda: store)

    with mock.patch.object(store, "update_user", wraps=store.update_user) as spy:
        response = client.post(
            "/api/v1/auth/saml/callback",
            data={"SAMLResponse": "dummy", "RelayState": ""},
        )

    assert response.status_code == 200
    spy.assert_not_called()
