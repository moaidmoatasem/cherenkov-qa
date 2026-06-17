"""
CHERENKOV adapters/exporters/xray_exporter.py — Xray Cloud test execution importer.

Exports CHERENKOV conformance verdicts as Xray Cloud test execution results via
the Xray Cloud REST API v2. Xray accepts JUnit XML imports which maps cleanly
onto our existing JUnit emitter.

References:
  https://docs.getxray.app/display/XRAYCLOUDDOCUMENTATION/Import+Execution+Results

Environment variables:
  CHERENKOV_XRAY_CLIENT_ID     — Xray Cloud client ID
  CHERENKOV_XRAY_CLIENT_SECRET — Xray Cloud client secret
  CHERENKOV_XRAY_PROJECT_KEY   — Jira project key (e.g. "QA")
"""
from __future__ import annotations

import os
import requests
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.execution.emitters.junit import emit_junit


XRAY_AUTH_URL = "https://xray.cloud.getxray.app/api/v2/authenticate"
XRAY_IMPORT_URL = "https://xray.cloud.getxray.app/api/v2/import/execution/junit"


class XrayExporter:
    """Exports CHERENKOV verdicts as Xray Cloud test execution results via JUnit XML import."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        project_key: str | None = None,
    ) -> None:
        self.client_id = client_id or os.getenv("CHERENKOV_XRAY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("CHERENKOV_XRAY_CLIENT_SECRET", "")
        self.project_key = project_key or os.getenv("CHERENKOV_XRAY_PROJECT_KEY", "QA")
        self._log = get_logger("XRAY_EXPORTER")
        self._token: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authenticate(self) -> str:
        """Obtain a bearer token from Xray Cloud. Cached per-instance."""
        if self._token:
            return self._token
        resp = requests.post(
            XRAY_AUTH_URL,
            json={"client_id": self.client_id, "client_secret": self.client_secret},
            timeout=10,
        )
        resp.raise_for_status()
        # Xray returns the token as a plain JSON string (with quotes)
        self._token = resp.json() if isinstance(resp.json(), str) else resp.text.strip('"')
        return self._token

    def import_execution(
        self,
        results: dict[str, Any],
        test_plan_key: str | None = None,
        environment: str = "CI",
        spec_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert CHERENKOV results to JUnit XML and upload to Xray Cloud.

        Args:
            results:       Validation results dict (with "reports" list).
            test_plan_key: Optional Xray test plan key to associate the run.
            environment:   Environment label (e.g. "CI", "staging").
            spec_path:     Optional spec path forwarded to JUnit emitter.

        Returns:
            Xray API response dict with the created test execution key.
        """
        if not self.is_configured:
            raise ValueError("Xray credentials not configured. Set CHERENKOV_XRAY_CLIENT_ID and _SECRET.")

        junit_xml = emit_junit(results, spec_path=spec_path)
        token = self.authenticate()

        params: dict[str, str] = {
            "projectKey": self.project_key,
        }
        if test_plan_key:
            params["testPlanKey"] = test_plan_key
        if environment:
            params["testEnvironments"] = environment

        resp = requests.post(
            XRAY_IMPORT_URL,
            params=params,
            data=junit_xml.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/xml",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Xray execution imported", key=data.get("key"), project=self.project_key)
        return data
