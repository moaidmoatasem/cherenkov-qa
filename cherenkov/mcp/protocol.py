"""
cherenkov/mcp/protocol.py
Minimal JSON-RPC 2.0 over stdio transport.

Reads newline-delimited JSON from stdin, routes to a dispatch table,
writes a JSON response to stdout. No third-party dependencies.

Each line on stdin must be a complete JSON-RPC 2.0 request object.
Responses are written as a single JSON line to stdout.

The server loop runs until stdin is closed (EOF).
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

from cherenkov.mcp.contracts import (
    INTERNAL_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    JsonRpcRequest,
    JsonRpcResponse,
)


DispatchTable = dict[str, Callable[[dict[str, Any]], Any]]


def _write_response(resp: JsonRpcResponse) -> None:
    """Serialise and flush one JSON-RPC response to stdout."""
    line = resp.model_dump_json(exclude_none=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _make_error(id: Any, code: int, message: str, data: Any = None) -> JsonRpcResponse:
    from cherenkov.mcp.contracts import JsonRpcError
    return JsonRpcResponse(id=id, error=JsonRpcError(code=code, message=message, data=data))


def _make_success(id: Any, result: Any) -> JsonRpcResponse:
    return JsonRpcResponse(id=id, result=result)


def dispatch_one(raw: str, table: DispatchTable) -> JsonRpcResponse | None:
    """
    Parse one JSON-RPC 2.0 request line and dispatch to *table*.

    Returns None for notifications (id is None/absent and we should not reply).
    Returning an error response on parse failures is required by the spec.
    """
    # ── Parse ────────────────────────────────────────────────────────────────
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _make_error(None, PARSE_ERROR, f"Parse error: {exc}")

    # ── Validate JSON-RPC envelope ────────────────────────────────────────────
    req_id = data.get("id")  # may be absent for notifications
    try:
        req = JsonRpcRequest.model_validate(data)
    except Exception as exc:
        return _make_error(req_id, INVALID_REQUEST, f"Invalid request: {exc}")

    # Notifications (no id) are processed but not replied to
    is_notification = "id" not in data

    # ── Dispatch ──────────────────────────────────────────────────────────────
    handler = table.get(req.method)
    if handler is None:
        if is_notification:
            return None
        return _make_error(req.id, METHOD_NOT_FOUND, f"Method not found: {req.method!r}")

    try:
        result = handler(req.params)
        if is_notification:
            return None
        return _make_success(req.id, result)
    except Exception as exc:
        if is_notification:
            return None
        return _make_error(req.id, INTERNAL_ERROR, f"Internal error: {exc}")


def serve_stdio(table: DispatchTable, *, input_stream=None, output_stream=None) -> None:
    """
    Run the JSON-RPC 2.0 stdio server loop.

    Reads lines from *input_stream* (default: sys.stdin) until EOF.
    Writes responses to *output_stream* (default: sys.stdout).

    Both streams can be overridden for testing without monkey-patching globals.
    """
    import cherenkov.mcp.protocol as _self_module  # noqa: F401 — keep module ref for test mocking

    stdin = input_stream or sys.stdin
    _orig_stdout = sys.stdout
    if output_stream:
        sys.stdout = output_stream

    try:
        for raw_line in stdin:
            raw_line = raw_line.rstrip("\n")
            if not raw_line.strip():
                continue
            resp = dispatch_one(raw_line, table)
            if resp is not None:
                _write_response(resp)
    finally:
        if output_stream:
            sys.stdout = _orig_stdout
