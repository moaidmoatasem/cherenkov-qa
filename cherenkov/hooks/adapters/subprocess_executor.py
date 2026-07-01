"""SubprocessHookExecutor — default HookExecutor adapter (ADR-012).

Runs hook commands as shell subprocesses with timeout enforcement,
template variable substitution, and environment injection.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import time

from cherenkov.hooks.domain.models import (
    FailMode,
    HookAbortError,
    HookConfig,
    HookContext,
    HookResult,
    HookStatus,
)


class SubprocessHookExecutor:
    """Execute hooks as shell subprocesses (ADR-012 default adapter)."""

    def execute(self, config: HookConfig, context: HookContext) -> HookResult:
        """Run config.run as a shell command, returning a HookResult.

        Raises HookAbortError if fail_mode=abort and command fails.
        """
        # Render template variables into the command string.
        # shlex.quote() prevents shell metacharacters in substituted values
        # (e.g. endpoint URLs, file paths) from escaping the intended command.
        template_vars = context.as_template_vars()
        safe_vars = {k: shlex.quote(v) if v else "''" for k, v in template_vars.items()}
        try:
            rendered_cmd = config.run.format(**safe_vars)
        except KeyError as exc:
            # Unknown template variable — treat as FAILED
            result = HookResult(
                event=config.event,
                status=HookStatus.FAILED,
                command=config.run,
                error_message=f"Unknown template variable: {exc}",
            )
            return self._handle_failure(config, result)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                rendered_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config.timeout,
                env={**_current_env(), **config.env},
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            if proc.returncode == 0:
                return HookResult(
                    event=config.event,
                    status=HookStatus.SUCCESS,
                    command=rendered_cmd,
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    duration_ms=duration_ms,
                )
            result = HookResult(
                event=config.event,
                status=HookStatus.FAILED,
                command=rendered_cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration_ms,
                error_message=f"Exit code {proc.returncode}",
            )
            return self._handle_failure(config, result)

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            result = HookResult(
                event=config.event,
                status=HookStatus.TIMEOUT,
                command=rendered_cmd,
                duration_ms=duration_ms,
                error_message=f"Timed out after {config.timeout}s",
            )
            return self._handle_failure(config, result)

    @staticmethod
    def _handle_failure(config: HookConfig, result: HookResult) -> HookResult:
        """Apply fail_mode policy to a non-success result."""
        if config.fail_mode == FailMode.ABORT:
            raise HookAbortError(config.event, result)
        # FailMode.WARN — return the result; caller logs the warning
        return result


def _current_env() -> dict[str, str]:
    """Return a copy of the current process environment."""
    return dict(os.environ)
