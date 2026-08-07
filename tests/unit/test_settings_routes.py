"""Phase 5: settings truthfulness — GET returns real stored literals, PUT persists, no fabricated fields."""

from __future__ import annotations

import os

os.environ.setdefault("CHERENKOV_ENV", "development")

import pytest
from fastapi.testclient import TestClient

from cherenkov.core import settings as settings_mod
from cherenkov.web.api import app
from cherenkov.web.routes import workspace_routes as wr

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def fresh_settings(monkeypatch):
    settings_mod.reset_settings()
    yield
    settings_mod.reset_settings()


def _get() -> dict:
    return client.get("/api/v1/settings").json()


def _put(body: dict) -> dict:
    return client.put("/api/v1/settings", json=body)


def test_get_reflects_real_provider_target_egress(fresh_settings, monkeypatch):
    monkeypatch.setenv("PROVIDER", "localai")
    monkeypatch.setenv("API_URL", "https://staging.example.com")
    monkeypatch.setenv("CHERENKOV_EGRESS", "external")
    payload = _get()
    assert payload["model"] == "localai"
    assert payload["target"] == {"url": "https://staging.example.com"}
    assert payload["security"] == {"egress_policy": "external"}


def test_get_reflects_real_airllm_and_vlm_settings(fresh_settings, monkeypatch):
    monkeypatch.setenv("CHERENKOV_AIRLLM_ENABLED", "true")
    monkeypatch.setenv("CHERENKOV_AIRLLM_MODEL", "Llama-3-70B")
    monkeypatch.setenv("CHERENKOV_VLM_PROVIDER", "ollama")
    monkeypatch.setenv("CHERENKOV_VLM_LOCALAI_MODEL", "llava")
    monkeypatch.setenv("CHERENKOV_OCR_ENABLED", "true")
    payload = _get()
    assert payload["airllm"]["enabled"] is True
    assert payload["airllm"]["model"] == "Llama-3-70B"
    assert payload["vlm"]["provider"] == "ollama"
    assert payload["vlm"]["model"] == "llava"
    assert payload["vlm"]["ocr_enabled"] is True


def test_get_never_fabricates_unbacked_fields(fresh_settings):
    payload = _get()
    for fake in (
        "enable_demo_mode", "execution_budget", "workers",
        "density", "reduced_motion", "auth_secret", "model_tier",
    ):
        assert fake not in payload, f"GET /settings fabricated unbacked field: {fake}"
    assert "engine" not in payload
    assert "ui" not in payload


def test_put_persists_target_url_egress_provider_and_airllm(fresh_settings, monkeypatch):
    written: list[tuple[str, str]] = []

    def fake_write(key: str, value: str) -> None:
        written.append((key, value))

    monkeypatch.setattr(wr, "_write_env_var", fake_write)
    resp = _put({
        "model": "nemoclaw",
        "target": {"url": "https://prod.example.com"},
        "security": {"egress_policy": "blocked"},
        "airllm": {"enabled": True, "model": "DeepSeek-Coder-33B", "compression": "8bit"},
    })
    assert resp.status_code == 200
    assert ("PROVIDER", "nemoclaw") in written
    assert ("API_URL", "https://prod.example.com") in written
    assert ("CHERENKOV_EGRESS", "blocked") in written
    assert ("CHERENKOV_AIRLLM_ENABLED", "true") in written
    assert ("CHERENKOV_AIRLLM_MODEL", "DeepSeek-Coder-33B") in written
    assert ("CHERENKOV_AIRLLM_COMPRESSION", "8bit") in written


def test_put_returns_truthful_updated_payload(fresh_settings, monkeypatch):
    def fake_write(key: str, value: str) -> None:
        pass

    monkeypatch.setattr(wr, "_write_env_var", fake_write)
    resp = _put({
        "model": "openai",
        "target": {"url": "https://prod.example.com"},
        "security": {"egress_policy": "external"},
    })
    body = resp.json()
    assert body["model"] == "openai"
    assert body["target"] == {"url": "https://prod.example.com"}
    assert body["security"] == {"egress_policy": "external"}
    assert "engine" not in body
    assert "ui" not in body
