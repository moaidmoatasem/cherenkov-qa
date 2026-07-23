"""Playbooks — reusable, auto-triggering validation strategies.

Inspired by RedPlanetHQ/core's "Skills" system: named instructions that
fire automatically when their trigger conditions match an endpoint.
"""

from cherenkov.playbooks.matcher import PlaybookMatcher
from cherenkov.playbooks.models import Playbook, PlaybookFinding, PlaybookTrigger
from cherenkov.playbooks.registry import PlaybookRegistry
from cherenkov.playbooks.runner import PlaybookRunner

__all__ = [
    "Playbook",
    "PlaybookFinding",
    "PlaybookMatcher",
    "PlaybookRegistry",
    "PlaybookRunner",
    "PlaybookTrigger",
]
