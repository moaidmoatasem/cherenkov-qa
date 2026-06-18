# TODO: convert to pytest — integration test with heavy mock patching (left for follow-up)
"""
Tests for Issue #196 — Security Hardening: HITL Auth + At-Rest Encryption.

Validates:
- API key auth verification (verify_api_key dependency)
- API key via X-API-Key header
- API key via Authorization: Bearer header
- Missing/Invalid API key returns 401
- SQLite at-rest encryption via CHERENKOV_DB_KEY
"""

import os
import tempfile
import unittest
from unittest.mock import patch


def _reload_config():
    import importlib
    import cherenkov.core.config

    importlib.reload(cherenkov.core.config)
    return cherenkov.core.config


class TestHitlAuthVerification(unittest.TestCase):
    """Tests for API key authentication on review endpoints."""

    def _make_vk(self, api_key=""):
        from cherenkov.core.settings import get_settings

        get_settings().HITL_API_KEY = api_key
        from cherenkov.web.routes.deps import verify_api_key

        return verify_api_key

    def test_missing_key_raises_401(self):
        import fastapi
        import asyncio

        vk = self._make_vk("test-key-123")
        with self.assertRaises(fastapi.HTTPException) as ctx:
            asyncio.run(vk(x_api_key=None, authorization=None))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_valid_x_api_key_passes(self):
        import asyncio

        vk = self._make_vk("test-key-123")
        result = asyncio.run(vk(x_api_key="test-key-123", authorization=None))
        self.assertIsNone(result, "Valid API key should return None (pass)")

    def test_valid_bearer_token_passes(self):
        import asyncio

        vk = self._make_vk("test-key-123")
        result = asyncio.run(vk(x_api_key=None, authorization="Bearer test-key-123"))
        self.assertIsNone(result, "Valid Bearer token should return None (pass)")

    def test_wrong_api_key_raises_401(self):
        import fastapi
        import asyncio

        vk = self._make_vk("test-key-123")
        with self.assertRaises(fastapi.HTTPException) as ctx:
            asyncio.run(vk(x_api_key="wrong-key", authorization=None))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_no_auth_configured_allows_all(self):
        import asyncio

        vk = self._make_vk("")
        result = asyncio.run(vk(x_api_key=None, authorization=None))
        self.assertIsNone(result, "No auth configured should allow all")


class TestHitlDbEncryption(unittest.TestCase):
    """Tests for SQLite at-rest encryption support."""

    def test_plain_sqlite_when_no_key(self):
        from cherenkov.hitl.store import _get_connection

        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.db")
        try:
            con = _get_connection(db_path)
            con.execute("CREATE TABLE t (x TEXT)")
            con.execute("INSERT INTO t VALUES ('hello')")
            rows = con.execute("SELECT x FROM t").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["x"], "hello")
            con.close()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_encryption_falls_back_gracefully(self):
        from cherenkov.hitl.store import _get_connection

        with patch("cherenkov.hitl.store._DB_KEY", "test-key-abc"):
            tmpdir = tempfile.mkdtemp()
            db_path = os.path.join(tmpdir, "test_enc.db")
            try:
                con = _get_connection(db_path)
                con.execute("CREATE TABLE t (x TEXT)")
                con.execute("INSERT INTO t VALUES ('encrypted')")
                rows = con.execute("SELECT x FROM t").fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["x"], "encrypted")
                con.close()
            finally:
                import shutil

                shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
