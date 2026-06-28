"""
Global JWT auth middleware — enforces viewer-level auth on all non-public paths
when CHERENKOV_AUTH_ENABLED=true.  Individual routes may add stricter role deps
on top of this (reviewer/admin) via require_role().

Public paths (no token needed even with auth enabled):
  /healthz, /api/v1/health, /api/v1/auth/*, static assets
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_PUBLIC_PREFIXES = (
    "/healthz",
    "/api/v1/health",
    "/api/v1/auth/",
    "/static/",
    "/assets/",
    "/favicon",
)


def _is_public(path: str) -> bool:
    return any(path == p.rstrip("/") or path.startswith(p) for p in _PUBLIC_PREFIXES)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from cherenkov.core.settings import get_settings

        if not get_settings().AUTH_ENABLED or _is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Not authenticated"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:]
        try:
            from cherenkov.web.auth import jwt as _jwt
            _jwt.decode(token)
        except ValueError as exc:
            return JSONResponse(
                {"detail": str(exc)},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
