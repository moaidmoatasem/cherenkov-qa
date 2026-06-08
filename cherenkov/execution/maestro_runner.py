from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

class MaestroRunner:
    def __init__(self, maestro_binary: str = "maestro"):
        self.maestro_binary = maestro_binary

    def run_test(self, yaml_path: str) -> dict:
        result = subprocess.run(
            [self.maestro_binary, "test", yaml_path],
            capture_output=True, text=True, timeout=300,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def run_directory(self, directory: str) -> dict:
        result = subprocess.run(
            [self.maestro_binary, "test", directory],
            capture_output=True, text=True, timeout=300,
        )
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def health_check(self) -> bool:
        try:
            result = subprocess.run([self.maestro_binary, "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
