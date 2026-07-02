from __future__ import annotations

import logging
import subprocess

_log = logging.getLogger(__name__)

from cherenkov.execution.mobile_runner_base import MobileRunnerBase


class MaestroRunner(MobileRunnerBase):
    def __init__(self, maestro_binary: str = "maestro"):
        self.maestro_binary = maestro_binary

    def run_test(self, yaml_path: str) -> dict:
        if self.dry_run:
            return self._dry_run_result(yaml_path)
        result = subprocess.run(
            [self.maestro_binary, "test", yaml_path],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def run_directory(self, directory: str) -> dict:
        if self.dry_run:
            return self._dry_run_result(directory)
        result = subprocess.run(
            [self.maestro_binary, "test", directory],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def health_check(self) -> bool:
        if self.dry_run:
            return True
        try:
            result = subprocess.run(
                [self.maestro_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
        except Exception:
            _log.warning("Unexpected error in maestro health_check", exc_info=True)
            return False
