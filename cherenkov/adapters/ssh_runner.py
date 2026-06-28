"""SSH Runner Adapter (CC-5)."""
from __future__ import annotations

import asyncio
from typing import Any

from cherenkov.ports.remote_runner import RemoteRunnerPort


class SSHRunner(RemoteRunnerPort):
    def __init__(self, host: str, user: str, port: int = 22):
        self.host = host
        self.user = user
        self.port = port

    async def execute_command(self, command: str, env: dict[str, str] | None = None) -> dict[str, Any]:
        """Execute command over SSH (stub implementation)."""
        # In a real implementation we would use asyncssh or paramiko
        # For Phase CC-5, we simulate the remote execution
        ssh_cmd = f"ssh -p {self.port} {self.user}@{self.host} '{command}'"

        process = await asyncio.create_subprocess_shell(
            ssh_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
            "simulated": True
        }
