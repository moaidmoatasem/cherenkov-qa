"""Application-level Role-Based Access Control for CHERENKOV enterprise mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


class Role(str, Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    READ_ONLY = "read_only"


class Permission(str, Enum):
    # HITL actions
    HITL_LIST = "hitl:list"
    HITL_APPROVE = "hitl:approve"
    HITL_REJECT = "hitl:reject"
    # Validation
    VALIDATE_RUN = "validate:run"
    VALIDATE_VIEW = "validate:view"
    # MCP tools
    MCP_LIST = "mcp:list"
    MCP_PUBLISH = "mcp:publish"
    # Enterprise
    RBAC_MANAGE = "rbac:manage"
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"
    GDPR_MANAGE = "gdpr:manage"
    SOC2_GENERATE = "soc2:generate"
    # Config
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"


# Default role-permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: {
        Permission.HITL_LIST,
        Permission.HITL_APPROVE,
        Permission.HITL_REJECT,
        Permission.VALIDATE_RUN,
        Permission.VALIDATE_VIEW,
        Permission.MCP_LIST,
        Permission.MCP_PUBLISH,
        Permission.RBAC_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.GDPR_MANAGE,
        Permission.SOC2_GENERATE,
        Permission.CONFIG_READ,
        Permission.CONFIG_WRITE,
    },
    Role.ENGINEER: {
        Permission.HITL_LIST,
        Permission.HITL_APPROVE,
        Permission.HITL_REJECT,
        Permission.VALIDATE_RUN,
        Permission.VALIDATE_VIEW,
        Permission.MCP_LIST,
        Permission.MCP_PUBLISH,
        Permission.AUDIT_VIEW,
        Permission.CONFIG_READ,
    },
    Role.VIEWER: {
        Permission.HITL_LIST,
        Permission.VALIDATE_VIEW,
        Permission.MCP_LIST,
        Permission.AUDIT_VIEW,
        Permission.CONFIG_READ,
    },
    Role.READ_ONLY: {
        Permission.VALIDATE_VIEW,
        Permission.CONFIG_READ,
    },
}


@dataclass
class User:
    id: str
    name: str
    email: str
    role: Role = Role.VIEWER
    teams: list[str] = field(default_factory=list)
    saml_assertion: str = ""


class RBACEngine:
    """Application-level RBAC enforcement.

    Integrates with SAML SSO for identity and provides permission checks
    across all CHERENKOV subsystems.
    """

    def __init__(self):
        self._users: dict[str, User] = {}

    def register_user(self, user: User) -> None:
        self._users[user.id] = user
        log.info("Registered user", user_id=user.id, role=user.role.value)

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def remove_user(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        return permission in ROLE_PERMISSIONS.get(user.role, set())

    def require_permission(self, user_id: str, permission: Permission) -> None:
        if not self.has_permission(user_id, permission):
            raise PermissionError(
                f"User {user_id} lacks required permission: {permission.value}"
            )

    def set_role(self, user_id: str, role: Role) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user.role = role
        log.info("Role changed", user_id=user_id, role=role.value)
        return True

    def user_has_any(self, user_id: str, permissions: list[Permission]) -> bool:
        return any(self.has_permission(user_id, p) for p in permissions)


# Global singleton
_engine = RBACEngine()


def get_rbac() -> RBACEngine:
    return _engine
