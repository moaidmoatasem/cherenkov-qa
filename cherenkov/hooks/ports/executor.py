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

        Args:
            config (HookConfig): Hook configuration object detailing run command, timeout, and fail mode.
            context (HookContext): Runtime context containing template variables to substitute into command.

        Returns:
            HookResult: Result containing status, exit code, stdout, stderr, and execution duration.

        Raises:
            HookAbortError: If config.fail_mode is ABORT and command fails or times out.
        """
        ...

