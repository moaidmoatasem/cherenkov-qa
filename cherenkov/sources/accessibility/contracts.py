"""
CHERENKOV cherenkov/sources/accessibility/contracts.py
Accessibility source Pydantic models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PageTarget(BaseModel):
    url: str
    description: str = ""

class AccessibilityScenario(BaseModel):
    scenario_id: str
    page_target: PageTarget
    rules: list[str] = Field(
        default_factory=lambda: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
    )
    tags: list[str] = Field(default_factory=list)
