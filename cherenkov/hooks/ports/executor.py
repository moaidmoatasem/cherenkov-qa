"""HookExecutor — port protocol (ADR-004, ADR-012)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from cherenkov.hooks.domain.models import HookConfig, HookContext, HookResult


@runtime_checkable
class HookExecutor(Protocol):
    """Port for executing a configured hook command."""

    def execute(self, config: HookConfig, context: HookContext) -> HookResult:
        """Run the hook command, returning a HookResult.

        Must NOT raise on hook failure when ``config.fail_mode == FailMode.WARN``.
        MUST raise ``HookAbortError`` when ``config.fail_mode == FailMode.ABORT``
        and the command exits non-zero or times out.
        """
        ...
