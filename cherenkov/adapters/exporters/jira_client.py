from __future__ import annotations

import os
import requests
from requests.auth import HTTPBasicAuth
from typing import Any, Literal

from cherenkov.core.errors import get_logger


class JiraClient:
    """Real Jira API v3 integration."""

    def __init__(self, url: str | None = None, email: str | None = None, token: str | None = None):
        self.url = (url or os.getenv("CHERENKOV_JIRA_URL", "")).rstrip("/")
        self.email = email or os.getenv("CHERENKOV_JIRA_EMAIL")
        self.token = token or os.getenv("CHERENKOV_JIRA_TOKEN")
        self._log = get_logger("JIRA_CLIENT")

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.email and self.token)

    def _get_auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth(self.email, self.token)  # type: ignore

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        assignee: str | None = None,
        labels: list[str] | None = None,
        priority: str = "High",
    ) -> dict[str, Any]:
        """Creates a Jira issue (Bug) using Jira REST API v3."""
        if not self.is_configured:
            raise ValueError("Jira credentials not configured")

        endpoint = f"{self.url}/rest/api/3/issue"
        
        # Create a simple ADF document with the description text in a codeblock for preserving formatting
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "codeBlock",
                            "attrs": {
                                "language": "markdown"
                            },
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Bug"},
                "labels": labels or ["api-conformance", "cherenkov"]
            }
        }

        # Optional fields
        if assignee:
            payload["fields"]["assignee"] = {"id": assignee}
            
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=self._get_auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            self._log.info("Jira issue created", issue_key=data.get("key"))
            return data
        except requests.RequestException as exc:
            self._log.error("Failed to create Jira issue", error=str(exc), response=getattr(exc.response, "text", None))
            raise

    def link_test_run(
        self,
        issue_key: str,
        verdict_id: str,
        link_type: str = "Relates"
    ) -> None:
        """Links a CHERENKOV test verdict to a Jira issue."""
        if not self.is_configured:
            raise ValueError("Jira credentials not configured")
            
        endpoint = f"{self.url}/rest/api/3/issue/{issue_key}/comment"
        
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Linked CHERENKOV Test Verdict: {verdict_id}"
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=self._get_auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            self._log.info("Linked test run to Jira issue", issue_key=issue_key, verdict_id=verdict_id)
        except requests.RequestException as exc:
            self._log.error("Failed to link test run to Jira issue", error=str(exc))
            raise

    def transition_issue(
        self,
        issue_key: str,
        transition: Literal["In Progress", "Done", "Won't Fix"],
    ) -> None:
        """Transitions a Jira issue."""
        if not self.is_configured:
            raise ValueError("Jira credentials not configured")
            
        # 1. Get available transitions
        transitions_endpoint = f"{self.url}/rest/api/3/issue/{issue_key}/transitions"
        try:
            resp = requests.get(
                transitions_endpoint,
                auth=self._get_auth(),
                headers={"Accept": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            transitions_data = resp.json().get("transitions", [])
            
            # Find the ID for the requested transition name (case insensitive)
            transition_id = None
            for t in transitions_data:
                if t.get("name", "").lower() == transition.lower():
                    transition_id = t.get("id")
                    break
                    
            if not transition_id:
                raise ValueError(f"Transition '{transition}' not found for issue {issue_key}")
                
            # 2. Execute transition
            payload = {
                "transition": {
                    "id": transition_id
                }
            }
            exec_resp = requests.post(
                transitions_endpoint,
                json=payload,
                auth=self._get_auth(),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10
            )
            exec_resp.raise_for_status()
            self._log.info("Transitioned Jira issue", issue_key=issue_key, transition=transition)
        except requests.RequestException as exc:
            self._log.error("Failed to transition Jira issue", error=str(exc))
            raise
