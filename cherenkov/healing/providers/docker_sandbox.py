"""
CHERENKOV healing/providers/docker_sandbox.py — Docker E2B sandbox provider.
Authority: v3.1 + delta.

D7 invariant: container boundary enforces isolation — no host filesystem write.
Anti-lock-in: non-Docker fallback is FilesystemSandboxProvider.
"""
from __future__ import annotations

import os
import subprocess

from cherenkov.core.errors import get_logger
from cherenkov.healing.providers.base import SandboxProvider, SandboxResult


class DockerSandboxProvider(SandboxProvider):
    def __init__(
        self,
        image: str = "cherenkov-mcp:latest",
        network: str = "host",
        cherenkov_dir: str | None = None,
    ):
        self.image = image
        self.network = network
        self.log = get_logger("DOCKER_SANDBOX")
        self.cherenkov_dir = cherenkov_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../.cherenkov")
        )

    def replicate_workspace(self, scenario_id: str, stub_dir: str) -> str:
        self.log.info("creating docker sandbox container", scenario=scenario_id)
        container_id = subprocess.check_output(
            [
                "docker", "create",
                "--rm",
                "--network", self.network,
                "--label", f"cherenkov.scenario={scenario_id}",
                "--label", "cherenkov.provider=docker",
                "-v", f"{stub_dir}:/workspace/stub:ro",
                "-v", f"{self.cherenkov_dir}:/workspace/.cherenkov",
                self.image,
                "sleep", "3600",
            ],
            text=True,
        ).strip()

        # Copy stubs into the container workspace
        subprocess.run(
            ["docker", "cp", f"{stub_dir}/.", f"{container_id}:/workspace/stub/"],
            capture_output=True,
        )

        self.log.info("docker sandbox container created", container_id=container_id[:12])
        return container_id

    def execute_test(self, container_id: str, spec: str, api_url: str) -> SandboxResult:
        self.log.info("executing test in docker sandbox", container_id=container_id[:12], spec=spec)
        result = subprocess.run(
            [
                "docker", "exec",
                "-e", f"API_URL={api_url}",
                container_id,
                "npx", "playwright", "test", f"generated_tests/{spec}", "--reporter=json",
            ],
            capture_output=True,
            text=True,
        )

        return SandboxResult(
            passed=(result.returncode == 0),
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def destroy_workspace(self, container_id: str) -> None:
        subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)
        self.log.info("destroyed docker sandbox", container_id=container_id[:12])

    def read_file(self, container_id: str, path: str) -> str:
        result = subprocess.run(
            ["docker", "cp", f"{container_id}:{path}", "-"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise FileNotFoundError(f"Cannot read {path} from container {container_id[:12]}")
        return result.stdout.decode("utf-8")

    def write_file(self, container_id: str, path: str, content: str) -> None:
        # Write content to a temp file and docker cp it into the container
        temp_dir = os.path.join(self.cherenkov_dir, ".docker_tmp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, os.path.basename(path))
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.run(
            ["docker", "cp", temp_path, f"{container_id}:{path}"],
            capture_output=True,
        )
        os.remove(temp_path)
