"""Teleport MCP Tools (CC-5)."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from cherenkov.continuity.sessions.adapters.sqlite_sessions import SQLiteSessionStore
from cherenkov.continuity.sessions.use_cases.resume import ResumeSessionUseCase
from cherenkov.continuity.sessions.use_cases.snapshot import SnapshotSessionUseCase

# Note: We assume MCP server instance is available or these are pure functions we register
# For CC-5, we provide the tool implementations

store = SQLiteSessionStore()
snapshot_uc = SnapshotSessionUseCase(store)
resume_uc = ResumeSessionUseCase(store)


def register_teleport_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def teleport_push(session_id: str, state_data_json: str) -> str:
        """Push a session state to teleport store and get a QR/link token."""
        try:
            state_data = json.loads(state_data_json)
        except json.JSONDecodeError:
            return "Error: Invalid JSON for state_data."

        snapshot = snapshot_uc.execute(session_id, state_data)
        if snapshot.token:
            return f"Session {session_id} snapshotted. Token: {snapshot.token.token}"
        return "Failed to generate teleport token."

    @mcp.tool()
    def teleport_pull(token_str: str) -> str:
        """Pull a session state from teleport store using a token."""
        snapshot = resume_uc.execute_by_token(token_str)
        if snapshot:
            return json.dumps(snapshot.state_data)
        return "Error: Invalid or expired token."
