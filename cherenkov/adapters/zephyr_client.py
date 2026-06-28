"""
cherenkov/adapters/zephyr_client.py — Zephyr Scale (SmartBear) test execution import.

Imports CHERENKOV validation results into Zephyr Scale after each
`cherenkov validate` run. Accepts JUnit XML (native Zephyr import) or
a structured CHERENKOV report dict.

Closes: #451
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

CHERENKOV_TO_ZEPHYR: dict[str, str] = {
    "PASS": "Pass",
    "FAIL": "Fail",
    "DRIFT": "Fail",
    "SKIP": "Not Executed",
    "ERROR": "Blocked",
}


class ZephyrConfig(BaseModel):
    token: str
    project_key: str
    base_url: str = "https://api.zephyrscale.smartbear.com/v2"


class ZephyrClient:
    """Import test execution results into Zephyr Scale (SmartBear)."""

    def __init__(self, config: ZephyrConfig, timeout: int = 30) -> None:
        self.config = config
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/json",
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def import_execution(
        self,
        report: dict[str, Any],
        test_cycle_name: str | None = None,
    ) -> dict[str, Any]:
        """Convert a CHERENKOV report dict and POST results to Zephyr Scale."""
        now = datetime.now(timezone.utc)
        cycle_name = (
            test_cycle_name or f"CHERENKOV run {now.strftime('%Y-%m-%d %H:%M')}"
        )
        cycle_key = self._create_test_cycle(cycle_name, now.isoformat())

        results = []
        for item in report.get("items", report.get("divergences", [])):
            verdict = str(item.get("verdict", item.get("status", "SKIP"))).upper()
            zephyr_status = CHERENKOV_TO_ZEPHYR.get(verdict, "Not Executed")
            test_case_key = item.get("test_case_key") or item.get("test_key")
            if not test_case_key:
                continue
            results.append(
                {
                    "testCaseKey": test_case_key,
                    "testCycleKey": cycle_key,
                    "statusName": zephyr_status,
                    "projectKey": self.config.project_key,
                    "comment": self._build_comment(item),
                    "executionTime": item.get("duration_ms", 0),
                }
            )

        if results:
            self._post_results(results)

        return {
            "testCycleKey": cycle_key,
            "resultsPosted": len(results),
            "cycleName": cycle_name,
        }

    def import_junit_xml(self, junit_xml_path: str) -> dict[str, Any]:
        """Import a JUnit XML file directly via Zephyr Scale's automation endpoint."""
        xml_content = Path(junit_xml_path).read_bytes()
        url = f"{self.config.base_url}/automations/executions/junit"
        headers = {
            "Authorization": f"Bearer {self.config.token}",
            "Content-Type": "application/xml",
        }
        params = {"projectKey": self.config.project_key, "autoCreateTestCases": "true"}
        resp = httpx.post(
            url,
            content=xml_content,
            headers=headers,
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _create_test_cycle(self, name: str, planned_start: str) -> str:
        url = f"{self.config.base_url}/testcycles"
        payload = {
            "name": name,
            "projectKey": self.config.project_key,
            "plannedStartDate": planned_start,
        }
        resp = httpx.post(
            url, json=payload, headers=self._headers(), timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()["key"]

    def _post_results(self, results: list[dict[str, Any]]) -> None:
        url = f"{self.config.base_url}/testexecutions"
        for result in results:
            resp = httpx.post(
                url, json=result, headers=self._headers(), timeout=self.timeout
            )
            resp.raise_for_status()

    @staticmethod
    def _build_comment(item: dict[str, Any]) -> str:
        endpoint = item.get("endpoint", item.get("path", ""))
        method = item.get("method", "GET")
        verdict = item.get("verdict", item.get("status", ""))
        summary = item.get("summary", item.get("message", ""))
        parts = [f"{method} {endpoint}" if endpoint else "", verdict, summary]
        return " — ".join(p for p in parts if p)

    # ── Factory from env ──────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> ZephyrClient | None:
        """Build ZephyrClient from environment variables. Returns None if not configured."""
        token = os.getenv("CHERENKOV_ZEPHYR_TOKEN")
        project_key = os.getenv("CHERENKOV_ZEPHYR_PROJECT_KEY")
        if not token or not project_key:
            return None
        base_url = os.getenv(
            "CHERENKOV_ZEPHYR_BASE_URL", "https://api.zephyrscale.smartbear.com/v2"
        )
        cfg = ZephyrConfig(token=token, project_key=project_key, base_url=base_url)
        return cls(cfg)
