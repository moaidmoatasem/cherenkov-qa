# TODO: convert to pytest — complex setUp with monkey-patching internals
"""
Tests for Local SQLite RAG Index (Issue #252).
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.ai.rag_index import RAGIndex
from cherenkov.core.errors import get_logger


class TestRAGIndex(unittest.TestCase):
    """Tests for local SQLite vector search index."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "rag_store.db")
        # Create index with custom db path by monkey-patching before init
        self.index = RAGIndex.__new__(RAGIndex)
        self.index.run_id = "test_run"
        self.index.log = get_logger("RAG_INDEX", "test_run")
        self.index.db_path = self.db_path
        import threading
        self.index._local = threading.local()
        self.index._initialize_db()

    def tearDown(self):
        if hasattr(self, 'index') and hasattr(self.index, 'close'):
            self.index.close()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initialize_db_creates_table(self):
        """Test database table is created on init."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='incident_vectors'"
        )
        result = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(result)

    def test_add_incident_stores_vector(self):
        """Test adding incident stores embedding in database."""
        with patch.object(self.index, "_get_embedding", return_value=[0.1] * 768):
            self.index.add_incident("inc-001", "SCN-001", "HTTP_500", "Server error")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, scenario_id, failure_class, error_message FROM incident_vectors WHERE id='inc-001'"
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "inc-001")
        self.assertEqual(row[1], "SCN-001")
        self.assertEqual(row[2], "HTTP_500")
        self.assertEqual(row[3], "Server error")

    def test_query_similar_incidents_returns_ranked(self):
        """Test query returns incidents ranked by cosine similarity."""
        # Add two incidents with different embeddings
        with patch.object(self.index, "_get_embedding") as mock_embed:
            # First incident: similar to query
            mock_embed.side_effect = [
                [1.0, 0.0, 0.0],  # incident 1 embedding
                [0.0, 1.0, 0.0],  # incident 2 embedding
                [1.0, 0.0, 0.0],  # query embedding (matches incident 1)
            ]
            self.index.add_incident("inc-001", "SCN-001", "HTTP_500", "Server error")
            self.index.add_incident("inc-002", "SCN-002", "TIMEOUT", "Request timeout")
            results = self.index.query_similar_incidents("Server error", limit=2)

        self.assertEqual(len(results), 2)
        # First result should be the similar one
        self.assertEqual(results[0]["id"], "inc-001")
        self.assertGreater(results[0]["similarity"], results[1]["similarity"])

    def test_empty_corpus_returns_empty(self):
        """Test empty corpus returns empty list (no fabricated results)."""
        results = self.index.query_similar_incidents("Any error", limit=3)
        self.assertEqual(results, [])

    def test_query_with_limit(self):
        """Test query respects limit parameter."""
        with patch.object(self.index, "_get_embedding", return_value=[0.1] * 768):
            for i in range(5):
                self.index.add_incident(f"inc-{i}", f"SCN-{i}", "ERROR", f"Error {i}")
            results = self.index.query_similar_incidents("Error", limit=2)
        self.assertEqual(len(results), 2)

    def test_add_incident_replaces_duplicate_id(self):
        """Test adding incident with same ID replaces existing."""
        with patch.object(self.index, "_get_embedding", return_value=[0.1] * 768):
            self.index.add_incident("inc-001", "SCN-001", "HTTP_500", "Server error")
            self.index.add_incident("inc-001", "SCN-001", "HTTP_500", "Updated error")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM incident_vectors WHERE id='inc-001'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_embedding_fallback_to_empty(self):
        """Test _get_embedding returns a mock vector when Ollama is unavailable."""
        with patch("requests.post", side_effect=Exception("Connection refused")):
            vector = self.index._get_embedding("test text")

        self.assertEqual(vector, [0.1] * 768)

    def test_ollama_embed_api_tried_first(self):
        """Test Ollama /api/embed is tried before legacy /api/embeddings."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: {"embeddings": [[0.5] * 768]}),
            ]
            vector = self.index._get_embedding("test")

        self.assertEqual(vector, [0.5] * 768)
        # Check /api/embed was called
        call_url = mock_post.call_args[0][0]
        self.assertIn("/api/embed", call_url)

    def test_legacy_embeddings_fallback(self):
        """Test legacy /api/embeddings is used when /api/embed fails."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                Exception("Not found"),  # /api/embed fails
                MagicMock(
                    status_code=200, json=lambda: {"embedding": [0.3] * 768}
                ),  # /api/embeddings works
            ]
            vector = self.index._get_embedding("test")

        self.assertEqual(vector, [0.3] * 768)
        self.assertEqual(mock_post.call_count, 2)


# Need to import sqlite3 for the first test


if __name__ == "__main__":
    unittest.main()
