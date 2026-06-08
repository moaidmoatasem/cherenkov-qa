from __future__ import annotations

import time
import logging
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]
        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning("rate limit exceeded", extra={"client_ip": client_ip})
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again later."},
            )
        self._requests[client_ip].append(now)
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


def add_security_middleware(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(InputValidationMiddleware)
