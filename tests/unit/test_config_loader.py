"""Unit tests for cherenkov/core/config_loader.py — LayeredConfig and load_effective_config."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cherenkov.core.config_loader import (
    LayeredConfig,
    BUILTIN_DEFAULTS,
    PROFILE_DEFAULTS,
    KNOWN_KEYS,
    load_effective_config,
    _flatten,
    _unflatten,
)


class TestFlatten:
    def test_flat_passthrough(self):
        assert _flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_nested_flattens(self):
        assert _flatten({"a": {"b": {"c": 3}}}) == {"a.b.c": 3}

    def test_mixed(self):
        result = _flatten({"x": 1, "y": {"z": 2}})
        assert result == {"x": 1, "y.z": 2}


class TestUnflatten:
    def test_roundtrip(self):
        flat = {"a.b.c": 1, "a.b.d": 2, "x": 3}
        nested = _unflatten(flat)
        assert nested == {"a": {"b": {"c": 1, "d": 2}}, "x": 3}

    def test_single_key(self):
        assert _unflatten({"foo": "bar"}) == {"foo": "bar"}


class TestLayeredConfigDefaults:
    def test_load_defaults_sets_profile(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        assert cfg.get("profile") == "laptop"

    def test_all_builtin_keys_present(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        for key in BUILTIN_DEFAULTS:
            assert cfg.get(key) is not None or cfg.get(key) == BUILTIN_DEFAULTS[key]

    def test_get_missing_key_returns_default(self):
        cfg = LayeredConfig()
        assert cfg.get("nonexistent.key", "fallback") == "fallback"

    def test_no_errors_on_clean_load(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        assert cfg.errors() == []


class TestLayeredConfigProfile:
    def test_profile_overrides_defaults(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("ci")
        assert cfg.get("divergence.adversarial_self_play") is False

    def test_unknown_profile_ignored(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("nonexistent-profile")
        assert cfg.get("profile") == "laptop"  # builtin default survives

    def test_all_four_profiles_valid(self):
        for profile in ("laptop", "ci", "enterprise-vpc", "frontier-cloud"):
            cfg = LayeredConfig()
            cfg.load_defaults()
            cfg.load_profile(profile)
            assert cfg.errors() == []

    def test_frontier_cloud_allows_openai(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("frontier-cloud")
        assert cfg.get("substrate.tiers.deep.provider") == "openai"

    def test_enterprise_vpc_egress_none(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("enterprise-vpc")
        assert cfg.get("substrate.egress") == "none"


class TestLayeredConfigEnv:
    def test_env_overrides_profile(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("laptop")
        with patch.dict(os.environ, {"CHERENKOV_EGRESS": "external"}):
            cfg.load_env()
        assert cfg.get("substrate.egress") == "external"

    def test_env_profile_key(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        with patch.dict(os.environ, {"CHERENKOV_PROFILE": "ci"}):
            cfg.load_env()
        assert cfg.get("profile") == "ci"

    def test_unknown_env_var_ignored(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        with patch.dict(os.environ, {"CHERENKOV_TOTALLY_UNKNOWN": "val"}):
            cfg.load_env()
        assert cfg.errors() == []

    def test_mode_env_var(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        with patch.dict(os.environ, {"CHERENKOV_MODE": "daemon"}):
            cfg.load_env()
        assert cfg.get("continuity.mode") == "daemon"


class TestLayeredConfigCLI:
    def test_cli_overrides_env(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        with patch.dict(os.environ, {"CHERENKOV_EGRESS": "internal"}):
            cfg.load_env()
        cfg.load_cli_override("substrate.egress", "none")
        assert cfg.get("substrate.egress") == "none"

    def test_unknown_cli_key_logged_as_error(self):
        cfg = LayeredConfig()
        cfg.load_cli_override("totally.unknown.key", "val")
        assert any("unknown" in e.lower() for e in cfg.errors())


class TestLayeredConfigToml:
    def test_valid_toml_loaded(self):
        toml_content = b'[substrate]\negress = "external"\n'
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            path = f.name
        cfg = LayeredConfig()
        cfg.load_defaults()
        result = cfg.load_toml(path)
        assert result is True
        assert cfg.get("substrate.egress") == "external"

    def test_unknown_key_in_toml_adds_error(self):
        toml_content = b'[foo]\nbar = "baz"\n'
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            path = f.name
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_toml(path)
        assert any("Unknown config key" in e for e in cfg.errors())

    def test_missing_toml_returns_false(self):
        cfg = LayeredConfig()
        result = cfg.load_toml("/nonexistent/cherenkov.toml")
        assert result is False


class TestLayeredConfigProvenance:
    def test_provenance_tracks_all_sources(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("ci")
        provenance = cfg.get_with_provenance("substrate.egress")
        sources = [s for s, _ in provenance]
        assert "built-in defaults" in sources
        assert any("profile" in s for s in sources)

    def test_last_wins(self):
        cfg = LayeredConfig()
        cfg.load_defaults()           # sets substrate.egress = "internal"
        cfg.load_profile("frontier-cloud")  # may change it
        cfg.load_cli_override("substrate.egress", "none")
        assert cfg.get("substrate.egress") == "none"


class TestLayeredConfigToDict:
    def test_to_dict_flat(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "substrate.egress" in d

    def test_to_nested_dict(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        nested = cfg.to_nested_dict()
        assert "substrate" in nested
        assert "egress" in nested["substrate"]


class TestAutodetect:
    def test_autodetect_profile_returns_known(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        profile = cfg.autodetect_profile()
        assert profile in PROFILE_DEFAULTS

    def test_autodetect_profile_respects_set_value(self):
        cfg = LayeredConfig()
        cfg.load_defaults()
        cfg.load_profile("ci")
        cfg._set("profile", "ci", "test")
        assert cfg.autodetect_profile() == "ci"


class TestLoadEffectiveConfig:
    def test_returns_layered_config(self):
        result = load_effective_config()
        assert isinstance(result, LayeredConfig)

    def test_profile_kwarg_applied(self):
        # Pass toml_path="/dev/null" (nonexistent) to skip auto-discovery of
        # the project cherenkov.toml which would override profile settings.
        cfg = load_effective_config(profile="ci", toml_path="/nonexistent.toml")
        # ci profile sets divergence.space to ["D1", "D2"] (smaller set)
        assert cfg.get("divergence.space") == ["D1", "D2"]

    def test_cli_overrides_applied(self):
        cfg = load_effective_config(
            cli_overrides={"substrate.egress": "none"},
            toml_path="/nonexistent.toml",
        )
        assert cfg.get("substrate.egress") == "none"

    def test_env_profile_applied(self):
        # Pass a nonexistent toml_path to prevent loading the project cherenkov.toml.
        with patch.dict(os.environ, {"CHERENKOV_PROFILE": "enterprise-vpc"}, clear=False):
            cfg = load_effective_config(toml_path="/nonexistent.toml")
        # enterprise-vpc profile includes k6 emitter
        assert "k6" in cfg.get("artifacts.emitters")
