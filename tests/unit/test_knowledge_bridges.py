import os
import tempfile
import pytest
from unittest.mock import MagicMock

from cherenkov.knowledge.bridges.hitl_reflector import HITLReflectorBridge
from cherenkov.knowledge.bridges.feedback_rag import FeedbackRAGBridge
from cherenkov.knowledge.bridges.agent_memory_rag import AgentMemoryRAGBridge
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository


@pytest.fixture
def hitl_bridge():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    repo = SQLiteKnowledgeRepository(db_path)
    reflector = MagicMock()
    bridge = HITLReflectorBridge(repo, reflector)
    yield bridge, repo, reflector
    repo.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def feedback_bridge():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    repo = SQLiteKnowledgeRepository(db_path)
    feedback_store = MagicMock()
    yield repo, feedback_store
    repo.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def agent_memory_bridge():
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp_db.name
    tmp_db.close()
    repo = SQLiteKnowledgeRepository(db_path)
    yield repo, tmp_dir
    repo.close()
    tmp_dir.cleanup()
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_on_hitl_decision_stores_item(hitl_bridge):
    bridge, repo, reflector = hitl_bridge
    bridge.on_hitl_decision("item-1", "approve", "looks good", "/api/users", "GET")
    result = repo.get_by_id("hitl_item-1")
    assert result is not None
    assert result.data["action"] == "approve"
    assert result.data["endpoint"] == "/api/users"


def test_on_hitl_decision_calls_reflector(hitl_bridge):
    bridge, repo, reflector = hitl_bridge
    bridge.on_hitl_decision("item-2", "reject", "bad spec", "/api/auth", "POST")
    reflector.ingest_human_verdict.assert_called_once_with(
        item_id="item-2",
        verdict="reject",
        reason="bad spec",
        endpoint="/api/auth",
        method="POST",
    )


def test_sync_feedback_stores_entries(feedback_bridge):
    repo, feedback_store = feedback_bridge
    entry = MagicMock()
    entry.id = "fb1"
    entry.endpoint = "/api/users"
    entry.method = "GET"
    entry.reason = "wrong status"
    entry.comment = "should be 422"
    entry.created_at = "2026-01-01T00:00:00"
    feedback_store.list_all.return_value = [entry]
    bridge = FeedbackRAGBridge(repo, feedback_store)
    count = bridge.sync_feedback()
    assert count == 1
    result = repo.get_by_id("feedback_fb1")
    assert result is not None
    assert result.data["endpoint"] == "/api/users"


def test_sync_feedback_empty(feedback_bridge):
    repo, feedback_store = feedback_bridge
    feedback_store.list_all.return_value = []
    bridge = FeedbackRAGBridge(repo, feedback_store)
    count = bridge.sync_feedback()
    assert count == 0


def test_sync_agent_memory_no_dir(agent_memory_bridge):
    repo, tmp_dir = agent_memory_bridge
    bridge = AgentMemoryRAGBridge(repo, memory_dir="/nonexistent/path")
    count = bridge.sync_agent_memory()
    assert count == 0


def test_sync_agent_memory_with_files(agent_memory_bridge):
    repo, tmp_dir = agent_memory_bridge
    md_file = os.path.join(tmp_dir.name, "test_finding.md")
    with open(md_file, "w") as f:
        f.write("# Finding\n\nThis is a test finding.")
    bridge = AgentMemoryRAGBridge(repo, memory_dir=tmp_dir.name)
    count = bridge.sync_agent_memory()
    assert count == 1
    result = repo.get_by_id("agent_memory_test_finding")
    assert result is not None
    assert "test finding" in result.data["content"]


def test_sync_agent_memory_multiple_files(agent_memory_bridge):
    repo, tmp_dir = agent_memory_bridge
    for name in ["a.md", "b.md"]:
        with open(os.path.join(tmp_dir.name, name), "w") as f:
            f.write(f"# {name}")
    bridge = AgentMemoryRAGBridge(repo, memory_dir=tmp_dir.name)
    count = bridge.sync_agent_memory()
    assert count == 2


def test_sync_agent_memory_skips_non_md(agent_memory_bridge):
    repo, tmp_dir = agent_memory_bridge
    txt_file = os.path.join(tmp_dir.name, "readme.txt")
    with open(txt_file, "w") as f:
        f.write("text file")
    bridge = AgentMemoryRAGBridge(repo, memory_dir=tmp_dir.name)
    count = bridge.sync_agent_memory()
    assert count == 0
