"""Data models and Enums for web authentication and user roles."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    """User authorization roles ordered by access hierarchy."""
    viewer   = "viewer"    # read-only
    reviewer = "reviewer"  # can approve/reject HITL divergences
    admin    = "admin"     # user management + full access

    @classmethod
    def hierarchy(cls) -> list[Role]:
        """Return roles in ascending order of privilege.

        Returns:
            List of Role enum members from lowest to highest privilege.
        """
        return [cls.viewer, cls.reviewer, cls.admin]

    def __ge__(self, other: Role) -> bool:  # type: ignore[override]  # TODO(#type-debt): str supertype expects str arg
        """Compare role privilege level against another role.

        Args:
            other: Role enum member to compare against.

        Returns:
            True if self has equal or higher privilege than other, False otherwise.
        """
        h = Role.hierarchy()
        return h.index(self) >= h.index(other)


class User(BaseModel):
    """Authenticated user domain model."""
    username: str
    role: Role
    disabled: bool = False
    organization_id: str = "default"


class TokenResponse(BaseModel):
    """JWT token issuance response payload."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role
    organization_id: str = "default"


class UserInDB(User):
    """User database record including password hash."""
    hashed_password: str
