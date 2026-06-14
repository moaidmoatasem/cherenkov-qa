from __future__ import annotations

from dataclasses import dataclass

from cherenkov.core.config import Config


@dataclass
class AutonomyProfile:
    level: str
    label: str
    description: str
    auto_approve: bool = False
    auto_triage: bool = False
    deep_rerank: bool = False
    auto_remediate: bool = False


PROFILE_LEVELS: dict[str, AutonomyProfile] = {
    "assisted": AutonomyProfile(
        level="assisted",
        label="Assisted",
        description="Tester authors tests manually; Copilot suggests idioms and surfaces risk digest.",
        auto_approve=False,
        auto_triage=False,
        deep_rerank=False,
        auto_remediate=False,
    ),
    "augmented": AutonomyProfile(
        level="augmented",
        label="Augmented",
        description="Copilot auto-triages failures and recommends fixes; human still approves.",
        auto_approve=False,
        auto_triage=True,
        deep_rerank=True,
        auto_remediate=False,
    ),
    "agentic": AutonomyProfile(
        level="agentic",
        label="Agentic",
        description="Copilot auto-approves low-risk findings, auto-remediates known patterns, routes edge cases to human.",
        auto_approve=True,
        auto_triage=True,
        deep_rerank=True,
        auto_remediate=True,
    ),
    "predictive": AutonomyProfile(
        level="predictive",
        label="Predictive",
        description="Copilot anticipates failures before they occur, pre-authors tests, and self-heals known drifts autonomously.",
        auto_approve=True,
        auto_triage=True,
        deep_rerank=True,
        auto_remediate=True,
    ),
}


def get_profile() -> AutonomyProfile:
    current = Config.COPILOT_AUTONOMY
    return PROFILE_LEVELS.get(current, PROFILE_LEVELS["assisted"])


def set_profile(level: str) -> AutonomyProfile:
    if level not in PROFILE_LEVELS:
        raise ValueError(
            f"Unknown autonomy level '{level}'. Valid: {', '.join(PROFILE_LEVELS.keys())}"
        )
    Config.COPILOT_AUTONOMY = level
    return PROFILE_LEVELS[level]
