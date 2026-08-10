"""HookRegistry — loads hook configurations from cherenkov.toml (ADR-012)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from cherenkov.hooks.domain.models import (
    FailMode,
    HookConfig,
    HookEvent,
)

_log = logging.getLogger(__name__)

# All valid hook event names — used for config validation
_VALID_EVENTS: frozenset[str] = frozenset(e.value for e in HookEvent)


class HookRegistry:
    """Load and validate hook configurations from a cherenkov.toml config dict.

    Attributes:
        _configs (dict[HookEvent, list[HookConfig]]): Internal mapping of events to hook lists.
    """

    def __init__(self, configs: dict[HookEvent, list[HookConfig]]) -> None:
        """Initialize HookRegistry with event-to-hook mapping.

        Args:
            configs (dict[HookEvent, list[HookConfig]]): Mapping of HookEvent to lists of HookConfig.

        Returns:
            None
        """
        self._configs = configs

    @classmethod
    def from_config(cls, hooks_section: dict[str, Any]) -> HookRegistry:
        """Parse the ``[hooks.*]`` TOML section into HookConfig objects.

        Args:
            hooks_section (dict[str, Any]): The raw dict from ``config["hooks"]``.

        Returns:
            HookRegistry: Populated HookRegistry instance.

        Raises:
            ValueError: If an unknown hook event name is found in the config.
        """
        configs: dict[HookEvent, list[HookConfig]] = {}

        for event_name, raw in hooks_section.items():
            if event_name not in _VALID_EVENTS:
                raise ValueError(
                    f"Unknown hook event {event_name!r} in cherenkov.toml [hooks.*]. "
                    f"Valid events: {sorted(_VALID_EVENTS)}"
                )
            event = HookEvent(event_name)

            # Support both single-table and list-of-tables format
            entries = raw if isinstance(raw, list) else [raw]

            hook_list: list[HookConfig] = []
            for entry in entries:
                if not isinstance(entry, dict) or "run" not in entry:
                    _log.warning("Skipping malformed hook config for %r: %r", event_name, entry)
                    continue

                fail_mode_str = entry.get("fail_mode", "warn")
                try:
                    fail_mode = FailMode(fail_mode_str)
                except ValueError:
                    _log.warning(
                        "Unknown fail_mode %r for hook %r, defaulting to 'warn'",
                        fail_mode_str,
                        event_name,
                    )
                    fail_mode = FailMode.WARN

                hook_list.append(
                    HookConfig(
                        event=event,
                        run=entry["run"],
                        timeout=int(entry.get("timeout", 30)),
                        fail_mode=fail_mode,
                        env=entry.get("env", {}),
                    )
                )

            if hook_list:
                configs.setdefault(event, []).extend(hook_list)

        return cls(configs)

    @classmethod
    def empty(cls) -> HookRegistry:
        """Return an empty registry (no hooks configured).

        Returns:
            HookRegistry: An unpopulated HookRegistry instance.
        """
        return cls({})

    def get(self, event: HookEvent) -> list[HookConfig]:
        """Return all HookConfig objects registered for the given event.

        Args:
            event (HookEvent): The hook event to look up.

        Returns:
            list[HookConfig]: List of configured hooks for the event.
        """
        return self._configs.get(event, [])

    def has(self, event: HookEvent) -> bool:
        """Check if at least one hook is configured for the event.

        Args:
            event (HookEvent): The hook event to check.

        Returns:
            bool: True if at least one hook is registered, False otherwise.
        """
        return bool(self._configs.get(event))

    def all_events(self) -> list[HookEvent]:
        """Return all events that have at least one hook registered.

        Returns:
            list[HookEvent]: List of hook events with active configurations.
        """
        return list(self._configs)

    def __repr__(self) -> str:
        """Return developer string representation of the registry.

        Returns:
            str: String representation summarizing event counts.
        """
        summary = {e.value: len(cfgs) for e, cfgs in self._configs.items()}
        return f"HookRegistry({summary})"


def load_registry_from_project(project_root: Path | None = None) -> HookRegistry:
    """Convenience factory: load HookRegistry from the project's cherenkov.toml.

    Args:
        project_root (Path | None): Optional path to project root. Defaults to None (CWD auto-detection).

    Returns:
        HookRegistry: Loaded HookRegistry instance or empty registry on failure.
    """
    try:
        from cherenkov.core.config_loader import LayeredConfig

        # If a project_root is provided, temporarily set CWD so config_loader
        # walks from the correct location.
        if project_root is not None:
            original_cwd = Path.cwd()
            os.chdir(project_root)
        else:
            original_cwd = None

        try:
            cfg = LayeredConfig()
            raw_hooks = cfg.get("hooks") or {}
            return HookRegistry.from_config(raw_hooks)
        finally:
            if original_cwd is not None:
                os.chdir(original_cwd)
    except Exception as exc:
        _log.debug("Could not load hook registry: %s", exc)
        return HookRegistry.empty()

