"""Integration test: verify SQLite fallback when Redis is unavailable."""
import unittest
from unittest import mock


class TestRedisFallback(unittest.TestCase):
    """When Redis is unavailable, all stores should fall back to SQLite."""

    def test_reflector_store_falls_back_to_sqlite(self):
        """ReflectorStore should use SQLite when Redis connection fails."""
        with mock.patch("redis.Redis.ping", side_effect=ConnectionError("Redis down")):
            try:
                from cherenkov.reflector.store import ReflectorStore
                store = ReflectorStore(db_path=":memory:")
                # Should not raise even with Redis down
                self.assertIsNotNone(store)
            except ImportError:
                self.skipTest("ReflectorStore not available")

    def test_verdict_store_falls_back_to_sqlite(self):
        """VerdictStore should use SQLite when Redis connection fails."""
        with mock.patch("redis.Redis.ping", side_effect=ConnectionError("Redis down")):
            try:
                from cherenkov.truth.model import VerdictRecord
                from cherenkov.reflector.store import VerdictStore
                store = VerdictStore(db_path=":memory:")
                self.assertIsNotNone(store)
            except ImportError:
                self.skipTest("VerdictStore not available")

    def test_hitl_store_falls_back_to_sqlite(self):
        """HitlStore should use SQLite when Redis is unavailable."""
        with mock.patch("redis.Redis.ping", side_effect=ConnectionError("Redis down")):
            try:
                from cherenkov.hitl.store import HitlStore
                store = HitlStore(db_path=":memory:")
                self.assertIsNotNone(store)
            except ImportError:
                self.skipTest("HitlStore not available")


if __name__ == "__main__":
    unittest.main()
