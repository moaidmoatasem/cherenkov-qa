from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.hitl.contracts import HitlEnvelope, HitlItem, HitlStatus
from cherenkov.openclaw.adapter import OpenClawAdapter
from cherenkov.openclaw.contracts import OpenClawConfig
from cherenkov.adapters.notifiers.slack import SlackNotifier


class TestSlackNotifier(unittest.TestCase):
    """Unit tests for SlackNotifier Block Kit formatting and webhook delivery (Issue #445)."""

    def setUp(self):
        self.webhook_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"

    @patch("cherenkov.adapters.notifiers.slack.requests.post")
    def test_send_message_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        notifier = SlackNotifier(self.webhook_url)
        
        result = notifier.send_message({"text": "hello"})
        self.assertTrue(result)
        mock_post.assert_called_once_with(self.webhook_url, json={"text": "hello"}, timeout=5)

    @patch("cherenkov.adapters.notifiers.slack.requests.post")
    def test_send_message_failure(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="Internal Error")
        notifier = SlackNotifier(self.webhook_url)
        
        result = notifier.send_message({"text": "hello"})
        self.assertFalse(result)

    def test_config_webhook_resolution(self):
        # Case 1: Provided in constructor
        notifier1 = SlackNotifier(self.webhook_url)
        self.assertEqual(notifier1.webhook_url, self.webhook_url)

        # Case 2: Read from environment
        with patch.dict(os.environ, {"CHERENKOV_SLACK_WEBHOOK_URL": "http://env-url"}):
            notifier2 = SlackNotifier()
            self.assertEqual(notifier2.webhook_url, "http://env-url")

    def test_format_block_kit_new_item(self):
        notifier = SlackNotifier(self.webhook_url)
        item_data = {
            "id": "scn-1",
            "endpoint": "/payments/charge",
            "method": "POST",
            "mutation_id": "payment_too_large",
            "mutation_label": "Payload size limit exceeded",
            "confidence": 0.85,
            "confidence_reason": "Expected `422` (spec) | Received `400` (server)",
            "review_gate_failed": "assertion",
            "spec_hash": "abcdefg12345",
            "run_id": "run-xyz"
        }
        envelope = HitlEnvelope(
            schema_version="hitl/v1",
            ok=True,
            command="openclaw.new_item",
            payload=item_data
        )

        payload = notifier.format_block_kit(envelope)
        self.assertIsNotNone(payload)
        
        blocks = payload["blocks"]
        self.assertEqual(blocks[0]["text"]["text"], "🔴 CHERENKOV: Conformance drift detected")
        
        body_text = blocks[1]["text"]["text"]
        self.assertIn("/payments/charge", body_text)
        self.assertIn("*Expected:* `422` (spec) → *Got:* `400` (server)", body_text)
        self.assertIn("assertion", body_text)
        
        actions = blocks[2]["elements"]
        self.assertEqual(actions[0]["url"], "http://localhost:3000/conformance/run-xyz")

    def test_format_block_kit_healing_suggestion(self):
        notifier = SlackNotifier(self.webhook_url)
        suggestion_data = {
            "scenario_id": "scn-1",
            "suggestion": "expect(response.status).toBe(201)",
            "failure_class": "CONTRACT_DRIFT"
        }
        envelope = HitlEnvelope(
            schema_version="hitl/v1",
            ok=True,
            command="openclaw.healing_suggestion",
            payload=suggestion_data
        )

        payload = notifier.format_block_kit(envelope)
        self.assertIsNotNone(payload)
        
        blocks = payload["blocks"]
        self.assertEqual(blocks[0]["text"]["text"], "💡 CHERENKOV: Healing Suggestion Available")
        
        body_text = blocks[1]["text"]["text"]
        self.assertIn("scn-1", body_text)
        self.assertIn("expect(response.status).toBe(201)", body_text)

    def test_format_block_kit_approve(self):
        notifier = SlackNotifier(self.webhook_url)
        approve_data = {
            "id": "scn-1",
            "action": "approve",
            "actor": "@reviewer",
            "current_status": "approved"
        }
        envelope = HitlEnvelope(
            schema_version="hitl/v1",
            ok=True,
            command="openclaw.approve",
            payload=approve_data
        )

        payload = notifier.format_block_kit(envelope)
        self.assertIsNotNone(payload)
        
        blocks = payload["blocks"]
        self.assertEqual(blocks[0]["text"]["text"], "🟢 CHERENKOV: HITL Item Approved")
        
        body_text = blocks[1]["text"]["text"]
        self.assertIn("scn-1", body_text)
        self.assertIn("@reviewer", body_text)

    @patch("cherenkov.adapters.notifiers.slack.requests.post")
    def test_openclaw_adapter_wires_slack(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        
        # Instantiate OpenClawAdapter with configured notification_endpoint
        config = OpenClawConfig(notification_endpoint=self.webhook_url)
        adapter = OpenClawAdapter(config=config)
        
        # Trigger notify_new_item
        item = HitlItem(
            id="test-item",
            endpoint="/api",
            method="GET",
            confidence_reason="expected 200 got 500"
        )
        adapter.notify_new_item(item)
        
        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], self.webhook_url)
        self.assertIn("blocks", kwargs["json"])


if __name__ == "__main__":
    unittest.main()
