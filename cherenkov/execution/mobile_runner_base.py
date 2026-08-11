from __future__ import annotations

import os
from abc import ABC, abstractmethod


class MobileRunnerBase(ABC):
    """Placeholder docstring.

<description>"""
    DRY_RUN_ENV = "CHERENKOV_MOBILE_DRY_RUN"

    @property
    def dry_run(self) -> bool:
        """Placeholder docstring.

:return: <description>"""
        return os.environ.get(self.DRY_RUN_ENV, "").lower() in ("1", "true", "yes")

    @abstractmethod
    def run_test(self, test_path: str) -> dict: ...
        """Placeholder docstring.

:param test_path: <description>
:return: <description>"""

    @abstractmethod
    def health_check(self) -> bool: ...
        """Placeholder docstring.

:return: <description>"""

    def _dry_run_result(self, test_path: str) -> dict:
        return {
            "status": "passed",
            "stdout": f"[DRY-RUN] {test_path}",
            "stderr": "",
            "dry_run": True,
        }
