"""
CHERENKOV validate/jira_exporter.py - Suggest-Only Jira Ticket Exporter.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional

from cherenkov.core.errors import get_logger


class JiraExporter:
    """Generates sandboxed, copy-ready Jira issue payloads inside .cherenkov/jira_tickets/ on test execution failure."""

    def __init__(
        self,
        run_id: str | None = None,
        jira_url: str | None = None,
        jira_token: str | None = None,
        jira_project: str | None = None,
    ):
        self.run_id = run_id or "jira_export"
        self.log = get_logger("JIRA_EXPORTER", self.run_id)
        self.ticket_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../.cherenkov/jira_tickets")
        )
        self.jira_url = jira_url or os.environ.get("CHERENKOV_JIRA_URL")
        self.jira_token = jira_token or os.environ.get("CHERENKOV_JIRA_TOKEN")
        self.jira_project = jira_project or os.environ.get("CHERENKOV_JIRA_PROJECT", "QA")

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
        compliance_score: Optional[int] = None,
    ) -> str:
        """Formats failed scenario information into a highly descriptive Markdown ticket payload."""
        lines = []
        lines.append(f"# \U0001f6d1 CHERENKOV QA \u2014 DRIFT DETECTED: {scenario_id}")
        lines.append("")
        lines.append("## \U0001f50d Incident Details")
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

        lines.append("### \u274c Error Message")
        lines.append("```text")
        lines.append(error_message.strip())
        lines.append("```")
        lines.append("")

        if hypothesis:
            lines.append("## \U0001f9e0 AI Root-Cause Hypothesis")
            lines.append(f"> {hypothesis}")
            lines.append("")

        if resolution_steps:
            lines.append("### \U0001f6e0\ufe0f Actionable Resolution Steps")
            for i, step in enumerate(resolution_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        lines.append("### \U0001f4da RAG Incident Correlation")
        if similar_cases_count > 0:
            lines.append(
                f"- Found **{similar_cases_count}** similar historical failure(s) in local SQLite database."
            )
        else:
            lines.append("- No similar historical failure cases detected in RAG index.")
        lines.append("")

        if compliance_score is not None:
            lines.append("## \U0001f512 Cybersecurity Compliance Status")
            lines.append(f"- **MENA Regulatory Score**: `{compliance_score}%`")
            lines.append(
                "  *Maps active header configurations and spec structures directly to SAMA CCSF and CBE FinCSF guidelines.*"
            )
            lines.append("")

        lines.append("---")
        lines.append("*Report generated automatically by CHERENKOV QA.*")
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
        compliance_score: Optional[int] = None,
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
            compliance_score=compliance_score,
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ticket_content)

        self.log.info(
            "suggest-only jira ticket exported successfully",
            filename=filename,
            path=file_path,
        )
        return file_path

    def create_jira_issue(self, summary: str, description: str) -> Optional[str]:
        import base64
        import urllib.request
        import json

        jira_url = os.environ.get("CHERENKOV_JIRA_URL")
        jira_token = os.environ.get("CHERENKOV_JIRA_TOKEN")
        jira_project = os.environ.get("CHERENKOV_JIRA_PROJECT", "QA")

        if not jira_url or not jira_token:
            self.log.warning(
                "Jira URL or Token not set. Skipping real Jira ticket creation."
            )
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
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
            }
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
                issue_key = res_data.get("key")
                self.log.info("Jira issue created successfully", key=issue_key)
                return issue_key
        except Exception as e:
            self.log.error("Failed to create Jira issue", error=str(e))
            raise e

    def _build_auth_headers(self, content_type="application/json"):
        import base64

        if not self.jira_url or not self.jira_token:
            return None

        if ":" in self.jira_token:
            auth_bytes = self.jira_token.encode("utf-8")
            auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")
            headers = {"Authorization": f"Basic {auth_b64}"}
        elif self.jira_token.startswith("Basic ") or self.jira_token.startswith("Bearer "):
            headers = {"Authorization": self.jira_token}
        else:
            headers = {"Authorization": f"Bearer {self.jira_token}"}

        if content_type:
            headers["Content-Type"] = content_type
        if content_type == "application/json":
            headers["Accept"] = "application/json"
        return headers

    def create_jira_issue_full(
        self,
        summary: str,
        description: str,
        labels: List[str] | None = None,
        priority: dict | str | None = None,
        components: List[str] | None = None,
        issuetype: str = "Bug",
    ) -> Optional[str]:
        import urllib.request
        import json

        headers = self._build_auth_headers()
        if headers is None:
            self.log.warning(
                "Jira URL or Token not set. Skipping real Jira ticket creation."
            )
            return None

        url = f"{self.jira_url.rstrip('/')}/rest/api/3/issue"

        fields = {
            "project": {"key": self.jira_project},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issuetype},
        }

        if labels:
            fields["labels"] = labels

        if priority is not None:
            if isinstance(priority, dict):
                fields["priority"] = priority
            else:
                fields["priority"] = {"name": priority}

        if components:
            fields["components"] = [{"name": comp} for comp in components]

        payload = {"fields": fields}

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
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

    def bulk_create(self, items: List[dict]) -> List[str]:
        created_keys: List[str] = []
        for item in items:
            try:
                key = self.create_jira_issue_full(
                    summary=item.get("summary", ""),
                    description=item.get("description", ""),
                    labels=item.get("labels"),
                    priority=item.get("priority"),
                    components=item.get("components"),
                    issuetype=item.get("issuetype", "Bug"),
                )
                if key:
                    created_keys.append(key)
            except Exception as e:
                self.log.error("bulk_create failed for item", error=str(e))
        return created_keys

    def add_comment(self, issue_key: str, comment: str) -> bool:
        import urllib.request
        import json

        headers = self._build_auth_headers()
        if headers is None:
            self.log.warning("Jira URL or Token not set. Skipping add_comment.")
            return False

        url = f"{self.jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment"

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10):
                self.log.info("Comment added successfully", issue_key=issue_key)
                return True
        except Exception as e:
            self.log.error("Failed to add comment", issue_key=issue_key, error=str(e))
            return False

    def add_attachment(self, issue_key: str, file_path: str) -> bool:
        import urllib.request
        import mimetypes
        import uuid

        if not os.path.isfile(file_path):
            self.log.error("Attachment file not found", file_path=file_path)
            return False

        headers = self._build_auth_headers(content_type=None)
        if headers is None:
            self.log.warning("Jira URL or Token not set. Skipping add_attachment.")
            return False

        if "Content-Type" in headers:
            del headers["Content-Type"]
        if "Accept" in headers:
            del headers["Accept"]
        headers["X-Atlassian-Token"] = "no-check"

        url = f"{self.jira_url.rstrip('/')}/rest/api/3/issue/{issue_key}/attachments"

        filename = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        boundary = uuid.uuid4().hex

        with open(file_path, "rb") as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8")
            + file_data
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )

        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30):
                self.log.info("Attachment added successfully", issue_key=issue_key, file_path=file_path)
                return True
        except Exception as e:
            self.log.error("Failed to add attachment", issue_key=issue_key, error=str(e))
            return False
