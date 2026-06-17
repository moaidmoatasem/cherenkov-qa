"""
CHERENKOV adapters/exporters/zephyr_exporter.py — Zephyr Scale test execution importer.

Exports CHERENKOV conformance verdicts as Zephyr Scale (SmartBear) test cycle
executions via the Zephyr Scale Cloud REST API v2. Accepts JUnit XML which maps
cleanly onto our existing JUnit emitter.

References:
  https://support.smartbear.com/zephyr-scale-cloud/api-docs/

Environment variables:
  CHERENKOV_ZEPHYR_TOKEN       — Zephyr Scale API token
  CHERENKOV_ZEPHYR_PROJECT_KEY — Jira project key (e.g. "QA")
  CHERENKOV_ZEPHYR_BASE_URL    — Optional override (default: SmartBear cloud)
"""
from __future__ import annotations

import os
import requests
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.execution.emitters.junit import emit_junit


ZEPHYR_DEFAULT_BASE = "https://api.zephyrscale.smartbear.com/v2"


class ZephyrExporter:
    """Exports CHERENKOV verdicts as Zephyr Scale Cloud test execution results via JUnit XML import."""

    def __init__(
        self,
        token: str | None = None,
        project_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.token = token or os.getenv("CHERENKOV_ZEPHYR_TOKEN", "")
        self.project_key = project_key or os.getenv("CHERENKOV_ZEPHYR_PROJECT_KEY", "QA")
        self.base_url = (base_url or os.getenv("CHERENKOV_ZEPHYR_BASE_URL", ZEPHYR_DEFAULT_BASE)).rstrip("/")
        self._log = get_logger("ZEPHYR_EXPORTER")

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def import_execution(
        self,
        results: dict[str, Any],
        test_cycle_name: str = "CHERENKOV Conformance Run",
        environment_name: str | None = None,
        spec_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert CHERENKOV results to JUnit XML and upload to Zephyr Scale Cloud.

        Zephyr Scale accepts JUnit XML at POST /automations/executions/junit.

        Args:
            results:          Validation results dict (with "reports" list).
            test_cycle_name:  Name for the created test cycle in Zephyr.
            environment_name: Optional environment label.
            spec_path:        Optional spec path forwarded to JUnit emitter.

        Returns:
            Zephyr API response dict.
        """
        if not self.is_configured:
            raise ValueError("Zephyr token not configured. Set CHERENKOV_ZEPHYR_TOKEN.")

        junit_xml = emit_junit(results, spec_path=spec_path)

        params: dict[str, str] = {
            "projectKey": self.project_key,
            "autoCreateTestCases": "true",
        }
        if test_cycle_name:
            params["testCycleName"] = test_cycle_name
        if environment_name:
            params["environmentName"] = environment_name

        url = f"{self.base_url}/automations/executions/junit"
        resp = requests.post(
            url,
            params=params,
            data=junit_xml.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/xml",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info(
            "Zephyr execution imported",
            test_cycle=data.get("testCycle", {}).get("key"),
            project=self.project_key,
        )
        return data
