"""FastAPI dependencies for authentication and RBAC."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cherenkov.web.auth import jwt as _jwt
from cherenkov.web.auth.models import Role, User
from cherenkov.web.auth.store import get_user_store

_bearer = HTTPBearer(auto_error=False)


def _auth_enabled() -> bool:
    from cherenkov.core.settings import get_settings
    return get_settings().AUTH_ENABLED


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    """Return the authenticated User, or None if auth is disabled."""
    if not _auth_enabled():
        return None
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _jwt.decode(creds.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_store().get(payload.get("sub", ""))
    if not user or user.disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
    return User(username=user.username, role=user.role)


def require_role(minimum: Role):
    """Dependency factory — raises 403 if the caller's role is below `minimum`."""
    async def _check(user: User | None = Depends(get_current_user)) -> User | None:
        if not _auth_enabled():
            return user
        if user is None or not (user.role >= minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{minimum.value}' role or higher",
            )
        return user
    return _check
