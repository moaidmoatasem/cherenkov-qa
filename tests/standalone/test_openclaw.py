"""
test_openclaw.py — Unit tests for OpenClaw Tier-1 adapter (Issue #116).

Tests the OpenClawAdapter class and its hitl/v1 envelope operations.
"""

import unittest
import os
import tempfile

from cherenkov.hitl.contracts import HitlItem, HitlStatus, ok_envelope
from cherenkov.hitl.store import HitlQueue
from cherenkov.openclaw.adapter import OpenClawAdapter, TriggerRequest
from cherenkov.openclaw.contracts import OpenClawConfig


class TestOpenClawAdapter(unittest.TestCase):
    """Tests for the core OpenClaw adapter logic (no HTTP)."""

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.queue = HitlQueue(db_path=self.db_path)
        self.adapter = OpenClawAdapter(queue=self.queue)
        self._seed_item()
        self.adapter.poll_envelope()  # prime poll so first call returns empty

    def tearDown(self):
        os.unlink(self.db_path)

    def _seed_item(
        self, item_id: str = "test-item-1", status: HitlStatus = HitlStatus.PENDING
    ):
        item = HitlItem(
            id=item_id,
            status=status,
            endpoint="/api/users",
            method="POST",
            mutation_id="missing_email",
            confidence=0.75,
            review_gate_failed="assertions",
        )
        self.queue.enqueue(item)
        return item

    # ── list_envelope ─────────────────────────────────────────────────────

    def test_list_envelope_returns_envelope(self):
        env = self.adapter.list_envelope()
        self.assertTrue(env.ok)
        self.assertEqual(env.schema_version, "hitl/v1")
        self.assertEqual(env.command, "openclaw.list")

    def test_list_envelope_contains_items(self):
        env = self.adapter.list_envelope()
        self.assertTrue(env.ok)
        self.assertIsNotNone(env.payload)
        self.assertGreaterEqual(env.payload["count"], 1)
        self.assertEqual(len(env.payload["items"]), env.payload["count"])

    def test_list_envelope_empty_status(self):
        env = self.adapter.list_envelope(status="approved")
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["count"], 0)

    def test_list_envelope_all_statuses(self):
        env = self.adapter.list_envelope(status=None)
        self.assertTrue(env.ok)
        self.assertGreaterEqual(env.payload["count"], 1)

    # ── show_envelope ─────────────────────────────────────────────────────

    def test_show_envelope_found(self):
        env = self.adapter.show_envelope("test-item-1")
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["item"]["id"], "test-item-1")
        self.assertEqual(env.payload["item"]["endpoint"], "/api/users")

    def test_show_envelope_not_found(self):
        env = self.adapter.show_envelope("nonexistent")
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "not_found")

    # ── approve_envelope ───────────────────────────────────────────────────

    def test_approve_envelope_success(self):
        env = self.adapter.approve_envelope("test-item-1", "test-actor")
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["action"], "approve")
        self.assertEqual(env.payload["actor"], "test-actor")

    def test_approve_envelope_conflict(self):
        self.adapter.approve_envelope("test-item-1", "actor-1")
        env = self.adapter.approve_envelope("test-item-1", "actor-2")
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "conflict")

    def test_approve_envelope_not_found(self):
        env = self.adapter.approve_envelope("nonexistent", "actor")
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "not_found")

    def test_approve_notifies_callbacks(self):
        calls = []
        self.adapter.on_notify(lambda env: calls.append(env.command))
        self.adapter.approve_envelope("test-item-1", "actor")
        self.assertIn("openclaw.approve", calls)

    # ── reject_envelope ────────────────────────────────────────────────────

    def test_reject_envelope_success(self):
        env = self.adapter.reject_envelope("test-item-1", "actor", "bad test")
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["action"], "reject")

    def test_reject_envelope_conflict(self):
        self.adapter.reject_envelope("test-item-1", "a", "reason")
        env = self.adapter.reject_envelope("test-item-1", "b", "reason")
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "conflict")

    def test_reject_notifies_callbacks(self):
        calls = []
        self.adapter.on_notify(lambda env: calls.append(env.command))
        self.adapter.reject_envelope("test-item-1", "actor", "reason")
        self.assertIn("openclaw.reject", calls)

    # ── trigger_run ────────────────────────────────────────────────────────

    def test_trigger_run_no_handler(self):
        req = TriggerRequest(reason="test")
        env = self.adapter.trigger_run(req)
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "not_found")

    def test_trigger_run_with_handler(self):
        results = []

        def handler(req: TriggerRequest) -> str:
            results.append(req.reason)
            return ok_envelope(
                "openclaw.trigger", {"triggered": True, "reason": req.reason}
            )

        # wrap the bare function since on_trigger expects a TriggerCallback
        self.adapter.on_trigger(handler)
        req = TriggerRequest(reason="manual")
        env = self.adapter.trigger_run(req)
        self.assertTrue(env.ok)
        self.assertEqual(len(results), 1)

    def test_trigger_run_handler_error_returns_error(self):
        def failing_handler(req):
            raise ValueError("handler failed")

        self.adapter.on_trigger(failing_handler)
        req = TriggerRequest(reason="test")
        env = self.adapter.trigger_run(req)
        self.assertFalse(env.ok)

    def test_trigger_notifies_callbacks(self):
        calls = []

        def handler(req):
            return ok_envelope("openclaw.trigger", {"triggered": True})

        self.adapter.on_trigger(handler)
        self.adapter.on_notify(lambda env: calls.append(env.command))
        req = TriggerRequest(reason="test")
        self.adapter.trigger_run(req)
        self.assertIn("openclaw.trigger", calls)

    # ── poll_envelope ──────────────────────────────────────────────────────

    def test_poll_returns_empty_first_call(self):
        env = self.adapter.poll_envelope()
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["new_count"], 0)

    def test_poll_detects_new_items(self):
        self.adapter.poll_envelope()  # prime
        self._seed_item("poll-test-2")
        env = self.adapter.poll_envelope()
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["new_count"], 1)
        ids = [i["id"] for i in env.payload["new_items"]]
        self.assertIn("poll-test-2", ids)

    def test_poll_does_not_duplicate_seen_items(self):
        self.adapter.poll_envelope()  # prime
        self._seed_item("poll-test-3")
        self.adapter.poll_envelope()  # consume
        env = self.adapter.poll_envelope()
        self.assertEqual(env.payload["new_count"], 0)

    # ── envelope contract ──────────────────────────────────────────────────

    def test_all_envelopes_have_hitl_v1_schema(self):
        for env in [
            self.adapter.list_envelope(),
            self.adapter.show_envelope("test-item-1"),
        ]:
            self.assertEqual(env.schema_version, "hitl/v1")

    def test_error_envelopes_have_valid_error_code(self):
        env = self.adapter.show_envelope("nope")
        self.assertIn(
            env.error.code,
            {
                "conflict",
                "not_found",
                "forbidden",
                "invalid_input",
                "db_locked",
                "llm_unavailable",
            },
        )

    # ── config ─────────────────────────────────────────────────────────────

    def test_default_config_values(self):
        cfg = OpenClawget_settings()
        self.assertEqual(cfg.host, "127.0.0.1")
        self.assertEqual(cfg.port, 8721)
        self.assertEqual(cfg.poll_interval_sec, 5.0)
        self.assertEqual(cfg.max_notify_retries, 3)

    def test_custom_config(self):
        cfg = OpenClawConfig(host="0.0.0.0", port=9999, poll_interval_sec=2.0)
        self.assertEqual(cfg.host, "0.0.0.0")
        self.assertEqual(cfg.port, 9999)

    # ── edge cases ─────────────────────────────────────────────────────────

    def test_schema_version_matches_hitl_contract(self):
        from cherenkov.hitl.contracts import SCHEMA_VERSION as HITL_SCHEMA

        env = self.adapter.list_envelope()
        self.assertEqual(env.schema_version, HITL_SCHEMA)


class TestTriggerRequest(unittest.TestCase):
    """Tests for the TriggerRequest model."""

    def test_default_values(self):
        req = TriggerRequest()
        self.assertEqual(req.reason, "manual_trigger")
        self.assertIsNone(req.run_id)
        self.assertIsNone(req.endpoint)

    def test_custom_values(self):
        req = TriggerRequest(
            run_id="run-1",
            endpoint="/api/test",
            method="POST",
            reason="ci_callback",
            params={"key": "value"},
        )
        self.assertEqual(req.run_id, "run-1")
        self.assertEqual(req.endpoint, "/api/test")
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.reason, "ci_callback")
        self.assertEqual(req.params, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
