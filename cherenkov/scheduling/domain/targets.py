"""The only callables a routine is allowed to schedule.

A routine's ``target_module`` is resolved with ``importlib`` and invoked on a
schedule with caller-supplied kwargs. Accepting arbitrary ``module:func`` strings
turned ``POST /routines/`` into remote code execution (``os:system`` with
``{"command": ...}``), so targets are an explicit allowlist, checked at the
model, the use case, the API, the CLI and again in the adapter right before the
import. Add a new routine template here deliberately, never by widening a check.
"""
from __future__ import annotations

ALLOWED_ROUTINE_TARGETS: frozenset[str] = frozenset({
    "cherenkov.scheduling.templates.daily_health_check:run",
    "cherenkov.scheduling.templates.spec_monitor:run",
})


def check_routine_target(target: str) -> str:
    """Return ``target`` unchanged, or raise ``ValueError`` if it is not allowlisted."""
    if target not in ALLOWED_ROUTINE_TARGETS:
        allowed = ", ".join(sorted(ALLOWED_ROUTINE_TARGETS))
        raise ValueError(f"{target!r} is not an allowed routine target. Allowed: {allowed}")
    return target
