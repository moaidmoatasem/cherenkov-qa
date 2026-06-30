"""PlaybookMatcher — evaluates which playbooks apply to a given endpoint."""

from __future__ import annotations

from cherenkov.playbooks.models import Playbook, PlaybookTrigger


class PlaybookMatcher:
    """Selects the subset of playbooks whose trigger conditions match an endpoint."""

    def __init__(self, playbooks: list[Playbook]) -> None:
        self._playbooks = playbooks

    def match(
        self,
        path: str,
        method: str,
        tags: list[str] | None = None,
    ) -> list[Playbook]:
        """Return every playbook whose trigger is satisfied by the given endpoint."""
        method = method.upper()
        tags = tags or []
        return [pb for pb in self._playbooks if self._matches(pb.trigger, path, method, tags)]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _matches(trigger: PlaybookTrigger, path: str, method: str, tags: list[str]) -> bool:
        if trigger.is_empty():
            return True

        if trigger.methods and method not in trigger.methods:
            return False

        if trigger.path_prefix and not path.startswith(trigger.path_prefix):
            return False

        if trigger.path_contains and trigger.path_contains not in path:
            return False

        if trigger.tags and not any(t in tags for t in trigger.tags):
            return False

        return True
