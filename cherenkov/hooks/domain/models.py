"""Hook system — domain models.

Pure business logic; no I/O, no subprocess calls (ADR-004).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class HookEvent(str, Enum):
    """Named pipeline hook points (ADR-012)."""

    PRE_GENERATE = "pre_generate"
    POST_GENERATE = "post_generate"
    PRE_REVIEW = "pre_review"
    POST_REVIEW = "post_review"
    PRE_VALIDATE = "pre_validate"
    POST_VALIDATE = "post_validate"
    PRE_EJECT = "pre_eject"
    POST_EJECT = "post_eject"
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"


class FailMode(str, Enum):
    """Behaviour when a hook command exits non-zero or times out."""

    WARN = "warn"   # Log and continue (default — non-breaking)
    ABORT = "abort"  # Raise HookAbortError and stop the pipeline


class HookStatus(str, Enum):
    """Outcome of a hook execution attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class HookConfig:
    """Configuration for a single hook, loaded from cherenkov.toml.

    Example TOML::

        [hooks.post_validate]
        run = "python scripts/notify_slack.py {report_path}"
        timeout = 30
        fail_mode = "warn"
        env = { SLACK_CHANNEL = "#qa-alerts" }
    """

    event: HookEvent
    run: str                         # Shell command template
    timeout: int = 30                # Seconds before TIMEOUT
    fail_mode: FailMode = FailMode.WARN
    env: dict[str, str] = field(default_factory=dict)

    # Template variables injected by CHERENKOV at fire time:
    #   {report_path}  — path to latest report JSON
    #   {output_dir}   — eject output directory
    #   {verdict}      — review verdict string
    #   {endpoint}     — current endpoint
    #   {spec_path}    — path to OpenAPI spec


@dataclass
class HookContext:
    """Runtime context injected into hook command templates."""

    report_path: str = ""
    output_dir: str = ""
    verdict: str = ""
    endpoint: str = ""
    spec_path: str = ""

    def as_template_vars(self) -> dict[str, str]:
        return {
            "report_path": self.report_path,
            "output_dir": self.output_dir,
            "verdict": self.verdict,
            "endpoint": self.endpoint,
            "spec_path": self.spec_path,
        }


@dataclass
class HookResult:
    """Result of executing a single hook."""

    event: HookEvent
    status: HookStatus
    command: str                     # Rendered command that was run
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error_message: str = ""
    executed_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def success(self) -> bool:
        return self.status == HookStatus.SUCCESS


class HookAbortError(Exception):
    """Raised when a hook with fail_mode=abort exits non-zero."""

    def __init__(self, event: HookEvent, result: HookResult) -> None:
        self.event = event
        self.result = result
        super().__init__(
            f"Hook {event.value!r} aborted pipeline: exit_code={result.exit_code} "
            f"stderr={result.stderr!r}"
        )
