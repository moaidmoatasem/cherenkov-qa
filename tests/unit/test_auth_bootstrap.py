"""Regression tests: first-user creation requires the bootstrap key."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cherenkov.core import settings as settings_mod
from cherenkov.web.auth import store as store_mod
from cherenkov.web.auth.routes import router


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CHERENKOV_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setenv("CHERENKOV_AUTH_ENABLED", "true")
    monkeypatch.setenv("CHERENKOV_BOOTSTRAP_KEY", "bootstrap-secret")
    monkeypatch.setattr(store_mod, "_store", None)
    settings_mod.reset_settings()
    app = FastAPI()
    app.include_router(router)
    yield TestClient(app)
    monkeypatch.setattr(store_mod, "_store", None)
    settings_mod.reset_settings()


_BODY = {"username": "admin", "password": "correct horse", "role": "admin"}


def test_bootstrap_requires_key(client):
    assert client.post("/api/v1/auth/users", json=_BODY).status_code == 403


def test_bootstrap_rejects_wrong_key(client):
    resp = client.post("/api/v1/auth/users", json=_BODY, headers={"X-Bootstrap-Key": "wrong"})
    assert resp.status_code == 403


def test_bootstrap_accepts_correct_key_once(client):
    headers = {"X-Bootstrap-Key": "bootstrap-secret"}
    assert client.post("/api/v1/auth/users", json=_BODY, headers=headers).status_code == 201
    # Once a user exists the bootstrap path closes: admin JWT is required.
    second = client.post(
        "/api/v1/auth/users",
        json={"username": "second", "password": "another pass", "role": "admin"},
        headers=headers,
    )
    assert second.status_code == 403
