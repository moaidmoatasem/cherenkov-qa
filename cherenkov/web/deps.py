"""
cherenkov/web/deps.py — Shared state, helpers, and Pydantic models for route files.
"""

from __future__ import annotations

import os
import asyncio

import re as _re
from urllib.parse import urlparse as _urlparse
import ipaddress as _ipaddress
import socket as _socket

from fastapi import Header, HTTPException
from pydantic import BaseModel

from cherenkov.core.settings import get_settings
from cherenkov.hitl.store import HitlQueue


# ── Validation helpers ──────────────────────────────────────────────────────


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
    # Use os.sep suffix to avoid prefix collision (e.g. /app vs /app_secret).
    if resolved != allowed_base and not resolved.startswith(allowed_base + os.sep):
        raise HTTPException(
            status_code=400, detail="Output path must be within the working directory"
        )
    return resolved


def _is_safe_ip(addr: "_ipaddress.IPv4Address | _ipaddress.IPv6Address") -> bool:
    return not (
        addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    )


async def _validate_spec_url(url: str) -> str:
    """Validate URL and return a TOCTOU-safe fetch URL.

    Resolves the hostname once, validates every returned IP, then rewrites the
    URL to use the first resolved IP so the subsequent requests.get call never
    triggers a second DNS lookup.  This closes the DNS-rebinding window between
    validation and fetch.
    """
    parsed = _urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")
    host = parsed.hostname or ""
    if host.lower() in (
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
    ):
        raise HTTPException(status_code=400, detail="Internal network URLs not allowed")
    try:
        # Literal IP in the URL — validate in-place, no rewrite needed.
        addr = _ipaddress.ip_address(host)
        if not _is_safe_ip(addr):
            raise HTTPException(
                status_code=400, detail="Internal network URLs not allowed"
            )
        return url
    except ValueError:
        pass
    # Hostname: resolve once, validate all IPs, return URL rewritten to the
    # first safe IP so requests.get never does a second DNS lookup.
    try:
        infos = await asyncio.to_thread(_socket.getaddrinfo, host, None)
    except _socket.gaierror:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    if not infos:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    first_ip: str | None = None
    for info in infos:
        addr_str = info[4][0]
        try:
            resolved_addr = _ipaddress.ip_address(addr_str)
            if not _is_safe_ip(resolved_addr):
                raise HTTPException(
                    status_code=400, detail="Internal network URLs not allowed"
                )
            if first_ip is None:
                first_ip = addr_str
        except ValueError:
            pass
    if first_ip is None:
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    # Rewrite to pre-resolved IP; requests must send Host header for SNI/vhosts.
    safe_url = parsed._replace(netloc=parsed.netloc.replace(host, first_ip, 1)).geturl()
    return safe_url


# ── API key auth ────────────────────────────────────────────────────────────


async def verify_api_key(
    x_api_key: str | None = Header(None), authorization: str | None = Header(None)
):
    import hmac as _hmac

    configured_key = get_settings().HITL_API_KEY
    if not configured_key:
        return  # no auth configured — allow all
    if x_api_key and _hmac.compare_digest(x_api_key, configured_key):
        return
    if (
        authorization
        and authorization.startswith("Bearer ")
        and _hmac.compare_digest(authorization[7:], configured_key)
    ):
        return
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Set CHERENKOV_HITL_API_KEY env var.",
    )


# ── WebSocket Manager ───────────────────────────────────────────────────────

from fastapi import WebSocket  # noqa: E402 (after helpers so grouping stays clear)

# main_loop is set by the lifespan in api.py; routes import it from there.
# We expose it here as a mutable container so ws_event_callback can reference it.
_main_loop_ref: list = []  # _main_loop_ref[0] = the running loop, if set


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


def ws_event_callback(type_: str, payload: dict):
    main_loop = _main_loop_ref[0] if _main_loop_ref else None
    if main_loop and manager.active_connections:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": type_, "payload": payload}), main_loop
        )


# ── Pydantic request models ─────────────────────────────────────────────────


class RunPipelinePayload(BaseModel):
    spec_path: str
    target_url: str | None = None
    auth_header: str | None = None
    demo_mode: bool = False
    intent: str | None = None


class ReviewActionPayload(BaseModel):
    scenario_id: str
    reason: str | None = None
    test_code: str | None = None


class ValidatePayload(BaseModel):
    target_url: str


class EjectPayload(BaseModel):
    output_path: str


class DivergenceActionPayload(BaseModel):
    divergence_id: str
    action: str
    reason: str | None = None


class ClassifyPayload(BaseModel):
    item_id: str
    classification: str
    detail: str | None = None
    actor: str | None = None


# ── HitlQueue singleton ─────────────────────────────────────────────────────

_queue: HitlQueue | None = None


def get_queue() -> HitlQueue:
    global _queue
    if _queue is None:
        _queue = HitlQueue(db_path=os.getenv("CHERENKOV_HITL_DB"))
    return _queue
