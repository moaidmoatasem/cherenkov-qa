"""
CHERENKOV cherenkov/stages/plan_accessibility.py
Planner for accessibility testing scenarios.
"""
from __future__ import annotations

from typing import List

from cherenkov.sources.accessibility.adapter import AccessibilitySourceAdapter
from cherenkov.sources.accessibility.contracts import AccessibilityScenario


class AccessibilityScenarioPlanner:
    """Consumes an AccessibilitySourceAdapter and outputs scenarios."""

    def plan(self, source: AccessibilitySourceAdapter) -> List[AccessibilityScenario]:
        return list(source.iter_scenarios())
