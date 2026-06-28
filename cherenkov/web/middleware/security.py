from __future__ import annotations

import logging
import os
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        max_requests: int = int(os.getenv("CHERENKOV_MAX_REQUESTS", "100")),
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds
        filtered = [t for t in self._requests[client_ip] if t > window_start]
        # Evict IPs with no recent requests to prevent unbounded dict growth
        if not filtered and client_ip in self._requests:
            del self._requests[client_ip]
        if len(filtered) >= self.max_requests:
            logger.warning("rate limit exceeded", extra={"client_ip": client_ip})
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again later."},
            )
        filtered.append(now)
        self._requests[client_ip] = filtered
        return await call_next(request)


class InputValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_type = request.headers.get("content-type", "")
        if request.method in ("POST", "PUT", "PATCH"):
            if "application/json" in content_type:
                try:
                    body = await request.json()
                except Exception:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid JSON body."},
                    )
                if body is None:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Empty JSON body."},
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    _SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        # React 19 + Vite production build produces no inline scripts, so
        # unsafe-inline and unsafe-eval are not needed on script-src.
        # style-src keeps unsafe-inline for React's style={{}} prop; removing it
        # would require hashing every inline style at build time.
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:; "
            "font-src 'self'; "
            "frame-ancestors 'none'"
        ),
    }

    # Only truly public, non-sensitive read-only endpoints.
    # /api/v1/metrics, /api/v1/truth-map, /api/v1/failures were removed —
    # they expose internal state that must not be publicly cached by CDNs/proxies.
    _CACHEABLE_PATHS = {
        "/api/v1/health",
        "/healthz",
        "/api/v1/tokens/report",
        "/api/v1/tokens/recommendations",
        "/api/v1/overview",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self._SECURITY_HEADERS.items():
            response.headers[header] = value
        # HSTS only over HTTPS — avoids breaking local HTTP dev while protecting L4+ deployments
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if proto == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        path = request.url.path
        if path.startswith("/assets/"):
            # Static assets: long-lived immutable cache (Vite hashes filenames)
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.method == "GET" and path in self._CACHEABLE_PATHS:
            # Safe read-only polling endpoints: short cache to reduce repeated backend hits
            response.headers["Cache-Control"] = (
                "public, max-age=5, stale-while-revalidate=10"
            )
        else:
            # Mutating endpoints and sensitive data: never cache
            response.headers["Cache-Control"] = "no-store"
        return response


def add_security_middleware(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
