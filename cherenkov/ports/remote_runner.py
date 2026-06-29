"""Remote Runner Port (CC-5)."""
from __future__ import annotations

import abc
from typing import Any


class RemoteRunnerPort(abc.ABC):
    @abc.abstractmethod
    async def execute_command(self, command: str, env: dict[str, str] | None = None) -> dict[str, Any]:
        """Execute a command on a remote runner and return the result."""
