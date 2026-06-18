"""Multi-tenant organization management for CHERENKOV enterprise mode."""

from __future__ import annotations

from dataclasses import dataclass, field
import uuid

from cherenkov.core.errors import get_logger

log = get_logger(__name__)


@dataclass
class Member:
    user_id: str
    role: str = "member"  # "owner", "admin", "member", "viewer"


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    team_ids: list[str] = field(default_factory=list)


@dataclass
class Team:
    id: str
    name: str
    members: list[Member] = field(default_factory=list)


@dataclass
class Organization:
    id: str
    name: str
    owner_id: str
    teams: dict[str, Team] = field(default_factory=dict)
    projects: dict[str, Project] = field(default_factory=dict)
    members: list[Member] = field(default_factory=list)
    tier: str = "enterprise"
    quota_max_users: int = 100
    quota_max_runs_per_month: int = 10000


class OrgManager:
    """Manages multi-tenant organizations, teams, and projects."""

    def __init__(self):
        self._orgs: dict[str, Organization] = {}

    def create_org(self, name: str, owner_id: str) -> Organization:
        org_id = f"org_{uuid.uuid4().hex[:8]}"
        org = Organization(
            id=org_id,
            name=name,
            owner_id=owner_id,
            members=[Member(user_id=owner_id, role="owner")],
        )
        self._orgs[org_id] = org
        log.info("Created organization", org_id=org_id, name=name)
        return org

    def get_org(self, org_id: str) -> Organization | None:
        return self._orgs.get(org_id)

    def list_orgs(self) -> list[Organization]:
        return list(self._orgs.values())

    def add_member(self, org_id: str, user_id: str, role: str = "member") -> bool:
        org = self.get_org(org_id)
        if not org:
            return False
        if len(org.members) >= org.quota_max_users:
            log.warning("Org user quota exceeded", org_id=org_id)
            return False
        if not any(m.user_id == user_id for m in org.members):
            org.members.append(Member(user_id=user_id, role=role))
            return True
        return False

    def remove_member(self, org_id: str, user_id: str) -> bool:
        org = self.get_org(org_id)
        if not org:
            return False
        initial_count = len(org.members)
        org.members = [m for m in org.members if m.user_id != user_id]
        return len(org.members) < initial_count

    def create_team(self, org_id: str, name: str) -> Team | None:
        org = self.get_org(org_id)
        if not org:
            return None
        team_id = f"team_{uuid.uuid4().hex[:8]}"
        team = Team(id=team_id, name=name)
        org.teams[team_id] = team
        return team

    def create_project(self, org_id: str, name: str) -> Project | None:
        org = self.get_org(org_id)
        if not org:
            return None
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        project = Project(id=project_id, name=name)
        org.projects[project_id] = project
        return project

    def is_member(self, org_id: str, user_id: str) -> bool:
        org = self.get_org(org_id)
        if not org:
            return False
        return any(m.user_id == user_id for m in org.members)


# Global singleton
_manager = OrgManager()


def get_org_manager() -> OrgManager:
    return _manager
