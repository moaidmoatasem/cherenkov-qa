"""
CHERENKOV healing/diagnose.py — core diagnostics component for classifying stage failures.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from cherenkov.core.errors import get_logger

class FailureClass(str, Enum):
    AUTH_EXPIRY = "AUTH_EXPIRY"
    CONTRACT_DRIFT = "CONTRACT_DRIFT"
    GENERIC_FAILURE = "GENERIC_FAILURE"

class DiagnosisResult:
    """Represents the classified diagnostic output of a failed test run."""

    def __init__(
        self,
        failure_class: FailureClass,
        detail: str,
        missing_fields: Optional[list[str]] = None,
        added_fields: Optional[list[str]] = None,
        snapshot_existed: bool = False
    ):
        self.failure_class = failure_class
        self.detail = detail
        self.missing_fields = missing_fields or []
        self.added_fields = added_fields or []
        self.snapshot_existed = snapshot_existed

class Diagnoser:
    """Diagnoses test failures before any repair is suggested, ensuring high-quality classifications."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("DIAGNOSE", run_id)
        self.snapshots_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.cherenkov/snapshots"))

    def diagnose_failure(
        self,
        scenario_id: str,
        current_status: int,
        current_body: Any,
        test_name: str
    ) -> DiagnosisResult:
        """Determines the exact failure cause by comparing against historical snapshots."""
        self.log.info("diagnosing failure", scenario_id=scenario_id, status=current_status)

        snapshot_path = os.path.join(self.snapshots_dir, f"{scenario_id}.json")
        snapshot_existed = os.path.exists(snapshot_path)
        
        previous_status = None
        previous_keys = []

        if snapshot_existed:
            try:
                with open(snapshot_path, "r", encoding="utf-8") as f:
                    snapshot = json.load(f)
                    previous_status = snapshot.get("status")
                    previous_keys = snapshot.get("body_keys", [])
            except Exception as e:
                self.log.warning("failed to read snapshot", path=snapshot_path, error=str(e))

        # 1. AUTH_EXPIRY: was 200/201 (success), now 401
        if current_status == 401:
            # If we historically passed (status in 200, 201, 204), but now we got 401
            if previous_status in (200, 201, 204) or not snapshot_existed:
                detail = f"Test previously returned success ({previous_status or 'N/A'}), but now returned 401 Unauthorized."
                self.log.info("diagnosed AUTH_EXPIRY", detail=detail)
                return DiagnosisResult(
                    failure_class=FailureClass.AUTH_EXPIRY,
                    detail=detail,
                    snapshot_existed=snapshot_existed
                )

        # Parse current body shape keys
        current_keys = []
        if isinstance(current_body, dict):
            current_keys = list(current_body.keys())
        elif isinstance(current_body, list) and len(current_body) > 0 and isinstance(current_body[0], dict):
            current_keys = list(current_body[0].keys())

        # 2. CONTRACT_DRIFT: Snapshot exists, and keys differ
        if snapshot_existed and previous_keys:
            missing = [k for k in previous_keys if k not in current_keys]
            added = [k for k in current_keys if k not in previous_keys]

            if missing or added:
                detail = f"Response body shape changed vs historical snapshot. Missing: {missing}, Added: {added}."
                self.log.info("diagnosed CONTRACT_DRIFT", missing=missing, added=added)
                return DiagnosisResult(
                    failure_class=FailureClass.CONTRACT_DRIFT,
                    detail=detail,
                    missing_fields=missing,
                    added_fields=added,
                    snapshot_existed=True
                )

        # 3. GENERIC_FAILURE: Default fallback
        detail = f"Generic test assertion failure. Status code: {current_status}."
        self.log.info("diagnosed GENERIC_FAILURE", detail=detail)
        return DiagnosisResult(
            failure_class=FailureClass.GENERIC_FAILURE,
            detail=detail,
            snapshot_existed=snapshot_existed
        )

    def record_passing_snapshot(self, scenario_id: str, status: int, body: Any) -> None:
        """Stores the response status and shape keys of a successful test execution for subsequent diffing."""
        os.makedirs(self.snapshots_dir, exist_ok=True)
        snapshot_path = os.path.join(self.snapshots_dir, f"{scenario_id}.json")

        body_keys = []
        if isinstance(body, dict):
            body_keys = list(body.keys())
        elif isinstance(body, list) and len(body) > 0 and isinstance(body[0], dict):
            body_keys = list(body[0].keys())

        snapshot_data = {
            "scenario_id": scenario_id,
            "status": status,
            "body_keys": body_keys,
            "timestamp": int(time.time()) if 'time' in globals() else 0
        }

        try:
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2)
            self.log.info("recorded passing snapshot", path=snapshot_path, keys=body_keys)
        except Exception as e:
            self.log.error("failed to write snapshot", path=snapshot_path, error=str(e))
