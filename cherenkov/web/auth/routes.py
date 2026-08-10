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
    """
    if not creds:
        return None
    return await get_current_user(creds)


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: Role = Role.viewer

    @field_validator("username")
    @classmethod
    def username_safe(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("Username must be alphanumeric (hyphens, underscores, dots allowed)")
        if len(v) > 64:
            raise ValueError("Username too long (max 64)")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


@router.post("/token", response_model=TokenResponse, summary="Obtain a JWT access token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
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

from cherenkov.adapters.identity.saml import SamlIdentityProvider
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

def get_saml_provider():
    from cherenkov.core.settings import get_settings
    settings = get_settings()
    config = {
        "strict": True,
        "debug": True,
        "sp": {
            "entityId": settings.SAML_SP_ENTITY_ID,
            "assertionConsumerService": {
                "url": f"{settings.API_URL}/api/v1/auth/saml/callback",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
        },
        "idp": {
            "entityId": settings.SAML_IDP_METADATA_URL,
            "singleSignOnService": {
                "url": settings.SAML_IDP_METADATA_URL,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            }
        }
    }
    return SamlIdentityProvider(config)


@router.get("/saml/login", summary="SP-initiated SAML login")
async def saml_login(request: Request, relay_state: str = ""):
    from cherenkov.core.settings import get_settings
    if not getattr(get_settings(), "SAML_ENABLED", False):
        raise HTTPException(status_code=400, detail="SAML SSO is not configured")
        
    sp = get_saml_provider()
    
    req_data = {
        'is_https': request.url.scheme == 'https',
        'host': request.headers.get('host', request.url.hostname),
        'port': str(request.url.port) if request.url.port else ('443' if request.url.scheme == 'https' else '80'),
        'path': request.url.path,
        'query_params': dict(request.query_params),
    }
    
    url = sp.get_login_url(req_data)
    if relay_state:
        # OneLogin python3-saml handles ReturnTo logic via query params
        pass 
    return RedirectResponse(url)

@router.post("/saml/callback", response_model=TokenResponse, summary="IdP SAML callback (ACS)")
async def saml_callback(request: Request, SAMLResponse: str = Form(...), RelayState: str = Form("")):
    from cherenkov.core.settings import get_settings
    if not getattr(get_settings(), "SAML_ENABLED", False):
        raise HTTPException(status_code=400, detail="SAML SSO is not configured")
    
    sp = get_saml_provider()
    
    req_data = {
        'is_https': request.url.scheme == 'https',
        'host': request.headers.get('host', request.url.hostname),
        'port': str(request.url.port) if request.url.port else ('443' if request.url.scheme == 'https' else '80'),
        'path': request.url.path,
        'form_data': {'SAMLResponse': SAMLResponse, 'RelayState': RelayState},
    }
    
    try:
        user_info = sp.authenticate(req_data)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid SAML Response: {str(e)}")

    username = user_info.get("email")
    org_id = user_info.get("organization_id", "default")
    roles = user_info.get("roles", ["viewer"])
    raw_role = roles[0] if roles else "viewer"
    
    role_map = {
        "admin": Role.admin,
        "engineer": Role.reviewer,
        "viewer": Role.viewer,
        "read_only": Role.viewer,
    }
    mapped_role = role_map.get(raw_role.lower(), Role.viewer)

    store = get_user_store()
    user = store.get(username)
    if not user:
        import secrets
        user = store.create(username, password=secrets.token_hex(32), role=mapped_role, organization_id=org_id)
    elif user.disabled:
        raise HTTPException(status_code=401, detail="User is disabled")

    expire_hours = get_settings().JWT_EXPIRE_HOURS
    token = _jwt.encode({"sub": user.username, "role": user.role.value, "organization_id": user.organization_id}, expire_hours=expire_hours)
    
    return TokenResponse(
        access_token=token,
        expires_in=expire_hours * 3600,
        role=user.role,
        organization_id=user.organization_id
    )

@router.get("/saml/metadata", summary="SAML SP Metadata", response_class=HTMLResponse)
async def saml_metadata():
    from cherenkov.core.settings import get_settings
    if not getattr(get_settings(), "SAML_ENABLED", False):
        raise HTTPException(status_code=400, detail="SAML SSO is not configured")
        
    sp = get_saml_provider()
    try:
        metadata = sp.build_metadata()
        return HTMLResponse(content=metadata, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=User, summary="Return the current authenticated user")
async def me(current_user: User | None = Depends(get_current_user)):
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
    return get_user_store().list_users()


@router.delete("/users/{username}", status_code=204, summary="Disable a user (admin only)")
async def disable_user(
    username: str,
    current_user: User | None = Depends(require_role(Role.admin)),
):
    if current_user and username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if not get_user_store().set_disabled(username, True):
        raise HTTPException(status_code=404, detail="User not found")
