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

    Attributes:
        event (HookEvent): Named hook event trigger point.
        run (str): Shell command template string to execute.
        timeout (int): Maximum execution timeout in seconds. Defaults to 30.
        fail_mode (FailMode): Action to take on failure (WARN or ABORT). Defaults to FailMode.WARN.
        env (dict[str, str]): Extra environment variables to pass to hook process.
    """

    event: HookEvent
    run: str                         # Shell command template
    timeout: int = 30                # Seconds before TIMEOUT
    fail_mode: FailMode = FailMode.WARN
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class HookContext:
    """Runtime context injected into hook command templates.

    Attributes:
        report_path (str): Path to latest report JSON file. Defaults to "".
        output_dir (str): Eject output directory path. Defaults to "".
        verdict (str): Review verdict string. Defaults to "".
        endpoint (str): Current endpoint being tested. Defaults to "".
        spec_path (str): Path to OpenAPI specification file. Defaults to "".
    """

    report_path: str = ""
    output_dir: str = ""
    verdict: str = ""
    endpoint: str = ""
    spec_path: str = ""

    def as_template_vars(self) -> dict[str, str]:
        """Convert runtime context parameters into a template substitution dictionary.

        Returns:
            dict[str, str]: Dictionary mapping context field names to string values.
        """
        return {
            "report_path": self.report_path,
            "output_dir": self.output_dir,
            "verdict": self.verdict,
            "endpoint": self.endpoint,
            "spec_path": self.spec_path,
        }


@dataclass
class HookResult:
    """Result of executing a single hook.

    Attributes:
        event (HookEvent): Hook event trigger point.
        status (HookStatus): Execution outcome status enum.
        command (str): Rendered command string executed.
        exit_code (int | None): Subprocess exit code, or None if timed out/failed.
        stdout (str): Captured standard output. Defaults to "".
        stderr (str): Captured standard error. Defaults to "".
        duration_ms (int): Execution duration in milliseconds. Defaults to 0.
        error_message (str): Diagnostic error message if failed. Defaults to "".
        executed_at (datetime): UTC timestamp when hook was executed.
    """

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
        """Check if the hook execution status was successful.

        Returns:
            bool: True if status is HookStatus.SUCCESS, False otherwise.
        """
        return self.status == HookStatus.SUCCESS


class HookAbortError(Exception):
    """Raised when a hook with fail_mode=abort exits non-zero."""

    def __init__(self, event: HookEvent, result: HookResult) -> None:
        """Initialize HookAbortError with the failed event and result object.

        Args:
            event (HookEvent): The hook event that triggered the abort.
            result (HookResult): Execution result details for the failed hook.

        Returns:
            None
        """
        self.event = event
        self.result = result
        super().__init__(
            f"Hook {event.value!r} aborted pipeline: exit_code={result.exit_code} "
            f"stderr={result.stderr!r}"
        )

