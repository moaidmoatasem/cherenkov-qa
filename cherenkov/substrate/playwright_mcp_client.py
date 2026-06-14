"""
Playwright MCP Client Interface (Horizon 3)
Connects to an external Playwright MCP Server to execute web automation via Semantic Accessibility Trees.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PlaywrightMCPClient:
    """
    Connects to the @playwright/mcp server to navigate and validate applications.
    Utilizes structured accessibility trees instead of heavy vision screenshots.
    Communicates via MCP stdio transport.
    """

    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None
        self._message_id = 1
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def connect(self):
        """Establish stdio connection to Playwright MCP server"""
        logger.info(
            f"Starting Playwright MCP server: {self.command} {' '.join(self.args)}"
        )
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Start a background task to read stdout
        asyncio.create_task(self._read_stdout())
        # Send initialize request
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cherenkov-qa", "version": "1.0.0"},
            },
        )
        # Send initialized notification
        await self._send_notification("notifications/initialized", {})

    async def _read_stdout(self):
        """Read JSON-RPC messages from the server's stdout."""
        if not self.process or not self.process.stdout:
            return

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break

            try:
                payload = json.loads(line.decode().strip())
                if "id" in payload and payload["id"] in self._pending_requests:
                    future = self._pending_requests.pop(payload["id"])
                    if "error" in payload:
                        future.set_exception(Exception(payload["error"]))
                    else:
                        future.set_result(payload.get("result"))
            except json.JSONDecodeError:
                continue

    async def _send_request(self, method: str, params: dict) -> Any:
        """Send a JSON-RPC request and wait for the response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP client not connected")

        req_id = self._message_id
        self._message_id += 1

        request = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = future

        self.process.stdin.write((json.dumps(request) + "\\n").encode())
        await self.process.stdin.drain()

        return await future

    async def _send_notification(self, method: str, params: dict):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP client not connected")

        notification = {"jsonrpc": "2.0", "method": method, "params": params}
        self.process.stdin.write((json.dumps(notification) + "\\n").encode())
        await self.process.stdin.drain()

    async def get_accessibility_snapshot(self) -> Dict[str, Any]:
        """Fetch the semantic DOM layout from the active browser"""
        return await self._send_request(
            "tools/call", {"name": "browser_snapshot", "arguments": {}}
        )

    async def execute_action(self, action_type: str, target: str) -> Any:
        """Execute a semantic action (click, fill) via Playwright MCP"""
        tool_name = f"browser_{action_type}"
        return await self._send_request(
            "tools/call", {"name": tool_name, "arguments": {"target": target}}
        )

    async def close(self):
        """Terminate the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
