"""
CHERENKOV validate/jira_exporter.py — Suggest-Only Jira Ticket Exporter.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from cherenkov.core.errors import get_logger


class JiraExporter:
    """Generates sandboxed, copy-ready Jira issue payloads inside .cherenkov/jira_tickets/ on test execution failure."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "jira_export"
        self.log = get_logger("JIRA_EXPORTER", self.run_id)
        self.ticket_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.cherenkov/jira_tickets"))

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
        compliance_score: Optional[int] = None
    ) -> str:
        """Formats failed scenario information into a highly descriptive Markdown ticket payload."""
        lines = []
        lines.append(f"# 🛑 CHERENKOV QA — DRIFT DETECTED: {scenario_id}")
        lines.append("")
        lines.append("## 🔍 Incident Details")
        lines.append(f"- **Scenario ID**: `{scenario_id}`")
        lines.append(f"- **Failure Classification**: `{failure_class}`")
        if expected_status is not None or received_status is not None:
            lines.append(f"- **HTTP Conformance**: Expected `{expected_status}` | Received `{received_status}`")
        lines.append(f"- **Timestamp**: `{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}`")
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

        lines.append("### 📚 RAG Incident Correlation")
        if similar_cases_count > 0:
            lines.append(f"- Found **{similar_cases_count}** similar historical failure(s) in local SQLite database.")
        else:
            lines.append("- No similar historical failure cases detected in RAG index.")
        lines.append("")

        if compliance_score is not None:
            lines.append("## 🔒 Cybersecurity Compliance Status")
            lines.append(f"- **MENA Regulatory Score**: `{compliance_score}%`")
            lines.append("  *Maps active header configurations and spec structures directly to SAMA CCSF and CBE FinCSF guidelines.*")
            lines.append("")

        lines.append("---")
        lines.append("*Report generated automatically by CHERENKOV QA (v3.1 + delta).*")
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
        compliance_score: Optional[int] = None
    ) -> str:
        """Writes the formatted copy-ready Markdown ticket to the standard local ticket directory."""
        os.makedirs(self.ticket_dir, exist_ok=True)
        filename = f"jira_ticket_{scenario_id}_{int(time.time())}.md"
        file_path = os.path.join(self.ticket_dir, filename)

        ticket_content = self.format_ticket(
            scenario_id=scenario_id,
            failure_class=failure_class,
            error_message=error_message,
            expected_status=expected_status,
            received_status=received_status,
            hypothesis=hypothesis,
            resolution_steps=resolution_steps,
            similar_cases_count=similar_cases_count,
            compliance_score=compliance_score
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ticket_content)

        self.log.info("suggest-only jira ticket exported successfully", filename=filename, path=file_path)
        return file_path

    def create_jira_issue(self, summary: str, description: str) -> Optional[str]:
        import base64
        import urllib.request
        import json

        jira_url = os.environ.get("CHERENKOV_JIRA_URL")
        jira_token = os.environ.get("CHERENKOV_JIRA_TOKEN")
        jira_project = os.environ.get("CHERENKOV_JIRA_PROJECT", "QA")

        if not jira_url or not jira_token:
            self.log.warning("Jira URL or Token not set. Skipping real Jira ticket creation.")
            return None

        url = f"{jira_url.rstrip('/')}/rest/api/3/issue"

        # Prepare auth header
        if ":" in jira_token:
            auth_bytes = jira_token.encode("utf-8")
            auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
            headers = {"Authorization": f"Basic {auth_b64}"}
        elif jira_token.startswith("Basic ") or jira_token.startswith("Bearer "):
            headers = {"Authorization": jira_token}
        else:
            headers = {"Authorization": f"Bearer {jira_token}"}

        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        # Payload for Jira REST API v3
        payload = {
            "fields": {
                "project": {"key": jira_project},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": "Bug"}
            }
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
                issue_key = res_data.get("key")
                self.log.info("Jira issue created successfully", key=issue_key)
                return issue_key
        except Exception as e:
            self.log.error("Failed to create Jira issue", error=str(e))
            raise e