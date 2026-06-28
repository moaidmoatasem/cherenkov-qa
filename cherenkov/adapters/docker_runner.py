"""Docker Runner Adapter (CC-5)."""
from __future__ import annotations

import asyncio
from typing import Any

from cherenkov.ports.remote_runner import RemoteRunnerPort


class DockerRunner(RemoteRunnerPort):
    def __init__(self, container_name: str):
        self.container_name = container_name

    async def execute_command(self, command: str, env: dict[str, str] | None = None) -> dict[str, Any]:
        """Execute command inside a Docker container."""
        # Using local docker cli to exec into the container
        env_args = ""
        if env:
            env_args = " ".join([f"-e {k}='{v}'" for k, v in env.items()])

        docker_cmd = f"docker exec {env_args} {self.container_name} sh -c '{command}'"

        process = await asyncio.create_subprocess_shell(
            docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8")
        }
