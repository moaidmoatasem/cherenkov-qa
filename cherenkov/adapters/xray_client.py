"""
cherenkov/adapters/xray_client.py — Xray Cloud & Server test execution import.

Imports CHERENKOV validation results into Xray Cloud or Xray Server (Jira DC)
after each `cherenkov validate` run. Triggered automatically when
CHERENKOV_XRAY_* env vars are set.

Closes: #450
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

CHERENKOV_TO_XRAY: dict[str, str] = {
    "PASS": "PASSED",
    "FAIL": "FAILED",
    "DRIFT": "FAILED",
    "SKIP": "ABORTED",
    "ERROR": "ABORTED",
}


class XrayCloudConfig(BaseModel):
    client_id: str
    client_secret: str
    base_url: str = "https://xray.cloud.getxray.app/api/v2"


class XrayServerConfig(BaseModel):
    base_url: str
    token: str
    project_key: str


class XrayClient:
    """Imports CHERENKOV test execution results into Xray Cloud or Xray Server."""

    def __init__(
        self,
        config: XrayCloudConfig | XrayServerConfig,
        timeout: int = 30,
    ) -> None:
        self.config = config
        self.timeout = timeout
        self._cloud_token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _authenticate_cloud(self) -> str:
        if self._cloud_token:
            return self._cloud_token
        cfg = self.config
        assert isinstance(cfg, XrayCloudConfig)
        resp = httpx.post(
            f"{cfg.base_url}/authenticate",
            json={"client_id": cfg.client_id, "client_secret": cfg.client_secret},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        self._cloud_token = resp.json()
        return self._cloud_token  # type: ignore[return-value]

    def _headers(self) -> dict[str, str]:
        if isinstance(self.config, XrayCloudConfig):
            token = self._authenticate_cloud()
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def import_execution(
        self,
        report: dict[str, Any],
        project_key: str,
        test_plan_key: str | None = None,
    ) -> dict[str, str]:
        """Convert a CHERENKOV DivergenceReport dict and POST to Xray."""
        payload = self._build_payload(report, project_key, test_plan_key)
        if isinstance(self.config, XrayCloudConfig):
            url = f"{self.config.base_url}/import/execution"
        else:
            url = f"{self.config.base_url}/rest/raven/1.0/import/execution"

        resp = httpx.post(
            url,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def import_junit_xml(self, junit_xml_path: str, project_key: str) -> dict[str, str]:
        """Import a JUnit XML file directly (Xray native format)."""
        xml_content = Path(junit_xml_path).read_bytes()
        if isinstance(self.config, XrayCloudConfig):
            url = f"{self.config.base_url}/import/execution/junit"
            params = {"projectKey": project_key}
        else:
            url = f"{self.config.base_url}/rest/raven/1.0/import/execution/junit"
            params = {"projectKey": project_key}

        headers = self._headers()
        headers["Content-Type"] = "text/xml"
        resp = httpx.post(
            url,
            content=xml_content,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Payload builder ───────────────────────────────────────────────────────

    def _build_payload(
        self,
        report: dict[str, Any],
        project_key: str,
        test_plan_key: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        tests = []
        for item in report.get("items", report.get("divergences", [])):
            verdict = str(item.get("verdict", item.get("status", "SKIP"))).upper()
            xray_status = CHERENKOV_TO_XRAY.get(verdict, "ABORTED")
            endpoint = item.get("endpoint", item.get("path", "unknown"))
            method = item.get("method", "GET")
            tests.append(
                {
                    "testKey": item.get("test_key"),
                    "start": now,
                    "finish": now,
                    "status": xray_status,
                    "comment": f"{method} {endpoint} — {verdict}",
                }
            )

        payload: dict[str, Any] = {
            "testExecutionKey": report.get("execution_key"),
            "info": {
                "project": project_key,
                "summary": f"CHERENKOV conformance run — {now}",
                "startDate": now,
                "finishDate": now,
                "testPlanKey": test_plan_key,
            },
            "tests": [t for t in tests if t["testKey"]],
        }
        return payload

    # ── Factory from env ──────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> "XrayClient | None":
        """Build XrayClient from environment variables. Returns None if not configured."""
        client_id = os.getenv("CHERENKOV_XRAY_CLIENT_ID")
        client_secret = os.getenv("CHERENKOV_XRAY_CLIENT_SECRET")
        server_url = os.getenv("CHERENKOV_XRAY_SERVER_URL")
        server_token = os.getenv("CHERENKOV_XRAY_SERVER_TOKEN")

        if client_id and client_secret:
            cfg = XrayCloudConfig(client_id=client_id, client_secret=client_secret)
            return cls(cfg)
        if server_url and server_token:
            project_key = os.getenv("CHERENKOV_XRAY_PROJECT_KEY", "")
            cfg = XrayServerConfig(
                base_url=server_url, token=server_token, project_key=project_key
            )
            return cls(cfg)
        return None
