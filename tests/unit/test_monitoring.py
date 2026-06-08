import json
import unittest

from cherenkov.web.monitoring import json_dumps, router


class TestMonitoringHelpers(unittest.TestCase):
    def test_json_dumps(self):
        data = {"status": "ok", "level": "healthy"}
        result = json_dumps(data)
        parsed = json.loads(result)
        self.assertEqual(parsed["status"], "ok")
        self.assertEqual(parsed["level"], "healthy")

    def test_router_has_routes(self):
        routes = [r.path for r in router.routes]
        self.assertIn("/healthz", routes)
        self.assertIn("/metrics", routes)
        self.assertIn("/api/v1/health/detail", routes)

    def test_router_routes_count(self):
        self.assertGreaterEqual(len(router.routes), 3)
