"""
Tests for cherenkov/mcp/policy.py – PolicyEngine.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from cherenkov.mcp.policy import PolicyEngine


SAMPLE_POLICY = {
    "version": "1.0",
    "profiles": {
        "test-profile": {
            "servers": {
                "test-server": {
                    "tools": ["allowed_tool", "another_tool"],
                    "blocked_tools": ["blocked_tool"],
                    "allow_network": ["api.example.com:443"],
                },
                "wildcard-server": {
                    "tools": ["*"],
                    "allow_network": ["*"],
                },
            }
        }
    },
    "invariants": {},
}


class TestPolicyEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(SAMPLE_POLICY, self.tmp)
        self.tmp.close()
        self.engine = PolicyEngine(policy_path=self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_policy_allows_known_tool(self):
        self.assertTrue(
            self.engine.is_tool_allowed("test-profile", "test-server", "allowed_tool")
        )

    def test_policy_blocks_unknown_tool(self):
        self.assertFalse(
            self.engine.is_tool_allowed("test-profile", "test-server", "unknown_tool")
        )

    def test_policy_allows_all_when_wildcard(self):
        self.assertTrue(
            self.engine.is_tool_allowed("test-profile", "wildcard-server", "anything")
        )

    def test_policy_blocks_tool_in_blocked_list(self):
        self.assertFalse(
            self.engine.is_tool_allowed("test-profile", "test-server", "blocked_tool")
        )

    def test_policy_network_allow(self):
        self.assertTrue(
            self.engine.is_network_allowed(
                "test-profile", "test-server", "api.example.com:443"
            )
        )

    def test_policy_network_block(self):
        self.assertFalse(
            self.engine.is_network_allowed(
                "test-profile", "test-server", "evil.example.com:443"
            )
        )

    def test_policy_reload_updates_runtime(self):
        old_allowed = self.engine.is_tool_allowed(
            "test-profile", "test-server", "new_tool"
        )
        self.assertFalse(old_allowed)

        updated = dict(SAMPLE_POLICY)
        updated["profiles"]["test-profile"]["servers"]["test-server"]["tools"].append(
            "new_tool"
        )
        with open(self.tmp.name, "w") as f:
            json.dump(updated, f)

        self.engine.reload()
        self.assertTrue(
            self.engine.is_tool_allowed("test-profile", "test-server", "new_tool")
        )

    def test_policy_missing_profile_defaults_to_permissive(self):
        self.assertTrue(
            self.engine.is_tool_allowed("nonexistent", "test-server", "anything")
        )


if __name__ == "__main__":
    unittest.main()
