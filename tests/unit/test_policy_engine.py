"""Unit tests for cherenkov/mcp/policy.py — PolicyEngine."""
import json
import os
import tempfile
import unittest


def _write_policy(directory: str, data: dict) -> str:
    path = os.path.join(directory, "cherenkov-policy.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


class TestPolicyEngineNoFile(unittest.TestCase):
    def test_missing_policy_file_returns_empty_policy(self):
        from cherenkov.mcp.policy import PolicyEngine
        engine = PolicyEngine(policy_path="/no/such/policy.json")
        policy = engine.list_policy()
        self.assertEqual(policy.get("profiles"), {})
        self.assertEqual(policy.get("invariants"), {})

    def test_missing_policy_allows_all_tools(self):
        from cherenkov.mcp.policy import PolicyEngine
        engine = PolicyEngine(policy_path="/no/such/policy.json")
        self.assertTrue(engine.is_tool_allowed("default", "filesystem", "read_file"))

    def test_missing_policy_allows_all_networks(self):
        from cherenkov.mcp.policy import PolicyEngine
        engine = PolicyEngine(policy_path="/no/such/policy.json")
        self.assertTrue(engine.is_network_allowed("default", "http", "example.com"))


class TestPolicyEngineWithFile(unittest.TestCase):
    def _engine(self, policy: dict):
        from cherenkov.mcp.policy import PolicyEngine
        self.tmpdir = tempfile.mkdtemp()
        path = _write_policy(self.tmpdir, policy)
        return PolicyEngine(policy_path=path)

    def test_wildcard_tool_allows_any_tool(self):
        engine = self._engine({
            "profiles": {
                "dev": {"servers": {"fs": {"tools": ["*"]}}}
            }
        })
        self.assertTrue(engine.is_tool_allowed("dev", "fs", "anything"))

    def test_explicit_tool_list_restricts_access(self):
        engine = self._engine({
            "profiles": {
                "dev": {"servers": {"fs": {"tools": ["read_file", "list_dir"]}}}
            }
        })
        self.assertTrue(engine.is_tool_allowed("dev", "fs", "read_file"))
        self.assertFalse(engine.is_tool_allowed("dev", "fs", "delete_file"))

    def test_blocked_tools_deny_even_if_in_allowed(self):
        engine = self._engine({
            "profiles": {
                "dev": {"servers": {"fs": {"tools": ["*"], "blocked_tools": ["rm_rf"]}}}
            }
        })
        self.assertFalse(engine.is_tool_allowed("dev", "fs", "rm_rf"))

    def test_network_explicit_host_allowed(self):
        engine = self._engine({
            "profiles": {
                "prod": {"servers": {"http": {"allow_network": ["api.example.com"]}}}
            }
        })
        self.assertTrue(engine.is_network_allowed("prod", "http", "api.example.com"))
        self.assertFalse(engine.is_network_allowed("prod", "http", "evil.example.com"))

    def test_unknown_profile_defaults_to_wildcard_allow(self):
        engine = self._engine({
            "profiles": {
                "dev": {"servers": {"fs": {"tools": ["read_file"]}}}
            }
        })
        # Unknown profile has no server config → tools defaults to ["*"] → all allowed
        self.assertTrue(engine.is_tool_allowed("unknown", "fs", "any_tool"))

    def test_reload_picks_up_updated_policy(self):
        from cherenkov.mcp.policy import PolicyEngine
        self.tmpdir = tempfile.mkdtemp()
        initial = {"profiles": {"dev": {"servers": {"fs": {"tools": ["read_file"]}}}}}
        path = _write_policy(self.tmpdir, initial)
        engine = PolicyEngine(policy_path=path)
        self.assertFalse(engine.is_tool_allowed("dev", "fs", "write_file"))

        updated = {"profiles": {"dev": {"servers": {"fs": {"tools": ["*"]}}}}}
        _write_policy(self.tmpdir, updated)
        engine.reload()
        self.assertTrue(engine.is_tool_allowed("dev", "fs", "write_file"))
