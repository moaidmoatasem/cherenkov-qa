from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    viewer   = "viewer"    # read-only
    reviewer = "reviewer"  # can approve/reject HITL divergences
    admin    = "admin"     # user management + full access

    @classmethod
    def hierarchy(cls) -> list[Role]:
        return [cls.viewer, cls.reviewer, cls.admin]

    def __ge__(self, other: Role) -> bool:
        h = Role.hierarchy()
        return h.index(self) >= h.index(other)


class User(BaseModel):
    username: str
    role: Role
    disabled: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role


class UserInDB(User):
    hashed_password: str
