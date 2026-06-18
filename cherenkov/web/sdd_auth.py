"""Auth helpers shared across API sub-routers."""

from fastapi import Request, HTTPException, Header
from cherenkov.core.settings import get_settings


async def verify_write_access(
    request: Request,
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    host = request.client.host if request.client else "unknown"
    if host in ("127.0.0.1", "::1", "localhost"):
        return
    configured_key = get_settings().HITL_API_KEY
    if not configured_key:
        return
    if x_api_key and x_api_key == configured_key:
        return
    if (
        authorization
        and authorization.startswith("Bearer ")
        and authorization[7:] == configured_key
    ):
        return
    raise HTTPException(
        status_code=403, detail="Write access requires localhost or valid API key"
    )


async def verify_api_key(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    """Require a valid HITL_API_KEY when one is configured. No-op if key is unset."""
    if not get_settings().HITL_API_KEY:
        return
    if x_api_key and x_api_key == get_settings().HITL_API_KEY:
        return
    if (
        authorization
        and authorization.startswith("Bearer ")
        and authorization[7:] == get_settings().HITL_API_KEY
    ):
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
