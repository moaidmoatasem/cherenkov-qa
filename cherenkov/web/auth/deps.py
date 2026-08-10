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
    """Return the authenticated User, or None if auth is disabled.

    Args:
        creds: HTTPAuthorizationCredentials object extracted from Bearer header.

    Returns:
        User object representing current authenticated user, or None if auth is disabled.

    Raises:
        HTTPException: 401 Unauthorized if token is missing, invalid, or user is disabled.
    """
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
        ) from None
    user = get_user_store().get(payload.get("sub", ""))
    if not user or user.disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
    return User(username=user.username, role=user.role, organization_id=user.organization_id)


def require_role(minimum: Role):
    """Dependency factory — raises 403 if the caller's role is below `minimum`.

    Args:
        minimum: Minimum required Role enum level.

    Returns:
        FastAPI async dependency function verifying user role and organization.
    """
    async def _check(user: User | None = Depends(get_current_user)) -> User | None:
        if not _auth_enabled():
            return user
        
        from cherenkov.core.context import current_org_id
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
            
        if user.organization_id != current_org_id.get():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization mismatch",
            )
            
        if not (user.role >= minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires '{minimum.value}' role or higher",
            )
        return user
    return _check
