import os
import time
import json
import urllib.request
from typing import List, Optional

from cherenkov.core.errors import get_logger


class LinearExporter:
    """Generates sandboxed, copy-ready Linear issue payloads inside .cherenkov/linear_tickets/ on test execution failure."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "linear_export"
        self.log = get_logger("LINEAR_EXPORTER", self.run_id)
        self.ticket_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../.cherenkov/linear_tickets")
        )

    def format_ticket(
        self,
        scenario_id: str,
        failure_class: str,
        error_message: str,
        expected_status: Optional[str | int] = None,
        received_status: Optional[str | int] = None,
        hypothesis: Optional[str] = None,
        resolution_steps: Optional[List[str]] = None,
        similar_cases_count: int = 0,
    ) -> str:
        """Formats failed scenario information into a descriptive Markdown ticket payload for Linear."""
        lines = []
        lines.append("## 🔍 Incident Details")
        lines.append(f"- **Scenario ID**: `{scenario_id}`")
        lines.append(f"- **Failure Classification**: `{failure_class}`")
        if expected_status is not None or received_status is not None:
            lines.append(
                f"- **HTTP Conformance**: Expected `{expected_status}` | Received `{received_status}`"
            )
        lines.append(
            f"- **Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`"
        )
        lines.append("")
        lines.append("### ❌ Error Message")
        lines.append("```text")
        lines.append(error_message.strip())
        lines.append("```")
        lines.append("")

        if hypothesis:
            lines.append("## 🧠 AI Root-Cause Hypothesis")
            lines.append(f"> {hypothesis}")
            lines.append("")

        if resolution_steps:
            lines.append("### 🛠️ Actionable Resolution Steps")
            for i, step in enumerate(resolution_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if similar_cases_count > 0:
            lines.append(
                f"- Found **{similar_cases_count}** similar historical failure(s) in local DB."
            )

        lines.append("\n*Report generated automatically by CHERENKOV QA.*")
        return "\n".join(lines)

    def export_ticket(
        self,
        scenario_id: str,
        failure_class: str,
        error_message: str,
        expected_status: Optional[str | int] = None,
        received_status: Optional[str | int] = None,
        hypothesis: Optional[str] = None,
        resolution_steps: Optional[List[str]] = None,
        similar_cases_count: int = 0,
    ) -> str:
        """Writes the formatted copy-ready Markdown ticket to the standard local ticket directory."""
        os.makedirs(self.ticket_dir, exist_ok=True)
        filename = f"linear_ticket_{scenario_id}_{int(time.time())}.md"
        file_path = os.path.join(self.ticket_dir, filename)

        ticket_content = self.format_ticket(
            scenario_id,
            failure_class,
            error_message,
            expected_status,
            received_status,
            hypothesis,
            resolution_steps,
            similar_cases_count,
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                f"# 🛑 CHERENKOV QA — DRIFT DETECTED: {scenario_id}\n\n{ticket_content}"
            )

        self.log.info(
            "suggest-only linear ticket exported successfully",
            filename=filename,
            path=file_path,
        )
        return file_path

    def create_linear_issue(self, title: str, description: str) -> Optional[str]:
        """Creates a real Linear issue using the Linear GraphQL API if API key is present."""
        linear_key = os.environ.get("CHERENKOV_LINEAR_API_KEY")
        team_id = os.environ.get("CHERENKOV_LINEAR_TEAM_ID")

        if not linear_key or not team_id:
            self.log.warning(
                "Linear API Key or Team ID not set. Skipping real Linear issue creation."
            )
            return None

        url = "https://api.linear.app/graphql"
        headers = {"Authorization": linear_key, "Content-Type": "application/json"}

        query = """
        mutation IssueCreate($title: String!, $description: String, $teamId: String!) {
          issueCreate(input: {
            title: $title,
            description: $description,
            teamId: $teamId
          }) {
            success
            issue {
              id
              identifier
              url
            }
          }
        }
        """

        payload = {
            "query": query,
            "variables": {
                "title": title,
                "description": description,
                "teamId": team_id,
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if "errors" in res_data:
                    self.log.error(f"Linear GraphQL error: {res_data['errors']}")
                    return None

                issue_data = (
                    res_data.get("data", {}).get("issueCreate", {}).get("issue", {})
                )
                issue_identifier = issue_data.get("identifier")
                self.log.info(
                    "Linear issue created successfully", identifier=issue_identifier
                )
                return issue_identifier
        except Exception as e:
            self.log.error("Failed to create Linear issue", error=str(e))
            raise e
