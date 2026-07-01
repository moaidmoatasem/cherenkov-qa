"""Playbooks — reusable, auto-triggering validation strategies.

Inspired by RedPlanetHQ/core's "Skills" system: named instructions that
fire automatically when their trigger conditions match an endpoint.
"""

from cherenkov.playbooks.models import Playbook, PlaybookTrigger, PlaybookFinding
from cherenkov.playbooks.registry import PlaybookRegistry
from cherenkov.playbooks.matcher import PlaybookMatcher
from cherenkov.playbooks.runner import PlaybookRunner

__all__ = [
    "Playbook",
    "PlaybookTrigger",
    "PlaybookFinding",
    "PlaybookRegistry",
    "PlaybookMatcher",
    "PlaybookRunner",
]
