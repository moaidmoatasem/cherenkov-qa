"""
Shared state and dependencies for the web API route modules.

Centralizes singletons (ConnectionManager, HitlQueue, asyncio loop) and
utility functions that multiple route modules need, avoiding circular imports
between api.py and individual route modules.
"""

from __future__ import annotations

import asyncio
import ipaddress as _ipaddress
import os
import re as _re
import socket as _socket
from contextlib import asynccontextmanager
from urllib.parse import urlparse as _urlparse

from fastapi import FastAPI, Header, HTTPException, WebSocket

from cherenkov.core.settings import get_settings
from cherenkov.hitl.store import HitlQueue


# ── WebSocket Manager (singleton) ─────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, message: dict):
        async with self._lock:
            conns = list(self.active_connections)
        dead = []
        for connection in conns:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        if dead:
            async with self._lock:
                for c in dead:
                    try:
                        self.active_connections.remove(c)
                    except ValueError:
                        pass


manager = ConnectionManager()
main_loop: asyncio.AbstractEventLoop | None = None


# ── HitlQueue singleton ───────────────────────────────────────────────

_queue: HitlQueue | None = None


def get_queue() -> HitlQueue:
    global _queue
    if _queue is None:
        _queue = HitlQueue(db_path=os.getenv("CHERENKOV_HITL_DB"))
    return _queue


# ── Security helpers ──────────────────────────────────────────────────

def _is_safe_ip(addr: _ipaddress.IPv4Address | _ipaddress.IPv6Address) -> bool:
    return not (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    )


async def _validate_spec_url(url: str) -> str:
    parsed = _urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")
    host = parsed.hostname or ""
    if host.lower() in (
        "localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal",
    ):
        raise HTTPException(status_code=400, detail="Internal network URLs not allowed")
    try:
        addr = _ipaddress.ip_address(host)
        if not _is_safe_ip(addr):
            raise HTTPException(status_code=400, detail="Internal network URLs not allowed")
        return url
    except ValueError:
        pass
    try:
        ips = await asyncio.to_thread(
            lambda: [info[4][0] for info in _socket.getaddrinfo(host, 80, family=_socket.AF_INET)]
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Could not resolve host")
    for ip_str in ips:
        try:
            addr = _ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if not _is_safe_ip(addr):
            raise HTTPException(status_code=400, detail="Internal network URLs not allowed")
    safe_host = ips[0]
    safe_url = url.replace(f"://{host}", f"://{safe_host}", 1)
    return safe_url


async def verify_api_key(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    import hmac as _hmac

    configured_key = get_settings().HITL_API_KEY
    if not configured_key:
        return
    if x_api_key and _hmac.compare_digest(x_api_key, configured_key):
        return
    if authorization and authorization.startswith("Bearer ") and _hmac.compare_digest(authorization[7:], configured_key):
        return
    raise HTTPException(status_code=401, detail="Missing or invalid API key")


def _validate_scenario_id(scenario_id: str) -> str:
    if not _re.match(r"^[a-zA-Z0-9_\-]{1,128}$", scenario_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid scenario_id: must be alphanumeric/underscore/hyphen, max 128 chars",
        )
    return scenario_id


def _validate_output_path(path: str) -> str:
    resolved = os.path.realpath(os.path.abspath(path))
    allowed_base = os.path.realpath(os.path.abspath("."))
    if resolved != allowed_base and not resolved.startswith(allowed_base + os.sep):
        raise HTTPException(
            status_code=400, detail="Output path must be within the working directory"
        )
    return resolved


def ws_event_callback(type_: str, payload: dict):
    if main_loop and manager.active_connections:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": type_, "payload": payload}), main_loop
        )


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app_: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    yield
