"""
cherenkov/core/config_loader.py — Layered configuration with provenance.
Authority: v3.1 + delta. Epoch 5 (E5-2).

Resolution order (lowest → highest precedence):
  built-in defaults
    → profile (laptop | ci | enterprise-vpc | frontier-cloud)
      → cherenkov.toml (project)
        → environment variables (CHERENKOV_*)
          → CLI flags
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from cherenkov.core.errors import CherenkovError


class ConfigError(CherenkovError):
    code = "CONFIG_ERROR"


# ── Known key schema ─────────────────────────────────────────────────────
# Keys the system understands. Unknown keys in cherenkov.toml → explicit error.

KNOWN_KEYS: set[str] = {
    "profile",
    "sources.openapi", "sources.traffic", "sources.db_schema",
    "substrate.egress",
    "substrate.tiers.small.provider", "substrate.tiers.small.model",
    "substrate.tiers.deep.provider", "substrate.tiers.deep.model",
    "substrate.budgets.max_cost_usd_per_run", "substrate.budgets.max_latency_ms",
    "divergence.space", "divergence.adversarial_self_play", "divergence.min_severity",
    "artifacts.emitters", "artifacts.eject",
    "oracle.kind",
    "continuity.mode", "continuity.behavioral_diff_on_pr",
    "reflector.enabled", "reflector.store_path", "reflector.decay_half_life_hours",
}

# ── Profile defaults ─────────────────────────────────────────────────────

PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "laptop": {
        "substrate.egress": "internal",
        "substrate.tiers.small.provider": "ollama",
        "substrate.tiers.small.model": "qwen2.5-coder:7b",
        "substrate.tiers.deep.provider": "ollama",
        "substrate.tiers.deep.model": "deepseek-r1:8b",
        "substrate.budgets.max_cost_usd_per_run": 0.0,
        "substrate.budgets.max_latency_ms": 120000,
        "divergence.space": ["D1", "D2", "D3", "D4", "D5"],
        "divergence.adversarial_self_play": True,
        "divergence.min_severity": "low",
        "artifacts.emitters": ["playwright"],
        "artifacts.eject": True,
        "oracle.kind": "spec+prism",
        "continuity.mode": "one-shot",
        "continuity.behavioral_diff_on_pr": False,
    },
    "ci": {
        "substrate.egress": "internal",
        "substrate.tiers.small.provider": "ollama",
        "substrate.tiers.small.model": "qwen2.5-coder:7b",
        "substrate.tiers.deep.provider": "ollama",
        "substrate.tiers.deep.model": "qwen2.5-coder:7b",
        "substrate.budgets.max_cost_usd_per_run": 0.0,
        "substrate.budgets.max_latency_ms": 120000,
        "divergence.space": ["D1", "D2"],
        "divergence.adversarial_self_play": False,
        "divergence.min_severity": "medium",
        "artifacts.emitters": ["playwright"],
        "artifacts.eject": True,
        "oracle.kind": "spec+prism",
        "continuity.mode": "one-shot",
        "continuity.behavioral_diff_on_pr": True,
    },
    "enterprise-vpc": {
        "substrate.egress": "none",
        "substrate.tiers.small.provider": "ollama",
        "substrate.tiers.small.model": "qwen2.5-coder:7b",
        "substrate.tiers.deep.provider": "ollama",
        "substrate.tiers.deep.model": "deepseek-r1:8b",
        "substrate.budgets.max_cost_usd_per_run": 0.0,
        "substrate.budgets.max_latency_ms": 120000,
        "divergence.space": ["D1", "D2", "D3", "D4", "D5"],
        "divergence.adversarial_self_play": True,
        "divergence.min_severity": "low",
        "artifacts.emitters": ["playwright", "k6"],
        "artifacts.eject": True,
        "oracle.kind": "spec+prism",
        "continuity.mode": "daemon",
        "continuity.behavioral_diff_on_pr": True,
    },
    "frontier-cloud": {
        "substrate.egress": "any",
        "substrate.tiers.small.provider": "ollama",
        "substrate.tiers.small.model": "qwen2.5-coder:7b",
        "substrate.tiers.deep.provider": "openai",
        "substrate.tiers.deep.model": "gpt-4o",
        "substrate.budgets.max_cost_usd_per_run": 5.0,
        "substrate.budgets.max_latency_ms": 30000,
        "divergence.space": ["D1", "D2", "D3", "D4", "D5"],
        "divergence.adversarial_self_play": True,
        "divergence.min_severity": "low",
        "artifacts.emitters": ["playwright", "spec-patch", "pr-comment"],
        "artifacts.eject": True,
        "oracle.kind": "spec+prism",
        "continuity.mode": "one-shot",
        "continuity.behavioral_diff_on_pr": True,
    },
}

# ── Built-in defaults (lowest priority) ──────────────────────────────────

BUILTIN_DEFAULTS: dict[str, Any] = {
    "profile": "laptop",
    "sources.openapi": [],
    "sources.traffic": [],
    "sources.db_schema": [],
    "substrate.egress": "internal",
    "substrate.tiers.small.provider": "ollama",
    "substrate.tiers.small.model": "qwen2.5-coder:7b",
    "substrate.tiers.deep.provider": "ollama",
    "substrate.tiers.deep.model": "deepseek-r1:8b",
    "substrate.budgets.max_cost_usd_per_run": 0.0,
    "substrate.budgets.max_latency_ms": 120000,
    "divergence.space": ["D1", "D2", "D3", "D4", "D5"],
    "divergence.adversarial_self_play": True,
    "divergence.min_severity": "low",
    "artifacts.emitters": ["playwright"],
    "artifacts.eject": True,
    "oracle.kind": "spec+prism",
    "continuity.mode": "one-shot",
    "continuity.behavioral_diff_on_pr": False,
    "reflector.enabled": True,
    "reflector.store_path": ".cherenkov/verdicts.db",
    "reflector.decay_half_life_hours": 168.0,
}


def _flatten(d: dict, parent_key: str = "") -> dict[str, Any]:
    """Flatten a nested dict to dot-separated keys."""
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        full = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten(v, full).items())
        else:
            items.append((full, v))
    return dict(items)


def _unflatten(d: dict[str, Any]) -> dict[str, Any]:
    """Unflatten dot-separated keys back to nested dict."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def _expand_profile(value: Any) -> list[dict[str, Any]]:
    """Expand an array-valued key where each item becomes its own dict entry."""
    if isinstance(value, list):
        return [{"$item": item} for item in value]
    return [{"$item": value}]


EnvValue = tuple[str, str]  # (layer_name, value)
ConfigStore = dict[str, list[EnvValue]]  # key -> list of (source, value)


class LayeredConfig:
    """Layered configuration with full provenance tracking.

    Every config value remembers *where* it was set (layer name + source file
    if applicable). The ``doctor`` command uses this to tell users exactly
    which layer won and why.
    """

    def __init__(self):
        self._store: ConfigStore = {}
        self._errors: list[str] = []

    def load_defaults(self):
        """Layer 1: built-in defaults."""
        for k, v in BUILTIN_DEFAULTS.items():
            self._set(k, v, "built-in defaults")

    def load_profile(self, profile: str | None = None):
        """Layer 2: profile defaults (if profile is set)."""
        if profile is None or profile not in PROFILE_DEFAULTS:
            return
        for k, v in PROFILE_DEFAULTS[profile].items():
            self._set(k, v, f"profile:{profile}")

    def load_toml(self, path: str | Path | None = None) -> bool:
        """Layer 3: cherenkov.toml.

        Returns True if a config file was loaded.
        """
        if path is None:
            path = self._find_toml()
        if path is None:
            return False
        try:
            data = self._parse_toml(path)
        except ConfigError as e:
            self._errors.append(str(e))
            return False
        flat = _flatten(data)
        for full_key in flat:
            if full_key not in KNOWN_KEYS:
                self._errors.append(
                    f"Unknown config key '{full_key}' in {path}. "
                    f"Known keys: {', '.join(sorted(KNOWN_KEYS))}"
                )
                continue
        for k, v in flat.items():
            if k in KNOWN_KEYS:
                self._set(k, v, str(path))
        return True

    def load_env(self):
        """Layer 4: CHERENKOV_* environment variables.

        Mapping:
          CHERENKOV_EGRESS               -> substrate.egress
          CHERENKOV_TIER_SMALL_PROVIDER   -> substrate.tiers.small.provider
          CHERENKOV_TIER_SMALL_MODEL      -> substrate.tiers.small.model
          CHERENKOV_TIER_DEEP_PROVIDER    -> substrate.tiers.deep.provider
          CHERENKOV_TIER_DEEP_MODEL       -> substrate.tiers.deep.model
          CHERENKOV_FALLBACK_ENABLED      -> (not yet keyed, skip)
          CHERENKOV_FALLBACK_PROVIDER     -> (not yet keyed, skip)
          CHERENKOV_PROFILE               -> profile
          CHERENKOV_MODE                  -> continuity.mode
          CHERENKOV_EGRESS                -> substrate.egress
        """
        env_map = {
            "CHERENKOV_EGRESS": "substrate.egress",
            "CHERENKOV_TIER_SMALL_PROVIDER": "substrate.tiers.small.provider",
            "CHERENKOV_TIER_SMALL_MODEL": "substrate.tiers.small.model",
            "CHERENKOV_TIER_DEEP_PROVIDER": "substrate.tiers.deep.provider",
            "CHERENKOV_TIER_DEEP_MODEL": "substrate.tiers.deep.model",
            "CHERENKOV_PROFILE": "profile",
            "CHERENKOV_MODE": "continuity.mode",
        }
        for env_var, config_key in env_map.items():
            val = os.environ.get(env_var)
            if val is not None and config_key in KNOWN_KEYS:
                self._set(config_key, val, f"env:{env_var}")

    def load_cli_override(self, key: str, value: Any):
        """Layer 5: single CLI flag override."""
        if key in KNOWN_KEYS:
            self._set(key, value, "cli flag")
        else:
            self._errors.append(f"Unknown CLI override key '{key}'.")

    def _set(self, key: str, value: Any, source: str):
        if key not in self._store:
            self._store[key] = []
        self._store[key].append((source, value))

    def get(self, key: str, default: Any = None) -> Any:
        """Get the highest-precedence value for key."""
        if key not in self._store or not self._store[key]:
            return default
        return self._store[key][-1][1]

    def get_with_provenance(self, key: str) -> list[EnvValue]:
        """Get all (source, value) pairs for key, in order low→high precedence."""
        return self._store.get(key, [])

    def all_keys(self) -> set[str]:
        return set(self._store.keys())

    def errors(self) -> list[str]:
        return self._errors

    def to_dict(self) -> dict[str, Any]:
        """Return the effective (highest-precedence) config as a flat dict."""
        return {k: self.get(k) for k in self._store}

    def to_nested_dict(self) -> dict[str, Any]:
        """Return the effective config as a nested dict."""
        return _unflatten(self.to_dict())

    def _find_toml(self) -> str | None:
        """Walk up from CWD looking for cherenkov.toml."""
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            candidate = parent / "cherenkov.toml"
            if candidate.exists():
                return str(candidate)
        return None

    def _parse_toml(self, path: str | Path) -> dict:
        """Parse a TOML file using tomllib (stdlib) or tomli (fallback)."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                raise ConfigError(
                    "tomllib/tomli not available. Install tomli for Python < 3.11: "
                    "pip install tomli"
                )
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to parse {path}: {e}")

    def autodetect_profile(self) -> str:
        """Determine the best profile heuristically.

        Returns the profile name (always one of the 4 known profiles).
        """
        explicit = self.get("profile")
        if explicit and explicit in PROFILE_DEFAULTS:
            return explicit
        return "laptop"

    def autodetect_spec(self) -> list[str]:
        """Autodetect OpenAPI spec files in the project root.

        Searches for common OpenAPI spec filenames.
        Returns paths with forward slashes for cross-platform consistency.
        """
        cwd = Path.cwd()
        patterns = [
            "openapi.yaml", "openapi.yml", "openapi.json",
            "spec.yaml", "spec.yml", "spec.json",
            "*spec*.yaml", "*spec*.yml", "*spec*.json",
            "stub/target_spec.json",
        ]
        found: list[str] = []
        for pattern in patterns:
            matches = sorted(cwd.glob(pattern))
            for m in matches:
                if m.is_file():
                    rel = m.relative_to(cwd)
                    found.append(str(rel).replace("\\", "/"))
        return found


def load_effective_config(
    profile: str | None = None,
    toml_path: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> LayeredConfig:
    """Convenience: load all layers and return the resolved config."""
    cfg = LayeredConfig()
    cfg.load_defaults()

    # Determine profile
    if profile is None:
        env_profile = os.environ.get("CHERENKOV_PROFILE")
        if env_profile:
            profile = env_profile
    if profile:
        cfg.load_profile(profile)

    cfg.load_toml(toml_path)
    cfg.load_env()

    if cli_overrides:
        for k, v in cli_overrides.items():
            cfg.load_cli_override(k, v)

    return cfg
