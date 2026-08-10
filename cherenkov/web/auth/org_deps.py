"""FastAPI dependency for extracting organization context from JWT claims."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from cherenkov.web.auth.deps import _bearer, _auth_enabled
from cherenkov.web.auth import jwt as _jwt
from cherenkov.core.errors import get_logger

log = get_logger(__name__)

def get_current_org(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> str:
    """Extract organization_id from JWT claims.

    Args:
        creds: HTTPAuthorizationCredentials object extracted from Bearer header.

    Returns:
        Organization ID string (defaults to 'default' if unauthenticated or missing).
    """
    if not _auth_enabled() or not creds:
        return "default"
    
    try:
        payload = _jwt.decode(creds.credentials)
    except ValueError:
        return "default"

    org_id = payload.get("organization_id", "default")
    if not org_id:
        log.warning("No organization_id found in claims, defaulting to 'default'")
        return "default"
    return org_id

OrgDep = Annotated[str, Depends(get_current_org)]
