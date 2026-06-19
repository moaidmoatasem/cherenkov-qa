import os
import json
import tempfile
import unittest

from cherenkov.adapters.notifiers.slack import SlackNotifier
from cherenkov.validate.asyncapi import AsyncAPIParser
from cherenkov.validate.buf_registry import BufRegistryClient

class TestSprint6Integrations(unittest.TestCase):
    def test_slack_notifier(self):
        notifier = SlackNotifier()
        self.assertIsNone(notifier.webhook_url)

        # Test with no failures (should return False because no webhook URL)
        result = notifier.send_report({"items": [{"status": "PASS"}]})
        self.assertFalse(result)

        # Test with failures
        result = notifier.send_report({"items": [{"status": "FAIL"}]})
        self.assertFalse(result)

    def test_asyncapi_parser(self):
        mock_yaml = """
asyncapi: 2.6.0
info:
  title: Test API
  version: 1.0.0
channels:
  user/signedup:
    publish:
      message:
        payload:
          type: object
  user/deleted:
    subscribe:
      message:
        payload:
          type: object
        """
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
            f.write(mock_yaml)
            temp_path = f.name
            
        try:
            parser = AsyncAPIParser()
            scenarios = parser.parse_spec(temp_path)
            self.assertEqual(len(scenarios), 2)
            
            publish_scenario = next(s for s in scenarios if s.method == "PUBLISH")
            self.assertEqual(publish_scenario.endpoint, "user/signedup")
            
            subscribe_scenario = next(s for s in scenarios if s.method == "SUBSCRIBE")
            self.assertEqual(subscribe_scenario.endpoint, "user/deleted")
        finally:
            os.remove(temp_path)

    def test_buf_registry_client(self):
        client = BufRegistryClient()
        self.assertIsNone(client.token)
        
        result = client.fetch_schema("acme/paymentapis")
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
