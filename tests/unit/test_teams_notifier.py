"""
Unit tests for cherenkov/adapters/notifiers/teams.py

Tests verify:
- TeamsNotifier skips sending when not configured
- notify_envelope dispatches correctly for all 4 command types
- format_adaptive_card returns None for unknown commands
- Adaptive Card payload contains expected fields for each command
- send_message returns True on 200/202, False on errors
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cherenkov.adapters.notifiers.teams import TeamsNotifier
from cherenkov.hitl.contracts import HitlEnvelope


def _make_envelope(command: str, payload: dict) -> HitlEnvelope:
    env = MagicMock(spec=HitlEnvelope)
    env.command = command
    env.payload = payload
    return env


@pytest.fixture
def configured() -> TeamsNotifier:
    return TeamsNotifier(webhook_url="https://teams.example.com/webhook")


@pytest.fixture
def unconfigured() -> TeamsNotifier:
    return TeamsNotifier(webhook_url=None)


class TestTeamsNotifierConfig:
    def test_is_configured_true(self, configured: TeamsNotifier):
        assert configured.is_configured is True

    def test_is_configured_false(self, unconfigured: TeamsNotifier):
        assert unconfigured.is_configured is False

    def test_notify_envelope_skips_when_unconfigured(self, unconfigured: TeamsNotifier):
        envelope = _make_envelope("openclaw.new_item", {"endpoint": "/x"})
        with patch.object(unconfigured, "send_message") as mock_send:
            unconfigured.notify_envelope(envelope)
            mock_send.assert_not_called()


class TestFormatAdaptiveCard:
    def test_unknown_command_returns_none(self, configured: TeamsNotifier):
        env = _make_envelope("some.unknown", {})
        result = configured.format_adaptive_card(env)
        assert result is None

    def test_empty_payload_returns_none(self, configured: TeamsNotifier):
        env = _make_envelope("openclaw.new_item", {})
        env.payload = None
        result = configured.format_adaptive_card(env)
        assert result is None

    def test_drift_detected_card_structure(self, configured: TeamsNotifier):
        payload = {
            "endpoint": "/payments",
            "method": "POST",
            "run_id": "run-123",
            "spec_hash": "abc12345",
            "review_gate_failed": "STATUS_CHECK",
            "confidence_reason": "Expected `201` received `400`"
        }
        env = _make_envelope("openclaw.new_item", payload)
        result = configured.format_adaptive_card(env)
        assert result is not None
        # Outer envelope
        assert result["type"] == "message"
        assert "attachments" in result
        card = result["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"
        # Check drift title is present
        body_texts = [b.get("text", "") for b in card["body"]]
        assert any("Drift Detected" in t for t in body_texts)

    def test_drift_card_extracts_status_codes(self, configured: TeamsNotifier):
        payload = {
            "endpoint": "/payments",
            "method": "POST",
            "confidence_reason": "Expected `201` received `400`"
        }
        env = _make_envelope("openclaw.new_item", payload)
        result = configured.format_adaptive_card(env)
        card = result["attachments"][0]["content"]
        fact_set = next(b for b in card["body"] if b["type"] == "FactSet")
        values = {f["title"]: f["value"] for f in fact_set["facts"]}
        assert "201" in values["Expected"]
        assert "400" in values["Received"]

    def test_healing_suggestion_card(self, configured: TeamsNotifier):
        payload = {
            "scenario_id": "sc-fail-1",
            "suggestion": "Add Content-Type: application/json header",
            "failure_class": "HEADER_MISSING"
        }
        env = _make_envelope("openclaw.healing_suggestion", payload)
        result = configured.format_adaptive_card(env)
        assert result is not None
        card = result["attachments"][0]["content"]
        body_texts = [b.get("text", "") for b in card["body"]]
        assert any("Healing" in t for t in body_texts)
        assert any("Add Content-Type" in t for t in body_texts)

    def test_hitl_approved_card(self, configured: TeamsNotifier):
        payload = {"action": "approve", "id": "item-abc", "actor": "user@example.com", "current_status": "approved"}
        env = _make_envelope("openclaw.approve", payload)
        result = configured.format_adaptive_card(env)
        card = result["attachments"][0]["content"]
        title_block = card["body"][0]
        assert "Approved" in title_block["text"] or "approved" in title_block["text"].lower()

    def test_hitl_rejected_card_includes_reason(self, configured: TeamsNotifier):
        payload = {
            "action": "reject",
            "id": "item-xyz",
            "actor": "user@example.com",
            "current_status": "rejected",
            "reject_reason": "False positive — spec is incorrect"
        }
        env = _make_envelope("openclaw.reject", payload)
        result = configured.format_adaptive_card(env)
        card = result["attachments"][0]["content"]
        fact_set = next(b for b in card["body"] if b["type"] == "FactSet")
        titles = [f["title"] for f in fact_set["facts"]]
        assert "Reason" in titles


class TestSendMessage:
    @patch("cherenkov.adapters.notifiers.teams.requests.post")
    def test_returns_true_on_200(self, mock_post: MagicMock, configured: TeamsNotifier):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        assert configured.send_message({"type": "message"}) is True

    @patch("cherenkov.adapters.notifiers.teams.requests.post")
    def test_returns_true_on_202(self, mock_post: MagicMock, configured: TeamsNotifier):
        mock_resp = MagicMock()
        mock_resp.status_code = 202
        mock_post.return_value = mock_resp
        assert configured.send_message({"type": "message"}) is True

    @patch("cherenkov.adapters.notifiers.teams.requests.post")
    def test_returns_false_on_4xx(self, mock_post: MagicMock, configured: TeamsNotifier):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_post.return_value = mock_resp
        assert configured.send_message({"type": "message"}) is False

    @patch("cherenkov.adapters.notifiers.teams.requests.post")
    def test_returns_false_on_exception(self, mock_post: MagicMock, configured: TeamsNotifier):
        mock_post.side_effect = Exception("Connection refused")
        assert configured.send_message({"type": "message"}) is False

    @patch("cherenkov.adapters.notifiers.teams.requests.post")
    def test_notify_envelope_calls_send(self, mock_post: MagicMock, configured: TeamsNotifier):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        payload = {"endpoint": "/x", "method": "GET", "confidence_reason": "test"}
        env = _make_envelope("openclaw.new_item", payload)
        configured.notify_envelope(env)
        mock_post.assert_called_once()
