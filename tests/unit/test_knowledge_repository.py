# TODO: convert to pytest — complex file (>150 lines, many test classes with setUp/tearDown)
import unittest
import os
import tempfile

from cherenkov.knowledge.domain.models import (
    KnowledgeQuery,
    KnowledgeQueryResult,
    KnowledgeItem,
)
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.graph_rag import GraphRAG


class TestKnowledgeQuery(unittest.TestCase):
    def test_defaults(self):
        q = KnowledgeQuery(query="auth timeout")
        self.assertEqual(q.query, "auth timeout")
        self.assertIsNone(q.source)
        self.assertEqual(q.limit, 10)
        self.assertEqual(q.filter, {})

    def test_with_source(self):
        q = KnowledgeQuery(query="test", source="verdicts", limit=5)
        self.assertEqual(q.source, "verdicts")
        self.assertEqual(q.limit, 5)


class TestKnowledgeQueryResult(unittest.TestCase):
    def test_to_dict(self):
        r = KnowledgeQueryResult(data={"key": "value"}, source="test", confidence=0.9)
        d = r.to_dict()
        self.assertEqual(d["data"]["key"], "value")
        self.assertEqual(d["source"], "test")
        self.assertEqual(d["confidence"], 0.9)
        self.assertIn("metadata", d)


class TestKnowledgeItem(unittest.TestCase):
    def test_defaults(self):
        item = KnowledgeItem(item_id="t1", source="verdicts", data={"ok": True})
        self.assertEqual(item.item_id, "t1")
        self.assertEqual(item.source, "verdicts")
        self.assertEqual(item.data["ok"], True)
        self.assertIsNotNone(item.created_at)
        self.assertEqual(item.metadata, {})


class TestSQLiteKnowledgeRepository(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = SQLiteKnowledgeRepository(self.db_path)

    def tearDown(self):
        if hasattr(self, 'repo'):
            self.repo.close()
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                pass

    def test_query_empty(self):
        q = KnowledgeQuery(query="test")
        result = self.repo.query(q)
        self.assertEqual(result.source, "all")
        self.assertEqual(len(result.data), 0)

    def test_store_and_query(self):
        item = KnowledgeItem(
            item_id="t1", source="verdicts", data={"endpoint": "/users"}
        )
        self.repo.store(item)
        q = KnowledgeQuery(query="test", source="verdicts")
        result = self.repo.query(q)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].data["endpoint"], "/users")

    def test_store_returns_id(self):
        item = KnowledgeItem(item_id="abc", source="test", data={"x": 1})
        returned = self.repo.store(item)
        self.assertEqual(returned, "abc")

    def test_search_finds_pattern(self):
        self.repo.store(
            KnowledgeItem(
                item_id="1",
                source="verdicts",
                data={"endpoint": "/users", "status": "auth timeout"},
            )
        )
        self.repo.store(
            KnowledgeItem(
                item_id="2",
                source="verdicts",
                data={"endpoint": "/login", "status": "success"},
            )
        )
        results = self.repo.search("auth timeout")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].data["endpoint"], "/users")

    def test_search_returns_empty_for_nonexistent(self):
        self.repo.store(
            KnowledgeItem(item_id="1", source="verdicts", data={"x": "hello"})
        )
        results = self.repo.search("nonexistent")
        self.assertEqual(len(results), 0)

    def test_get_by_id_found(self):
        self.repo.store(
            KnowledgeItem(item_id="t1", source="verdicts", data={"endpoint": "/api"})
        )
        result = self.repo.get_by_id("t1")
        self.assertIsNotNone(result)
        self.assertEqual(result.data["endpoint"], "/api")

    def test_get_by_id_not_found(self):
        result = self.repo.get_by_id("nonexistent")
        self.assertIsNone(result)

    def test_query_filters_by_source(self):
        self.repo.store(KnowledgeItem(item_id="v1", source="verdicts", data={"x": 1}))
        self.repo.store(KnowledgeItem(item_id="f1", source="feedback", data={"x": 2}))
        q = KnowledgeQuery(query="test", source="verdicts")
        result = self.repo.query(q)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].source, "verdicts")

    def test_query_limit(self):
        for i in range(5):
            self.repo.store(
                KnowledgeItem(item_id=f"t{i}", source="verdicts", data={"i": i})
            )
        q = KnowledgeQuery(query="test", limit=3)
        result = self.repo.query(q)
        self.assertLessEqual(len(result.data), 3)

    def test_search_with_limit(self):
        for i in range(5):
            self.repo.store(
                KnowledgeItem(
                    item_id=f"t{i}", source="test", data={"text": f"hello {i}"}
                )
            )
        results = self.repo.search("hello", limit=3)
        self.assertLessEqual(len(results), 3)

    def test_source_index_created(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [r[0] for r in cursor.fetchall()]
        conn.close()
        self.assertIn("idx_source", indexes)

    def test_reinit_idempotent(self):
        repo2 = SQLiteKnowledgeRepository(self.db_path)
        self.assertIsNotNone(repo2)

    def test_store_override(self):
        self.repo.store(
            KnowledgeItem(item_id="t1", source="verdicts", data={"version": 1})
        )
        self.repo.store(
            KnowledgeItem(item_id="t1", source="verdicts", data={"version": 2})
        )
        result = self.repo.get_by_id("t1")
        self.assertEqual(result.data["version"], 2)

    def test_query_result_metadata(self):
        self.repo.store(KnowledgeItem(item_id="t1", source="test", data={"x": 1}))
        q = KnowledgeQuery(query="test", source="test")
        result = self.repo.query(q)
        self.assertIn("count", result.metadata)
        self.assertEqual(result.metadata["count"], 1)

    def test_search_pattern_in_json_value(self):
        self.repo.store(
            KnowledgeItem(
                item_id="1", source="test", data={"endpoint": "/api/v1/users"}
            )
        )
        results = self.repo.search("/api/v1")
        self.assertEqual(len(results), 1)

    def test_multiple_sources(self):
        for i in range(3):
            self.repo.store(
                KnowledgeItem(item_id=f"v{i}", source="verdicts", data={"i": i})
            )
        for i in range(3):
            self.repo.store(
                KnowledgeItem(item_id=f"f{i}", source="feedback", data={"i": i})
            )
        all_results = self.repo.query(KnowledgeQuery(query="test"))
        self.assertEqual(len(all_results.data), 6)


class TestGraphRAG(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = SQLiteKnowledgeRepository(self.db_path)
        self.graph = GraphRAG(self.repo)

    def tearDown(self):
        if hasattr(self, 'repo'):
            self.repo.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_query_no_sources(self):
        results = self.graph.query("test", limit=10)
        self.assertEqual(len(results), 0)

    def test_query_with_data(self):
        self.repo.store(
            KnowledgeItem(
                item_id="v1",
                source="verdicts",
                data={"endpoint": "/auth", "status": "timeout"},
            )
        )
        results = self.graph.query("timeout", sources=["verdicts"], limit=10)
        self.assertGreater(len(results), 0)

    def test_query_respects_limit(self):
        for i in range(5):
            self.repo.store(
                KnowledgeItem(item_id=f"v{i}", source="verdicts", data={"i": i})
            )
        for i in range(5):
            self.repo.store(
                KnowledgeItem(item_id=f"f{i}", source="feedback", data={"i": i})
            )
        results = self.graph.query("test", limit=3)
        self.assertLessEqual(len(results), 3)

    def test_query_default_sources(self):
        results = self.graph.query("test")
        self.assertIsInstance(results, list)

    def test_explain_divergence(self):
        self.repo.store(
            KnowledgeItem(
                item_id="v1",
                source="verdicts",
                data={"endpoint": "/users", "method": "GET"},
            )
        )
        self.repo.store(
            KnowledgeItem(
                item_id="i1",
                source="idioms",
                data={"endpoint": "/users", "method": "GET"},
            )
        )
        result = self.graph.explain_divergence("/users", "GET")
        self.assertEqual(result.source, "graph_rag")
        self.assertIn("endpoint", result.data)
        self.assertEqual(result.data["endpoint"], "/users")
        self.assertIn("verdicts_count", result.metadata)

    def test_explain_divergence_empty(self):
        result = self.graph.explain_divergence("/nonexistent", "POST")
        self.assertEqual(result.metadata["verdicts_count"], 0)


class TestKnowledgeItemCreatedAt(unittest.TestCase):
    def test_default_created_at(self):
        item = KnowledgeItem(item_id="t1", source="test", data={})
        self.assertIsNotNone(item.created_at)

    def test_custom_created_at(self):
        from datetime import datetime

        dt = datetime(2026, 1, 1)
        item = KnowledgeItem(item_id="t2", source="test", data={}, created_at=dt)
        self.assertEqual(item.created_at, dt)
