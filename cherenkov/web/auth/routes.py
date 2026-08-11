"""Auth API routes: token, me, user management (admin)."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator

from cherenkov.web.auth import jwt as _jwt
from cherenkov.web.auth.deps import get_current_user, require_role
from cherenkov.web.auth.models import Role, TokenResponse, User
from cherenkov.web.auth.store import get_user_store
from cherenkov.enterprise.saml import SAMLServiceProvider
from fastapi import Form
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> User | None:
    """Resolve the caller, returning None instead of 401 when unauthenticated.

    The bootstrap path of `create_user` has to be reachable before any user (and
    therefore any token) exists, which `get_current_user` would reject outright.

    Args:
        creds: HTTPAuthorizationCredentials object from Bearer header or None.

    Returns:
        User object if authenticated, or None if unauthenticated.
    """
    if not creds:
        return None
    return await get_current_user(creds)


class CreateUserRequest(BaseModel):
    """Payload model for creating a new user account."""
    username: str
    password: str
    role: Role = Role.viewer

    @field_validator("username")
    @classmethod
    def username_safe(cls, v: str) -> str:
        """Validate that username contains valid alphanumeric characters.

        Args:
            v: Input username string.

        Returns:
            Validated username string.

        Raises:
            ValueError: If username is invalid or exceeds max length.
        """
        if not v or not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username must be alphanumeric (hyphens, underscores, dots allowed)")
        if len(v) > 64:
            raise ValueError("Username too long (max 64)")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength.

        Args:
            v: Input password string.

        Returns:
            Validated password string.

        Raises:
            ValueError: If password length is less than 8 characters.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


@router.post("/token", response_model=TokenResponse, summary="Obtain a JWT access token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user credentials and issue a JWT token.

    Args:
        form: OAuth2PasswordRequestForm containing username and password.

    Returns:
        TokenResponse object containing JWT access token and role info.

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid.
    """
    user = get_user_store().authenticate(form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from cherenkov.core.settings import get_settings

    expire_hours = get_settings().JWT_EXPIRE_HOURS
    token = _jwt.encode({"sub": user.username, "role": user.role.value}, expire_hours=expire_hours)
    return TokenResponse(
        access_token=token,
        expires_in=expire_hours * 3600,
        role=user.role,
        organization_id=user.organization_id,
    )

@router.get("/saml/login", summary="SP-initiated SAML login")
async def saml_login(relay_state: str = ""):
    """Initiate SAML single sign-on redirect.

    Args:
        relay_state: Optional state parameter to pass through IdP redirect.

    Returns:
        RedirectResponse to IdP authentication URL.

    Raises:
        HTTPException: 400 Bad Request if SAML is not configured.
    """
    sp = SAMLServiceProvider()
    if not sp.is_enabled():
        raise HTTPException(status_code=400, detail="SAML SSO is not configured")
    url = sp.get_login_url(relay_state)
    return RedirectResponse(url)

@router.post("/saml/callback", response_model=TokenResponse, summary="IdP SAML callback (ACS)")
async def saml_callback(SAMLResponse: str = Form(...), RelayState: str = Form("")):
    """Process SAML Assertion response from Identity Provider (IdP).

    Args:
        SAMLResponse: Base64-encoded SAML XML assertion response from IdP.
        RelayState: Optional relay state string returned from IdP.

    Returns:
        TokenResponse object containing JWT access token for SAML user.

    Raises:
        HTTPException: 400 if SAML disabled, or 401 if assertion invalid or user disabled.
    """
    sp = SAMLServiceProvider()
    if not sp.is_enabled():
        raise HTTPException(status_code=400, detail="SAML SSO is not configured")
    
    assertion = sp.process_response(SAMLResponse)
    if not assertion:
        raise HTTPException(status_code=401, detail="Invalid SAML Response")

    # Map SAML attributes to our internal model. 
    # Hardcoded mapping logic as specified in the enterprise model docs.
    username = assertion.email
    org_id = assertion.attributes.get("organization_id", ["default"])[0]
    raw_role = assertion.attributes.get("role", ["viewer"])[0]
    
    # Map raw_role (could be 'ADMIN' or 'admin' or 'viewer') to web Role
    role_map = {
        "admin": Role.admin,
        "engineer": Role.reviewer,
        "viewer": Role.viewer,
        "read_only": Role.viewer,
    }
    mapped_role = role_map.get(raw_role.lower(), Role.viewer)

    store = get_user_store()
    user: User | None = store.get(username)
    if not user:
        # Auto-provision user on first SSO login
        # We don't have a real password since they authenticate via IdP
        import secrets
        user = store.create(username, password=secrets.token_hex(32), role=mapped_role, organization_id=org_id)
    elif user.disabled:
        raise HTTPException(status_code=401, detail="User is disabled")
    else:
        # Update user's role and org if it drifted in IdP
        # Sync role and organization if they differ from IdP attributes
        if user.role != mapped_role or user.organization_id != org_id:
            store.update_user(username, role=mapped_role, organization_id=org_id)
            # Refresh the user record after update
            refreshed = store.get(username)
            if refreshed:
                user = refreshed

    from cherenkov.core.settings import get_settings
    expire_hours = get_settings().JWT_EXPIRE_HOURS
    token = _jwt.encode({"sub": user.username, "role": user.role.value, "organization_id": user.organization_id}, expire_hours=expire_hours)
    
    return TokenResponse(
        access_token=token,
        expires_in=expire_hours * 3600,
        role=user.role,
        organization_id=user.organization_id
    )


@router.get("/me", response_model=User, summary="Return the current authenticated user")
async def me(current_user: User | None = Depends(get_current_user)):
    """Retrieve identity of current authenticated user.

    Args:
        current_user: Authenticated User object from dependency.

    Returns:
        User object for caller, or default anonymous user if auth disabled.
    """
    if current_user is None:
        return User(username="anonymous", role=Role.admin)
    return current_user


@router.post(
    "/users", response_model=User, status_code=201, summary="Create a user (admin or bootstrap)"
)
async def create_user(
    body: CreateUserRequest,
    current_user: User | None = Depends(_optional_current_user),
    x_bootstrap_key: str | None = Header(None),
):
    """Create a new user account (requires admin role or bootstrap header).

    Args:
        body: CreateUserRequest payload containing credentials and role.
        current_user: Optional authenticated caller User.
        x_bootstrap_key: Optional X-Bootstrap-Key header for initial user creation.

    Returns:
        Created User object.

    Raises:
        HTTPException: 403 Forbidden if unauthorized, 409 Conflict if username exists.
    """
    store = get_user_store()
    # Bootstrap path: if no users exist, allow creation with CHERENKOV_BOOTSTRAP_KEY
    if store.count() == 0:
        from cherenkov.core.settings import get_settings

        bk = get_settings().BOOTSTRAP_KEY
        if not bk:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No users exist and CHERENKOV_BOOTSTRAP_KEY is not set. "
                "Set it to create the first admin user.",
            )
        # No JWT exists yet, so the bootstrap key presented in X-Bootstrap-Key
        # is the only credential gating creation of the first (admin) user.
        if not x_bootstrap_key or not hmac.compare_digest(x_bootstrap_key, bk):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or missing X-Bootstrap-Key header",
            )
    else:
        # Require admin role for subsequent user creation
        if current_user is None or not (current_user.role >= Role.admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        user = store.create(body.username, body.password, body.role)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="Username already exists") from None
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return user


@router.get("/users", response_model=list[User], summary="List all users (admin only)")
async def list_users(_: User | None = Depends(require_role(Role.admin))):
    """List all registered users.

    Args:
        _: Authenticated admin user verification dependency.

    Returns:
        List of User objects.
    """
    return get_user_store().list_users()


@router.delete("/users/{username}", status_code=204, summary="Disable a user (admin only)")
async def disable_user(
    username: str,
    current_user: User | None = Depends(require_role(Role.admin)),
):
    """Disable a user account by username.

    Args:
        username: Target username to disable.
        current_user: Authenticated admin user making request.

    Raises:
        HTTPException: 400 Bad Request if disabling self, or 404 Not Found if user missing.
    """
    if current_user and username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if not get_user_store().set_disabled(username, True):
        raise HTTPException(status_code=404, detail="User not found")
