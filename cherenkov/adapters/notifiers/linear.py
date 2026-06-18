from typing import Any, Dict, Optional
import os
import json
import urllib.request
from cherenkov.hitl.contracts import HitlEnvelope, ok_envelope
from cherenkov.core.events import CHERENKOVEvent
from cherenkov.core.errors import get_logger


class LinearNotifier:
    """Sends notifications to Linear via its GraphQL API."""

    name: str = "linear"

    def __init__(self, api_key: Optional[str] = None, team_id: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CHERENKOV_LINEAR_API_KEY")
        self.team_id = team_id or os.environ.get("CHERENKOV_LINEAR_TEAM_ID")
        self.log = get_logger("LINEAR_NOTIFIER")

    def notify(self, envelope: HitlEnvelope) -> bool:
        """Process an incoming HITL envelope and create a Linear issue if it's a failure.

        Returns True if no notification was needed or the issue was created
        successfully; False if Linear is unconfigured or the API call failed.
        """
        if not self.api_key or not self.team_id:
            self.log.debug(  # type: ignore
                "LinearNotifier skipped: CHERENKOV_LINEAR_API_KEY or TEAM_ID not set"
            )
            return False

        if envelope.ok:
            return True  # Only notify on failure

        # Format issue
        title = f"API Drift: {envelope.scenario_id or 'Unknown Endpoint'}"  # type: ignore
        description = (
            f"CHERENKOV detected an API conformance drift.\n\n"
            f"**Error**:\n{envelope.error.message if envelope.error else 'Unknown error'}\n\n"
            f"Please review the logs or the CHERENKOV dashboard for details."
        )

        query = """
        mutation IssueCreate($title: String!, $teamId: String!, $description: String) {
            issueCreate(input: {
                title: $title,
                teamId: $teamId,
                description: $description
            }) {
                success
                issue {
                    id
                    url
                }
            }
        }
        """

        variables = {"title": title, "teamId": self.team_id, "description": description}

        req = urllib.request.Request(
            "https://api.linear.app/graphql",
            data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": self.api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("data", {}).get("issueCreate", {}).get("success"):
                    issue_url = res_data["data"]["issueCreate"]["issue"]["url"]
                    self.log.info("Linear issue created successfully", url=issue_url)
                    return True
                self.log.error("Failed to create Linear issue", response=res_data)
                return False
        except Exception as e:
            self.log.error("Failed to call Linear API", error=str(e))
            return False

    def send(self, report: Dict[str, Any]) -> bool:
        envelope = ok_envelope(
            command=report.get("command", "notify"),
            payload=report,
        )
        return self.notify(envelope)

    def notify_event(self, event: CHERENKOVEvent) -> None:
        envelope = ok_envelope(
            command=event.name,
            payload=event.to_dict(),
        )
        self.notify(envelope)
