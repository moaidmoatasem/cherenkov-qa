import unittest
from unittest.mock import patch, MagicMock

from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity
from cherenkov.adapters.notifiers.registry import NotifierRegistry
from cherenkov.adapters.notifiers.slack import SlackNotifier
from cherenkov.adapters.notifiers.teams import TeamsNotifier
from cherenkov.adapters.notifiers.linear import LinearNotifier
from cherenkov.adapters.notifiers.webhook import WebhookNotifier
from cherenkov.adapters.notifiers.opsgenie import OpsGenieNotifier
from cherenkov.adapters.notifiers.pagerduty import PagerDutyNotifier


class StubNotifier:
    name = "stub"

    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.last_report = None
        self.last_event = None

    def send(self, report):
        self.last_report = report
        return self.should_succeed

    def notify_event(self, event):
        self.last_event = event


class TestNotifierRegistry(unittest.TestCase):

    def test_registry_register_and_list(self):
        registry = NotifierRegistry()
        notifier = StubNotifier()
        registry.register(notifier)
        self.assertEqual(registry.list_notifiers(), ["stub"])

    def test_registry_notify_all(self):
        registry = NotifierRegistry()
        notifier = StubNotifier(should_succeed=True)
        registry.register(notifier)
        report = {"execution_key": "run-1", "items": []}
        results = registry.notify_all(report)
        self.assertEqual(results, {"stub": True})
        self.assertEqual(notifier.last_report, report)

    def test_registry_notify_event_all(self):
        registry = NotifierRegistry()
        notifier = StubNotifier()
        registry.register(notifier)
        event = CHERENKOVEvent(
            category=EventCategory.PIPELINE,
            name="pipeline.start",
            payload={"run_id": "r1"},
        )
        registry.notify_event_all(event)
        self.assertEqual(notifier.last_event, event)

    def test_registry_get_existing(self):
        registry = NotifierRegistry()
        notifier = StubNotifier()
        registry.register(notifier)
        self.assertIs(registry.get("stub"), notifier)

    def test_registry_get_missing_returns_none(self):
        registry = NotifierRegistry()
        self.assertIsNone(registry.get("nonexistent"))

    @patch.dict("os.environ", {
        "CHERENKOV_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        "CHERENKOV_TEAMS_WEBHOOK_URL": "https://outlook.office.com/test",
        "CHERENKOV_LINEAR_API_KEY": "lin-key",
        "CHERENKOV_WEBHOOK_URL": "https://example.com/hook",
        "CHERENKOV_OPSGENIE_API_KEY": "og-key",
        "CHERENKOV_PAGERDUTY_ROUTING_KEY": "pd-key",
    })
    def test_registry_from_env_auto_discovers(self):
        registry = NotifierRegistry.from_env()
        names = registry.list_notifiers()
        self.assertIn("slack", names)
        self.assertIn("teams", names)
        self.assertIn("linear", names)
        self.assertIn("webhook", names)
        self.assertIn("opsgenie", names)
        self.assertIn("pagerduty", names)

    def test_slack_notifier_has_name(self):
        self.assertEqual(SlackNotifier.name, "slack")

    @patch.object(TeamsNotifier, "send_report", return_value=True)
    def test_teams_notifier_send_delegates(self, mock_send_report):
        notifier = TeamsNotifier(webhook_url="https://example.com")
        result = notifier.send({"execution_key": "run-1"})
        mock_send_report.assert_called_once_with({"execution_key": "run-1"})
        self.assertTrue(result)

    def test_linear_notifier_name_attribute(self):
        self.assertEqual(LinearNotifier.name, "linear")

    @patch.object(WebhookNotifier, "notify")
    def test_webhook_notifier_send_delegates(self, mock_notify):
        notifier = WebhookNotifier(webhook_url="https://example.com/hook")
        result = notifier.send({"command": "test", "data": "hello"})
        mock_notify.assert_called_once()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()