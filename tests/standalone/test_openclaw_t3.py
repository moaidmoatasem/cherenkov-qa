import unittest
import tempfile
import os
from unittest.mock import patch

from cherenkov.hitl.contracts import HitlItem
from cherenkov.hitl.store import HitlQueue
from cherenkov.openclaw.adapter import OpenClawAdapter
from cherenkov.openclaw.feedback import HealingFeedbackStore
from cherenkov.core.contracts import ReasoningResult


class TestOpenClawTier3(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.fb_fd, self.fb_path = tempfile.mkstemp()
        self.queue = HitlQueue(db_path=self.db_path)
        self.feedback = HealingFeedbackStore(db_path=self.fb_path)
        self.adapter = OpenClawAdapter(queue=self.queue, feedback_store=self.feedback)

    def tearDown(self):
        os.close(self.db_fd)
        os.close(self.fb_fd)
        try:
            os.unlink(self.db_path)
            os.unlink(self.fb_path)
        except Exception:
            pass

    @patch("cherenkov.openclaw.adapter.route")
    def test_explain_success(self, mock_route):
        item = HitlItem(
            id="test-item-1",
            endpoint="/api/users",
            method="POST",
            mutation_id="missing_email",
            review_gate_failed="assertions",
        )
        self.queue.enqueue(item)

        mock_route.return_value = ReasoningResult(
            content="This request failed because assertions failed.",
            provider="ollama",
            model="qwen2.5-coder:7b",
        )

        env = self.adapter.explain_envelope("test-item-1")
        self.assertTrue(env.ok)
        self.assertEqual(env.payload["id"], "test-item-1")
        self.assertEqual(
            env.payload["explanation"],
            "[AI 🤖] This request failed because assertions failed.",
        )

    @patch("cherenkov.openclaw.adapter.route")
    def test_explain_model_down(self, mock_route):
        item = HitlItem(id="test-item-2", endpoint="/api/users", method="POST")
        self.queue.enqueue(item)

        mock_route.side_effect = Exception("Ollama server unreachable")

        env = self.adapter.explain_envelope("test-item-2")
        self.assertFalse(env.ok)
        self.assertEqual(env.error.code, "llm_unavailable")
        self.assertIn("Offline path: Local model is down", env.error.message)
