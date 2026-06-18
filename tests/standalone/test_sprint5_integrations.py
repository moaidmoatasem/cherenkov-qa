import os
import tempfile
import json
import unittest

from cherenkov.adapters.notifiers.pagerduty import PagerDutyNotifier
from cherenkov.adapters.notifiers.opsgenie import OpsGenieNotifier
from cherenkov.adapters.postman_importer import PostmanImporter


class TestSprint5Integrations(unittest.TestCase):
    def test_pagerduty_notifier(self):
        notifier = PagerDutyNotifier()
        self.assertIsNone(notifier.routing_key)

        # Test no failures
        result = notifier.send_report({"items": [{"status": "PASS"}]})
        self.assertFalse(result)  # Fails fast due to missing key

        # Test failures without key
        result = notifier.send_report({"items": [{"status": "FAIL"}]})
        self.assertFalse(result)

    def test_opsgenie_notifier(self):
        notifier = OpsGenieNotifier()
        self.assertIsNone(notifier.api_key)

        result = notifier.send_report({"items": [{"status": "FAIL"}]})
        self.assertFalse(result)

    def test_postman_importer(self):
        # Create a mock postman collection JSON
        mock_data = {
            "info": {"name": "Test Collection"},
            "item": [
                {
                    "name": "Get User",
                    "request": {
                        "method": "GET",
                        "url": {"raw": "https://api.example.com/users/1"},
                        "header": [{"key": "Authorization", "value": "Bearer test"}],
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(mock_data, f)
            temp_path = f.name

        try:
            importer = PostmanImporter()
            scenarios = importer.import_collection(temp_path)
            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0].method, "GET")
            self.assertEqual(scenarios[0].endpoint, "https://api.example.com/users/1")
            self.assertEqual(scenarios[0].expected_status, 200)
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
