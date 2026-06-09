from __future__ import annotations
from abc import ABC, abstractmethod
import os


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
        return {"status": "passed", "stdout": f"[DRY-RUN] {test_path}", "stderr": "", "dry_run": True}
