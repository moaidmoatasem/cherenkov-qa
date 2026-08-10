"""
cherenkov/core/flags.py — Lightweight feature flag system.

Flags are defined in code with a default value and an optional description.
At runtime the value resolves in priority order:

    1. CHERENKOV_FLAG_<NAME>=true/false  (env var override — highest priority)
    2. JSON file at CHERENKOV_FLAGS_FILE (optional; hot-reloaded on each read)
    3. In-process override via set_flag() (for tests / runtime mutation)
    4. Compiled-in default

Flag names are UPPER_SNAKE_CASE. The env var prefix strips the CHERENKOV_FLAG_ prefix.

Usage:
    from cherenkov.core.flags import flag, set_flag

    if flag("NEW_GRPC_PLANNER"):
        ...

    # In tests:
    set_flag("NEW_GRPC_PLANNER", True)

    # Add new flags here — default=False means safe to ship dark.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from cherenkov.core.errors import get_logger

_log = get_logger("FLAGS")

_LOCK = threading.RLock()

# ── compiled-in defaults ────────────────────────────────────────────────────
# Add new flags here. Default False = safe dark launch.
_DEFAULTS: dict[str, bool] = {
    # Core pipeline
    "NEW_GRPC_PLANNER": False,          # next-gen gRPC scenario planner
    "NEW_GRAPHQL_PLANNER": False,       # next-gen GraphQL scenario planner
    "ASYNC_VALIDATE_ENGINE": False,     # async-first ValidationEngine
    "EVAL_REGRESSION_CI": True,         # run eval regression check in CI (on by default)
    # Security
    "RATE_LIMIT_STRICT": False,         # drop burst to 5 for public deployments
    "PII_HARD_BLOCK": False,            # reject requests containing PII instead of redacting
    # Enterprise
    "MULTI_TENANT_ROW_SECURITY": False, # per-org data partitioning
    "AUDIT_LOG_STREAM": False,          # stream audit events to external SIEM
    # UI
    "VISUAL_REGRESSION_SCREEN": False,  # VLM visual diffing screen in UI
    "DARK_MODE_DEFAULT": False,         # start UI in dark mode
}

# ── runtime overrides (set_flag / tests) ────────────────────────────────────
_OVERRIDES: dict[str, bool] = {}

_FLAGS_FILE_PATH: Path | None = (
    Path(os.getenv("CHERENKOV_FLAGS_FILE", "")) if os.getenv("CHERENKOV_FLAGS_FILE") else None
)


def _load_file() -> dict[str, bool]:
    if _FLAGS_FILE_PATH is None or not _FLAGS_FILE_PATH.exists():
        return {}
    try:
        raw = json.loads(_FLAGS_FILE_PATH.read_text(encoding="utf-8"))
        return {k.upper(): bool(v) for k, v in raw.items() if isinstance(v, bool)}
    except (OSError, ValueError, AttributeError) as exc:
        _log.warning(
            "flags file unreadable — falling back to compiled-in defaults",
            path=str(_FLAGS_FILE_PATH),
            error=f"{type(exc).__name__}: {exc}",
        )
        return {}


def _env_value(name: str) -> bool | None:
    env_key = f"CHERENKOV_FLAG_{name.upper()}"
    val = os.getenv(env_key)
    if val is None:
        return None
    return val.lower() in ("true", "1", "yes", "on")


def flag(name: str) -> bool:
    """Return the resolved value for flag `name`.

    Resolution order: env var > runtime override > flags file > compiled default.
    Unknown flags return False (safe default) rather than raising.

    Args:
        name (str): Upper-snake-case feature flag name.

    Returns:
        bool: Resolved boolean value for the flag.
    """
    name = name.upper()
    with _LOCK:
        # 1. env var
        env_val = _env_value(name)
        if env_val is not None:
            return env_val

        # 2. in-process override
        if name in _OVERRIDES:
            return _OVERRIDES[name]

        # 3. flags file (hot-reloaded)
        file_flags = _load_file()
        if name in file_flags:
            return file_flags[name]

        # 4. compiled default
        return _DEFAULTS.get(name, False)


def set_flag(name: str, value: bool) -> None:
    """Override a flag at runtime. Primarily for tests.

    Args:
        name (str): Feature flag name string.
        value (bool): Override value to set.

    Returns:
        None
    """
    with _LOCK:
        _OVERRIDES[name.upper()] = value


def reset_flags() -> None:
    """Clear all runtime overrides. Call in test teardown.

    Returns:
        None
    """
    with _LOCK:
        _OVERRIDES.clear()


def all_flags() -> dict[str, bool]:
    """Return resolved values for all compiled-in flags (useful for /debug endpoint).

    Returns:
        dict[str, bool]: Dictionary mapping all compiled-in flag names to resolved boolean values.
    """
    with _LOCK:
        return {name: flag(name) for name in _DEFAULTS}

