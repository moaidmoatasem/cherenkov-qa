"""
cherenkov/substrate/retry.py — Exponential back-off retry for LLM substrate calls.

Wraps a callable with retry logic for transient provider errors (rate limits,
temporary unavailability). Budget errors and certification failures are
re-raised immediately (not retried — they are permanent for this run).

Usage:
    from cherenkov.substrate.retry import with_retry

    result = with_retry(provider.generate, request, max_attempts=3)

    # Or as a decorator:
    @retryable(max_attempts=3, base_delay=1.0)
    def my_func(...): ...

Configuration (env vars):
    CHERENKOV_RETRY_MAX_ATTEMPTS  — int, default 3
    CHERENKOV_RETRY_BASE_DELAY    — float seconds, default 1.0
    CHERENKOV_RETRY_MAX_DELAY     — float seconds, default 30.0
    CHERENKOV_RETRY_ENABLED       — set "false" to disable (for tests)
"""

from __future__ import annotations

import functools
import os
import time
import random
from typing import Any, Callable

from cherenkov.core.errors import get_logger

_log = get_logger("RETRY")

_MAX_ATTEMPTS = int(os.getenv("CHERENKOV_RETRY_MAX_ATTEMPTS", "3"))
_BASE_DELAY = float(os.getenv("CHERENKOV_RETRY_BASE_DELAY", "1.0"))
_MAX_DELAY = float(os.getenv("CHERENKOV_RETRY_MAX_DELAY", "30.0"))
_ENABLED = os.getenv("CHERENKOV_RETRY_ENABLED", "true").lower() not in ("false", "0", "no")

# Errors that should never be retried — re-raise immediately
_NO_RETRY_TYPES: tuple[type, ...] = ()

# Error message substrings that indicate a permanent (non-retryable) failure
_PERMANENT_SUBSTRINGS: tuple[str, ...] = (
    "budget exceeded",
    "certification failed",
    "content policy",
    "invalid api key",
    "authentication",
    "unauthorized",
    "forbidden",
)

# Substrings that indicate a transient (retryable) failure
_TRANSIENT_SUBSTRINGS: tuple[str, ...] = (
    "rate limit",
    "429",
    "503",
    "502",
    "timeout",
    "connection",
    "temporarily unavailable",
    "overloaded",
    "server error",
    "internal server error",
)


def _is_retryable(exc: Exception) -> bool:
    """Return True if *exc* looks like a transient error worth retrying."""
    msg = str(exc).lower()

    # Explicit permanent patterns — never retry
    if any(p in msg for p in _PERMANENT_SUBSTRINGS):
        return False

    # Known transient patterns — always retry
    if any(p in msg for p in _TRANSIENT_SUBSTRINGS):
        return True

    # Unknown errors: retry by default (conservative — don't silence real errors)
    return True


def _delay(attempt: int, base: float, maximum: float) -> float:
    """Full-jitter exponential back-off: uniform(0, min(max, base * 2^attempt))."""
    ceiling = min(maximum, base * (2 ** attempt))
    return random.uniform(0, ceiling)  # noqa: S311 — not used for crypto


def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    max_delay: float = _MAX_DELAY,
    **kwargs: Any,
) -> Any:
    """Call *fn(*args, **kwargs)* with exponential back-off on transient errors.

    Args:
        fn: The callable to invoke.
        *args / **kwargs: Forwarded to *fn*.
        max_attempts: Total attempts before re-raising (default 3).
        base_delay: Base delay in seconds for back-off calculation (default 1.0).
        max_delay: Maximum delay cap in seconds (default 30.0).

    Returns:
        The return value of *fn* on success.

    Raises:
        The last exception if all attempts fail, or immediately if the error
        is classified as non-retryable.
    """
    if not _ENABLED:
        return fn(*args, **kwargs)

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            # Check for known permanent error types first
            try:
                from cherenkov.core.budget import BudgetExceededError
                if isinstance(exc, BudgetExceededError):
                    raise
            except ImportError:
                pass

            try:
                from cherenkov.substrate.certification import CertificationError
                if isinstance(exc, CertificationError):
                    raise
            except ImportError:
                pass

            if not _is_retryable(exc):
                _log.info("non-retryable error — not retrying", error=str(exc)[:120])
                raise

            last_exc = exc
            remaining = max_attempts - attempt - 1
            if remaining == 0:
                break

            wait = _delay(attempt, base_delay, max_delay)
            _log.warning(
                "transient error — retrying",
                attempt=attempt + 1,
                remaining=remaining,
                wait_s=round(wait, 2),
                error=str(exc)[:120],
            )
            time.sleep(wait)

    assert last_exc is not None
    raise last_exc


def retryable(
    max_attempts: int = _MAX_ATTEMPTS,
    base_delay: float = _BASE_DELAY,
    max_delay: float = _MAX_DELAY,
) -> Callable:
    """Decorator factory — wraps a function with retry logic.

    Example:
        @retryable(max_attempts=4, base_delay=0.5)
        def call_llm(request): ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return with_retry(
                fn, *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                **kwargs,
            )
        return wrapper
    return decorator
