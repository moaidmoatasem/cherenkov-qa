import unittest
from cherenkov.adapters.notifiers.teams import TeamsNotifier
from cherenkov.validate.github_exporter import GitHubExporter


class TestSprint3Integrations(unittest.TestCase):
    def test_teams_notifier_init(self):
        # Should initialize even without webhook url
        notifier = TeamsNotifier()
        self.assertIsNone(notifier.webhook_url)

    def test_github_exporter_init(self):
        # Should initialize
        exporter = GitHubExporter()
        self.assertEqual(exporter.token, "")
        self.assertEqual(exporter.repo, "")

    def test_github_create_no_auth(self):
        exporter = GitHubExporter()
        result = exporter.create_github_issue("Title", "Body")
        self.assertIsNone(result)

    def test_teams_send_no_auth(self):
        notifier = TeamsNotifier()
        result = notifier.send_report(
            {"execution_key": "123", "items": [{"status": "FAIL"}]}
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
