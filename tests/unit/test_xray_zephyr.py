"""
tests/unit/test_xray_zephyr.py — unit tests for Xray (#450) and Zephyr (#451) adapters.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.adapters.xray_client import (
    XrayClient,
    XrayCloudConfig,
    XrayServerConfig,
    CHERENKOV_TO_XRAY,
)
from cherenkov.adapters.zephyr_client import (
    ZephyrClient,
    ZephyrConfig,
    CHERENKOV_TO_ZEPHYR,
)


# ── Verdict mapping ────────────────────────────────────────────────────────────


def test_xray_verdict_mapping():
    assert CHERENKOV_TO_XRAY["PASS"] == "PASSED"
    assert CHERENKOV_TO_XRAY["FAIL"] == "FAILED"
    assert CHERENKOV_TO_XRAY["DRIFT"] == "FAILED"
    assert CHERENKOV_TO_XRAY["SKIP"] == "ABORTED"
    assert CHERENKOV_TO_XRAY["ERROR"] == "ABORTED"


def test_zephyr_verdict_mapping():
    assert CHERENKOV_TO_ZEPHYR["PASS"] == "Pass"
    assert CHERENKOV_TO_ZEPHYR["FAIL"] == "Fail"
    assert CHERENKOV_TO_ZEPHYR["DRIFT"] == "Fail"
    assert CHERENKOV_TO_ZEPHYR["SKIP"] == "Not Executed"
    assert CHERENKOV_TO_ZEPHYR["ERROR"] == "Blocked"


# ── from_env ───────────────────────────────────────────────────────────────────


def test_xray_from_env_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        assert XrayClient.from_env() is None


def test_xray_from_env_cloud(monkeypatch):
    monkeypatch.setenv("CHERENKOV_XRAY_CLIENT_ID", "cid")
    monkeypatch.setenv("CHERENKOV_XRAY_CLIENT_SECRET", "csec")
    client = XrayClient.from_env()
    assert client is not None
    assert isinstance(client.config, XrayCloudConfig)


def test_xray_from_env_server(monkeypatch):
    monkeypatch.setenv("CHERENKOV_XRAY_SERVER_URL", "https://jira.company.com")
    monkeypatch.setenv("CHERENKOV_XRAY_SERVER_TOKEN", "tok")
    monkeypatch.setenv("CHERENKOV_XRAY_PROJECT_KEY", "QA")
    # Clear cloud creds
    os.environ.pop("CHERENKOV_XRAY_CLIENT_ID", None)
    os.environ.pop("CHERENKOV_XRAY_CLIENT_SECRET", None)
    client = XrayClient.from_env()
    assert client is not None
    assert isinstance(client.config, XrayServerConfig)
    assert client.config.project_key == "QA"


def test_zephyr_from_env_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        assert ZephyrClient.from_env() is None


def test_zephyr_from_env_configured(monkeypatch):
    monkeypatch.setenv("CHERENKOV_ZEPHYR_TOKEN", "ztok")
    monkeypatch.setenv("CHERENKOV_ZEPHYR_PROJECT_KEY", "QA")
    client = ZephyrClient.from_env()
    assert client is not None
    assert client.config.project_key == "QA"


# ── Payload building ───────────────────────────────────────────────────────────


def test_xray_build_payload():
    cfg = XrayCloudConfig(client_id="cid", client_secret="csec")
    client = XrayClient(cfg)
    report = {
        "items": [
            {"verdict": "PASS", "endpoint": "/users", "method": "GET", "test_key": "QA-1"},
            {"verdict": "FAIL", "endpoint": "/users", "method": "POST", "test_key": "QA-2"},
        ]
    }
    payload = client._build_payload(report, "QA", None)
    tests = payload["tests"]
    assert len(tests) == 2
    assert tests[0]["status"] == "PASSED"
    assert tests[1]["status"] == "FAILED"


def test_xray_build_payload_no_test_key():
    cfg = XrayCloudConfig(client_id="cid", client_secret="csec")
    client = XrayClient(cfg)
    report = {
        "items": [
            {"verdict": "PASS", "endpoint": "/foo", "method": "GET"},  # no test_key
        ]
    }
    payload = client._build_payload(report, "QA", None)
    assert payload["tests"] == []  # filtered out — no test_key


def test_zephyr_comment_builder():
    item = {"endpoint": "/users", "method": "POST", "verdict": "FAIL", "summary": "Missing field"}
    comment = ZephyrClient._build_comment(item)
    assert "POST /users" in comment
    assert "FAIL" in comment
    assert "Missing field" in comment


# ── Anthropic provider ────────────────────────────────────────────────────────


def test_anthropic_provider_import():
    from cherenkov.substrate.providers.anthropic import AnthropicProvider, _cost_usd
    assert callable(_cost_usd)
    cost = _cost_usd("claude-sonnet-4-6", input_tokens=1000, output_tokens=500)
    assert cost > 0


def test_anthropic_provider_capabilities():
    from cherenkov.substrate.providers.anthropic import AnthropicProvider
    p = AnthropicProvider(api_key="dummy")
    caps = p.capabilities()
    assert caps.requires_egress is True
    assert caps.provider_name == "anthropic"
    assert "small" in caps.capability_tiers
    assert "deep" in caps.capability_tiers


def test_get_provider_anthropic():
    from cherenkov.substrate.provider import get_provider, _PROVIDER_CACHE
    _PROVIDER_CACHE.pop("anthropic", None)
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "dummy"}):
        p = get_provider("anthropic")
    assert p.capabilities().provider_name == "anthropic"
    _PROVIDER_CACHE.pop("anthropic", None)


def test_get_provider_unknown():
    from cherenkov.substrate.provider import get_provider
    with pytest.raises(ValueError, match="anthropic"):
        get_provider("nonexistent_provider_xyz")
