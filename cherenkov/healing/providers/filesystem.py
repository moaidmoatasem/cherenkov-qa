"""
CHERENKOV healing/providers/filesystem.py — filesystem sandbox provider.

Anti-lock-in: this is the default fallback when Docker is unavailable.
D7 invariant: operations are confined to .cherenkov/sandbox_* directories.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from cherenkov.core.compat import npx as _npx
from cherenkov.core.errors import get_logger
from cherenkov.healing.providers.base import SandboxProvider, SandboxResult


class FilesystemSandboxProvider(SandboxProvider):
    def __init__(self, cherenkov_dir: str | None = None):
        self.log = get_logger("FS_SANDBOX")
        self.cherenkov_dir = cherenkov_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../.cherenkov")
        )

    def replicate_workspace(self, scenario_id: str, stub_dir: str) -> str:
        sandbox_path = os.path.join(self.cherenkov_dir, f"sandbox_{scenario_id}")
        self.log.info(
            "replicating stub workspace to filesystem sandbox", path=sandbox_path
        )

        if os.path.exists(sandbox_path):
            shutil.rmtree(sandbox_path)
        os.makedirs(sandbox_path, exist_ok=True)

        shutil.ignore_patterns(
            "node_modules", "generated_tests", "test-results"
        )
        for item in os.listdir(stub_dir):
            s = os.path.join(stub_dir, item)
            d = os.path.join(sandbox_path, item)
            if os.path.isdir(s):
                if item not in ("node_modules", "generated_tests", "test-results"):
                    shutil.copytree(s, d, symlinks=True)
            else:
                shutil.copy2(s, d)

        os.makedirs(os.path.join(sandbox_path, "generated_tests"), exist_ok=True)

        parent_node_modules = os.path.join(stub_dir, "node_modules")
        sandbox_node_modules = os.path.join(sandbox_path, "node_modules")
        if os.path.exists(parent_node_modules):
            try:
                os.symlink(parent_node_modules, sandbox_node_modules)
                self.log.info("successfully symlinked node_modules to sandbox")
            except Exception as e:
                self.log.warning(
                    "failed to symlink node_modules, attempting copy", error=str(e)
                )
                if os.path.exists(sandbox_node_modules):
                    shutil.rmtree(sandbox_node_modules)
                shutil.copytree(
                    parent_node_modules, sandbox_node_modules, dirs_exist_ok=True
                )

        return sandbox_path

    def execute_test(self, workspace: str, spec: str, api_url: str) -> SandboxResult:
        spec_path = f"generated_tests/{spec}"
        self.log.info("executing playwright test in filesystem sandbox", spec=spec_path)

        env = os.environ.copy()
        env["API_URL"] = api_url

        process = subprocess.run(
            [_npx(), "playwright", "test", spec_path, "--reporter=json"],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
        )

        return SandboxResult(
            passed=(process.returncode == 0),
            exit_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )

    def destroy_workspace(self, workspace: str) -> None:
        shutil.rmtree(workspace, ignore_errors=True)
        self.log.info("destroyed filesystem sandbox", path=workspace)

    def read_file(self, workspace: str, path: str) -> str:
        full_path = os.path.join(workspace, path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, workspace: str, path: str, content: str) -> None:
        full_path = os.path.join(workspace, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
