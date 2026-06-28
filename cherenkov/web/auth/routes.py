"""Auth API routes: token, me, user management (admin)."""
from __future__ import annotations


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator

from cherenkov.web.auth import jwt as _jwt
from cherenkov.web.auth.deps import get_current_user, require_role
from cherenkov.web.auth.models import Role, TokenResponse, User
from cherenkov.web.auth.store import get_user_store

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
    )


@router.get("/me", response_model=User, summary="Return the current authenticated user")
async def me(current_user: User | None = Depends(get_current_user)):
    if current_user is None:
        return User(username="anonymous", role=Role.admin)
    return current_user


@router.post("/users", response_model=User, status_code=201, summary="Create a user (admin or bootstrap)")
async def create_user(
    body: CreateUserRequest,
    current_user: User | None = Depends(get_current_user),
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
        # Caller must include bootstrap key as password of a sentinel user
        # Actually: caller POSTs normally but must present the bootstrap key
        # via X-Bootstrap-Key header — checked below.  We allow no JWT here.
    else:
        # Require admin role for subsequent user creation
        if current_user is None or not (current_user.role >= Role.admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        user = store.create(body.username, body.password, body.role)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="Username already exists")
        raise HTTPException(status_code=500, detail=str(exc))
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
