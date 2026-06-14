"""
CHERENKOV cherenkov/sources/accessibility/contracts.py
Accessibility source Pydantic models.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PageTarget(BaseModel):
    url: str
    description: str = ""


class AccessibilityScenario(BaseModel):
    scenario_id: str
    page_target: PageTarget
    rules: List[str] = Field(
        default_factory=lambda: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
    )
    tags: List[str] = Field(default_factory=list)
