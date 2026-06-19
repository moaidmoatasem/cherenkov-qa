"""Unit tests for MCP mesh registry."""

import unittest


class TestMCPRegistry(unittest.TestCase):

    def setUp(self):
        from cherenkov.mcp.mesh_router import MCPRegistry
        self.reg = MCPRegistry()

    def test_register_server_returns_id(self):
        reg_id = self.reg.register_server(
            "test-srv", "http://localhost:8080/mcp", [{"name": "echo"}]
        )
        self.assertIsInstance(reg_id, str)
        self.assertEqual(len(reg_id), 12)

    def test_list_servers_empty_initially(self):
        servers = self.reg.list_servers()
        self.assertEqual(servers, [])

    def test_list_servers_after_register(self):
        self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        servers = self.reg.list_servers()
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["name"], "srv1")

    def test_register_multiple_servers(self):
        self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        self.reg.register_server(
            "srv2", "http://localhost:9090/mcp", [{"name": "tool2"}, {"name": "tool3"}]
        )
        servers = self.reg.list_servers()
        self.assertEqual(len(servers), 2)

    def test_unregister_server(self):
        reg_id = self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        self.assertTrue(self.reg.unregister_server(reg_id))
        self.assertEqual(len(self.reg.list_servers()), 0)

    def test_unregister_nonexistent_returns_false(self):
        self.assertFalse(self.reg.unregister_server("nonexistent"))

    def test_resolve_tool(self):
        self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "my_tool"}]
        )
        server = self.reg.resolve_tool("my_tool")
        self.assertIsNotNone(server)
        self.assertEqual(server.name, "srv1")

    def test_resolve_nonexistent_tool(self):
        self.assertIsNone(self.reg.resolve_tool("ghost_tool"))

    def test_get_combined_tools(self):
        self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool_a"}]
        )
        self.reg.register_server(
            "srv2", "http://localhost:9090/mcp", [{"name": "tool_b"}]
        )
        combined = self.reg.get_combined_tools()
        self.assertEqual(len(combined), 2)
        names = {t["name"] for t in combined}
        self.assertIn("tool_a", names)
        self.assertIn("tool_b", names)

    def test_get_server_returns_none_for_missing(self):
        self.assertIsNone(self.reg.get_server("does-not-exist"))

    def test_get_server_returns_registration(self):
        reg_id = self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        server = self.reg.get_server(reg_id)
        self.assertIsNotNone(server)
        self.assertEqual(server.url, "http://localhost:8080/mcp")

    def test_prune_stale(self):
        import time
        self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        # Force last_seen to the past
        for s in self.reg._servers.values():
            s.last_seen = 0
        pruned = self.reg.prune_stale(max_age_seconds=1)
        self.assertEqual(pruned, 1)
        self.assertEqual(len(self.reg.list_servers()), 0)

    def test_resolve_tool_after_unregister(self):
        reg_id = self.reg.register_server(
            "srv1", "http://localhost:8080/mcp", [{"name": "tool1"}]
        )
        self.reg.unregister_server(reg_id)
        self.assertIsNone(self.reg.resolve_tool("tool1"))


if __name__ == "__main__":
    unittest.main()
