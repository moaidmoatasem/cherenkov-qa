"""
cherenkov/web/middleware/rate_limit.py — Token-bucket rate limiter.

Per-client (IP) rate limiting enforced at the ASGI middleware layer.
No external dependencies — uses stdlib threading + time.

Configuration (env vars):
    CHERENKOV_RATE_LIMIT_RPS  — max requests per second per client (default 10)
    CHERENKOV_RATE_LIMIT_BURST — burst capacity (default 20)
    CHERENKOV_RATE_LIMIT_ENABLED — set to "false" to disable (default enabled)

Endpoints with heavier cost (e.g. /api/v1/verify) are assigned a higher token
cost server-side via _route_cost(). Client-supplied cost headers are ignored.

HTTP 429 response body:
    {"error": "rate_limit_exceeded", "retry_after_seconds": <float>}
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_RPS: float = float(os.getenv("CHERENKOV_RATE_LIMIT_RPS", "10"))
_BURST: float = float(os.getenv("CHERENKOV_RATE_LIMIT_BURST", "20"))
_ENABLED: bool = os.getenv("CHERENKOV_RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

# Paths that are exempt from rate limiting (health/metrics probes)
_EXEMPT_PREFIXES: tuple[str, ...] = ("/health", "/metrics", "/docs", "/openapi.json", "/redoc")

# Server-side route cost table — clients cannot influence this.
_ROUTE_COSTS: dict[str, float] = {
    "/api/v1/verify": 5.0,
    "/api/v1/generate": 5.0,
    "/api/v1/run": 3.0,
}


def _route_cost(path: str) -> float:
    for prefix, cost in _ROUTE_COSTS.items():
        if path == prefix or path.startswith(prefix + "/"):
            return cost
    return 1.0


class _Bucket:
    """Single-client token bucket (thread-safe)."""

    __slots__ = ("_lock", "last_refill", "tokens")

    def __init__(self, capacity: float) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, rps: float, burst: float, cost: float = 1.0) -> tuple[bool, float]:
        """Try to consume `cost` tokens. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            elapsed = now - self.last_refill
            self.tokens = min(burst, self.tokens + elapsed * rps)
            self.last_refill = now

            if self.tokens >= cost:
                self.tokens -= cost
                return True, 0.0

            deficit = cost - self.tokens
            retry_after = deficit / rps
            return False, retry_after


class RateLimitMiddleware:
    """ASGI middleware that enforces per-IP token-bucket rate limits."""

    def __init__(self, app: ASGIApp, rps: float = _RPS, burst: float = _BURST, enabled: bool = _ENABLED) -> None:
        self._app = app
        self._rps = rps
        self._burst = burst
        self._enabled = enabled
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(burst))
        self._lock = threading.Lock()

    def _get_bucket(self, client_key: str) -> _Bucket:
        with self._lock:
            return self._buckets[client_key]

    def _client_key(self, scope: Scope) -> str:
        # Use the direct peer IP as the authoritative key.
        # X-Forwarded-For is attacker-controlled when there is no trusted reverse
        # proxy in front, so we do NOT use it for rate-limit keying.
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._enabled or scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            await self._app(scope, receive, send)
            return

        # Cost is determined server-side by path, never from client-supplied headers.
        cost = _route_cost(scope.get("path", ""))

        client_key = self._client_key(scope)
        bucket = self._get_bucket(client_key)
        allowed, retry_after = bucket.consume(self._rps, self._burst, cost)

        if allowed:
            await self._app(scope, receive, send)
        else:
            response = JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after_seconds": round(retry_after, 3)},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
            await response(scope, receive, send)
