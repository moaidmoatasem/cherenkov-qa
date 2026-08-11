from __future__ import annotations

import os
from abc import ABC, abstractmethod


class MobileRunnerBase(ABC):
    DRY_RUN_ENV = "CHERENKOV_MOBILE_DRY_RUN"

    @property
    def dry_run(self) -> bool:
        return os.environ.get(self.DRY_RUN_ENV, "").lower() in ("1", "true", "yes")

    @abstractmethod
    def run_test(self, test_path: str) -> dict: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    def _dry_run_result(self, test_path: str) -> dict:
        """Result for a flow that was never put on a device.

        Status is ``skipped``, never ``passed``: a flow that did not execute has
        produced no evidence, and reporting it green is the exact fabrication
        this project exists to detect.
        """
        return {
            "status": "skipped",
            "executed": False,
            "reason": "dry-run (CHERENKOV_MOBILE_DRY_RUN set); no device involved",
            "stdout": f"[DRY-RUN] {test_path}",
            "stderr": "",
            "dry_run": True,
        }
