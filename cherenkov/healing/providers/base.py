"""
CHERENKOV healing/providers/base.py — SandboxProvider abstract base.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SandboxResult:
    passed: bool = False
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""


class SandboxProvider(ABC):
    @abstractmethod
    def replicate_workspace(self, scenario_id: str, stub_dir: str) -> str:
        """Copy stubs to isolated workspace. Return workspace path / container ID."""
        ...

    @abstractmethod
    def execute_test(self, workspace: str, spec: str, api_url: str) -> SandboxResult:
        """Run a test in the workspace."""
        ...

    @abstractmethod
    def destroy_workspace(self, workspace: str) -> None:
        """Clean up the workspace."""
        ...

    @abstractmethod
    def read_file(self, workspace: str, path: str) -> str:
        """Read a file from the workspace (for diff extraction)."""
        ...

    @abstractmethod
    def write_file(self, workspace: str, path: str, content: str) -> None:
        """Write content to a file in the workspace."""
        ...
