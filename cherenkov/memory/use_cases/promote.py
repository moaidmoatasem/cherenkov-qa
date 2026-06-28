"""Promote recurring patterns to auto-load status (use case)."""
from __future__ import annotations

from cherenkov.memory.domain.models import PromotionRule
from cherenkov.memory.ports.repository import MemoryRepository


def run_promotion(
    repo: MemoryRepository,
    rule: PromotionRule | None = None,
) -> list[str]:
    """Evaluate all patterns against the promotion rule.

    Patterns that meet ``rule.min_session_count`` are marked
    ``is_auto_loaded = True`` and will be injected into every
    future ``agent_sync before`` context load.

    Args:
        repo: MemoryRepository instance.
        rule: PromotionRule to apply (default: 3 sessions).

    Returns:
        List of fingerprints promoted in this call.
    """
    if rule is None:
        rule = PromotionRule()
    return repo.apply_promotion_rules(rule)
