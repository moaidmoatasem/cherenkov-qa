"""Tests for cherenkov/core/flags.py"""

import json
import os
import pytest
from unittest.mock import patch

from cherenkov.core.flags import flag, set_flag, reset_flags, all_flags, _DEFAULTS


@pytest.fixture(autouse=True)
def clean_flags():
    reset_flags()
    yield
    reset_flags()


class TestFlagDefaults:
    def test_known_flag_returns_default(self):
        assert flag("EVAL_REGRESSION_CI") is True  # default True
        assert flag("NEW_GRPC_PLANNER") is False   # default False

    def test_unknown_flag_returns_false(self):
        assert flag("TOTALLY_UNKNOWN_FEATURE_XYZ") is False

    def test_case_insensitive(self):
        assert flag("eval_regression_ci") == flag("EVAL_REGRESSION_CI")


class TestSetFlag:
    def test_override_changes_value(self):
        set_flag("NEW_GRPC_PLANNER", True)
        assert flag("NEW_GRPC_PLANNER") is True

    def test_override_is_local(self):
        set_flag("NEW_GRPC_PLANNER", True)
        reset_flags()
        assert flag("NEW_GRPC_PLANNER") is False

    def test_override_false_beats_default_true(self):
        set_flag("EVAL_REGRESSION_CI", False)
        assert flag("EVAL_REGRESSION_CI") is False


class TestEnvVarOverride:
    def test_env_true_overrides_default(self):
        with patch.dict(os.environ, {"CHERENKOV_FLAG_NEW_GRPC_PLANNER": "true"}):
            assert flag("NEW_GRPC_PLANNER") is True

    def test_env_false_overrides_in_process(self):
        set_flag("NEW_GRPC_PLANNER", True)
        with patch.dict(os.environ, {"CHERENKOV_FLAG_NEW_GRPC_PLANNER": "false"}):
            assert flag("NEW_GRPC_PLANNER") is False

    def test_env_var_truthy_values(self):
        for val in ("1", "yes", "on", "true", "True", "TRUE"):
            with patch.dict(os.environ, {"CHERENKOV_FLAG_NEW_GRPC_PLANNER": val}):
                assert flag("NEW_GRPC_PLANNER") is True

    def test_env_var_falsy_values(self):
        for val in ("0", "no", "off", "false", "False"):
            with patch.dict(os.environ, {"CHERENKOV_FLAG_EVAL_REGRESSION_CI": val}):
                assert flag("EVAL_REGRESSION_CI") is False

    def test_env_var_beats_in_process_override(self):
        set_flag("NEW_GRPC_PLANNER", False)
        with patch.dict(os.environ, {"CHERENKOV_FLAG_NEW_GRPC_PLANNER": "true"}):
            assert flag("NEW_GRPC_PLANNER") is True


class TestFlagsFile:
    def test_file_values_used_when_no_env_or_override(self, tmp_path):
        flags_file = tmp_path / "flags.json"
        flags_file.write_text(json.dumps({"new_grpc_planner": True}), encoding="utf-8")
        with patch("cherenkov.core.flags._FLAGS_FILE_PATH", flags_file):
            assert flag("NEW_GRPC_PLANNER") is True

    def test_file_is_hot_reloaded(self, tmp_path):
        flags_file = tmp_path / "flags.json"
        flags_file.write_text(json.dumps({"new_grpc_planner": False}), encoding="utf-8")
        with patch("cherenkov.core.flags._FLAGS_FILE_PATH", flags_file):
            assert flag("NEW_GRPC_PLANNER") is False
            flags_file.write_text(json.dumps({"new_grpc_planner": True}), encoding="utf-8")
            assert flag("NEW_GRPC_PLANNER") is True

    def test_corrupt_file_falls_back_to_default(self, tmp_path):
        flags_file = tmp_path / "flags.json"
        flags_file.write_text("NOT VALID JSON", encoding="utf-8")
        with patch("cherenkov.core.flags._FLAGS_FILE_PATH", flags_file):
            assert flag("NEW_GRPC_PLANNER") is False


class TestAllFlags:
    def test_returns_all_compiled_defaults(self):
        result = all_flags()
        assert set(result.keys()) == set(_DEFAULTS.keys())

    def test_reflects_overrides(self):
        set_flag("NEW_GRPC_PLANNER", True)
        result = all_flags()
        assert result["NEW_GRPC_PLANNER"] is True
