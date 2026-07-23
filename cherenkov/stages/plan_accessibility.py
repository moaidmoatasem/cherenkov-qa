"""
CHERENKOV cherenkov/stages/plan_accessibility.py
Planner for accessibility testing scenarios.
"""

from __future__ import annotations

from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
from cherenkov.sources.accessibility.contracts import AccessibilityScenario


class AccessibilityScenarioPlanner:
    """Consumes an AccessibilitySourceAdapter and outputs scenarios."""

    def plan(self, source: AccessibilitySourceAdapter) -> list[AccessibilityScenario]:
        return list(source.iter_scenarios())
