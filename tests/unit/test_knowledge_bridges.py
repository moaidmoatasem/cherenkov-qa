import os
import tempfile
import unittest
from unittest.mock import MagicMock

from cherenkov.knowledge.bridges.hitl_reflector import HITLReflectorBridge
from cherenkov.knowledge.bridges.feedback_rag import FeedbackRAGBridge
from cherenkov.knowledge.bridges.agent_memory_rag import AgentMemoryRAGBridge
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository


class TestHITLReflectorBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = SQLiteKnowledgeRepository(self.db_path)
        self.reflector = MagicMock()
        self.bridge = HITLReflectorBridge(self.repo, self.reflector)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_on_hitl_decision_stores_item(self):
        self.bridge.on_hitl_decision("item-1", "approve", "looks good", "/api/users", "GET")
        result = self.repo.get_by_id("hitl_item-1")
        self.assertIsNotNone(result)
        self.assertEqual(result.data["action"], "approve")
        self.assertEqual(result.data["endpoint"], "/api/users")

    def test_on_hitl_decision_calls_reflector(self):
        self.bridge.on_hitl_decision("item-2", "reject", "bad spec", "/api/auth", "POST")
        self.reflector.ingest_human_verdict.assert_called_once_with(
            item_id="item-2",
            verdict="reject",
            reason="bad spec",
            endpoint="/api/auth",
            method="POST",
        )


class TestFeedbackRAGBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = SQLiteKnowledgeRepository(self.db_path)
        self.feedback_store = MagicMock()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_sync_feedback_stores_entries(self):
        entry = MagicMock()
        entry.id = "fb1"
        entry.endpoint = "/api/users"
        entry.method = "GET"
        entry.reason = "wrong status"
        entry.comment = "should be 422"
        entry.created_at = "2026-01-01T00:00:00"
        self.feedback_store.list_all.return_value = [entry]
        bridge = FeedbackRAGBridge(self.repo, self.feedback_store)
        count = bridge.sync_feedback()
        self.assertEqual(count, 1)
        result = self.repo.get_by_id("feedback_fb1")
        self.assertIsNotNone(result)
        self.assertEqual(result.data["endpoint"], "/api/users")

    def test_sync_feedback_empty(self):
        self.feedback_store.list_all.return_value = []
        bridge = FeedbackRAGBridge(self.repo, self.feedback_store)
        count = bridge.sync_feedback()
        self.assertEqual(count, 0)


class TestAgentMemoryRAGBridge(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp_db.name
        self.tmp_db.close()
        self.repo = SQLiteKnowledgeRepository(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_sync_agent_memory_no_dir(self):
        bridge = AgentMemoryRAGBridge(self.repo, memory_dir="/nonexistent/path")
        count = bridge.sync_agent_memory()
        self.assertEqual(count, 0)

    def test_sync_agent_memory_with_files(self):
        md_file = os.path.join(self.tmp_dir.name, "test_finding.md")
        with open(md_file, "w") as f:
            f.write("# Finding\n\nThis is a test finding.")
        bridge = AgentMemoryRAGBridge(self.repo, memory_dir=self.tmp_dir.name)
        count = bridge.sync_agent_memory()
        self.assertEqual(count, 1)
        result = self.repo.get_by_id("agent_memory_test_finding")
        self.assertIsNotNone(result)
        self.assertIn("test finding", result.data["content"])

    def test_sync_agent_memory_multiple_files(self):
        for name in ["a.md", "b.md"]:
            with open(os.path.join(self.tmp_dir.name, name), "w") as f:
                f.write(f"# {name}")
        bridge = AgentMemoryRAGBridge(self.repo, memory_dir=self.tmp_dir.name)
        count = bridge.sync_agent_memory()
        self.assertEqual(count, 2)

    def test_sync_agent_memory_skips_non_md(self):
        txt_file = os.path.join(self.tmp_dir.name, "readme.txt")
        with open(txt_file, "w") as f:
            f.write("text file")
        bridge = AgentMemoryRAGBridge(self.repo, memory_dir=self.tmp_dir.name)
        count = bridge.sync_agent_memory()
        self.assertEqual(count, 0)
