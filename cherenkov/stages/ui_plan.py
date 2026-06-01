"""
CHERENKOV stages/ui_plan.py — UI scenario and specification Pydantic models.
Authority: v3.1 + delta.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

class UIElement(BaseModel):
    """Represents an interactive element discovered on the UI page."""
    id: str
    selector: str
    tag: str
    type: str = "button"
    label: str | None = None


class UISpec(BaseModel):
    """Visual page specification containing URL and interactive elements list."""
    url: str
    elements: list[UIElement] = Field(default_factory=list)


class UIScenario(BaseModel):
    """UI test automation scenario describing step actions."""
    id: str
    name: str
    description: str
    steps: list[str] = Field(default_factory=list)
