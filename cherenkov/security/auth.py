import hmac

from fastapi import Request, HTTPException, Header

from cherenkov.core.settings import get_settings


def _constant_time_compare(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return hmac.compare_digest(a, b)


async def verify_api_key(
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
):
    configured_key = get_settings().HITL_API_KEY
    if not configured_key:
        return
    if _constant_time_compare(x_api_key, configured_key):
        return
    if authorization and authorization.startswith("Bearer ") and _constant_time_compare(authorization[7:], configured_key):
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


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
    if _constant_time_compare(x_api_key, configured_key):
        return
    if authorization and authorization.startswith("Bearer ") and _constant_time_compare(authorization[7:], configured_key):
        return
    raise HTTPException(
        status_code=403, detail="Write access requires localhost or valid API key"
    )
