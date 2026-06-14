import os
import json
import urllib.request
from typing import Optional

class GitHubExporter:
    """Creates GitHub issues for failed validation items."""

    def __init__(self):
        self.token = os.environ.get("CHERENKOV_GITHUB_TOKEN", "")
        self.repo = os.environ.get("CHERENKOV_GITHUB_REPO", "") # Format: owner/repo

    def create_github_issue(self, title: str, body: str) -> Optional[str]:
        """Creates a real GitHub issue using the GitHub REST API if token is present."""
        if not self.token or not self.repo:
            return None

        url = f"https://api.github.com/repos/{self.repo}/issues"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json"
        }

        payload = {
            "title": title,
            "body": body,
            "labels": ["bug", "conformance-drift", "cherenkov-qa"]
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("html_url")
        except Exception:
            return None
