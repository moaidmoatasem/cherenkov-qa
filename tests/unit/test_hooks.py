"""Tests for cherenkov.hooks — hook system (CC-1, ADR-012)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cherenkov.hooks.adapters.subprocess_executor import SubprocessHookExecutor
from cherenkov.hooks.domain.models import (
    FailMode,
    HookAbortError,
    HookConfig,
    HookContext,
    HookEvent,
    HookStatus,
)
from cherenkov.hooks.registry import HookRegistry


# ── SubprocessHookExecutor ────────────────────────────────────────────


class TestSubprocessHookExecutor:
    def setup_method(self) -> None:
        self.executor = SubprocessHookExecutor()

    def _config(
        self,
        event: HookEvent = HookEvent.POST_VALIDATE,
        run: str = "echo hello",
        fail_mode: FailMode = FailMode.WARN,
        timeout: int = 10,
    ) -> HookConfig:
        return HookConfig(event=event, run=run, timeout=timeout, fail_mode=fail_mode)

    def test_successful_command_returns_success(self) -> None:
        config = self._config(run="echo hello")
        result = self.executor.execute(config, HookContext())
        assert result.success is True
        assert result.status == HookStatus.SUCCESS
        assert "hello" in result.stdout

    def test_failing_command_warn_mode_returns_failed(self) -> None:
        config = self._config(run="exit 1", fail_mode=FailMode.WARN)
        result = self.executor.execute(config, HookContext())
        assert result.success is False
        assert result.status == HookStatus.FAILED
        assert result.exit_code == 1

    def test_failing_command_abort_mode_raises(self) -> None:
        config = self._config(run="exit 2", fail_mode=FailMode.ABORT)
        with pytest.raises(HookAbortError) as exc_info:
            self.executor.execute(config, HookContext())
        assert exc_info.value.event == HookEvent.POST_VALIDATE
        assert exc_info.value.result.exit_code == 2

    def test_timeout_warn_mode_returns_timeout(self) -> None:
        config = self._config(run="sleep 10", timeout=1, fail_mode=FailMode.WARN)
        result = self.executor.execute(config, HookContext())
        assert result.status == HookStatus.TIMEOUT
        assert "Timed out" in result.error_message

    def test_timeout_abort_mode_raises(self) -> None:
        config = self._config(run="sleep 10", timeout=1, fail_mode=FailMode.ABORT)
        with pytest.raises(HookAbortError):
            self.executor.execute(config, HookContext())

    def test_template_variable_substitution(self) -> None:
        """Template variables are correctly substituted in the command."""
        config = self._config(run="echo {verdict}")
        ctx = HookContext(verdict="auto_approve")
        result = self.executor.execute(config, ctx)
        assert result.success is True
        assert "auto_approve" in result.stdout

    def test_unknown_template_variable_warn_mode(self) -> None:
        """Unknown template variable produces FAILED (warn mode, no raise)."""
        config = self._config(run="echo {unknown_var}", fail_mode=FailMode.WARN)
        result = self.executor.execute(config, HookContext())
        assert result.status == HookStatus.FAILED
        assert "Unknown template variable" in result.error_message

    def test_unknown_template_variable_abort_mode_raises(self) -> None:
        config = self._config(run="echo {unknown_var}", fail_mode=FailMode.ABORT)
        with pytest.raises(HookAbortError):
            self.executor.execute(config, HookContext())

    def test_duration_is_recorded(self) -> None:
        config = self._config(run="echo timing")
        result = self.executor.execute(config, HookContext())
        assert result.duration_ms >= 0

    def test_all_hook_events_are_valid_enum(self) -> None:
        """Smoke: every HookEvent can be used in a HookConfig."""
        for event in HookEvent:
            cfg = HookConfig(event=event, run="echo ok")
            assert cfg.event == event


# ── HookRegistry ─────────────────────────────────────────────────────


class TestHookRegistry:
    def test_empty_registry(self) -> None:
        reg = HookRegistry.empty()
        assert reg.get(HookEvent.POST_VALIDATE) == []
        assert reg.has(HookEvent.POST_VALIDATE) is False
        assert reg.all_events() == []

    def test_from_config_parses_single_hook(self) -> None:
        raw = {
            "post_validate": {
                "run": "echo {report_path}",
                "timeout": 30,
                "fail_mode": "warn",
            }
        }
        reg = HookRegistry.from_config(raw)
        hooks = reg.get(HookEvent.POST_VALIDATE)
        assert len(hooks) == 1
        assert hooks[0].run == "echo {report_path}"
        assert hooks[0].fail_mode == FailMode.WARN

    def test_from_config_multiple_events(self) -> None:
        raw = {
            "post_validate": {"run": "echo validate"},
            "post_eject": {"run": "echo eject"},
        }
        reg = HookRegistry.from_config(raw)
        assert reg.has(HookEvent.POST_VALIDATE)
        assert reg.has(HookEvent.POST_EJECT)
        assert not reg.has(HookEvent.PRE_GENERATE)

    def test_from_config_list_of_hooks(self) -> None:
        """A list of hook tables is supported for the same event."""
        raw = {
            "post_review": [
                {"run": "echo first"},
                {"run": "echo second", "fail_mode": "abort"},
            ]
        }
        reg = HookRegistry.from_config(raw)
        hooks = reg.get(HookEvent.POST_REVIEW)
        assert len(hooks) == 2
        assert hooks[1].fail_mode == FailMode.ABORT

    def test_from_config_rejects_unknown_event(self) -> None:
        raw = {"nonexistent_event": {"run": "echo oops"}}
        with pytest.raises(ValueError, match="Unknown hook event"):
            HookRegistry.from_config(raw)

    def test_from_config_defaults_timeout_and_fail_mode(self) -> None:
        raw = {"pre_generate": {"run": "echo minimal"}}
        reg = HookRegistry.from_config(raw)
        hook = reg.get(HookEvent.PRE_GENERATE)[0]
        assert hook.timeout == 30
        assert hook.fail_mode == FailMode.WARN

    def test_all_events_returns_configured_events(self) -> None:
        raw = {
            "post_validate": {"run": "echo a"},
            "post_eject": {"run": "echo b"},
        }
        reg = HookRegistry.from_config(raw)
        events = set(reg.all_events())
        assert events == {HookEvent.POST_VALIDATE, HookEvent.POST_EJECT}

    def test_repr_is_informative(self) -> None:
        raw = {"post_validate": {"run": "echo a"}}
        reg = HookRegistry.from_config(raw)
        assert "post_validate" in repr(reg)


# ── HookAbortError ────────────────────────────────────────────────────


class TestHookAbortError:
    def test_abort_error_carries_event_and_result(self) -> None:
        from cherenkov.hooks.domain.models import HookResult
        result = HookResult(
            event=HookEvent.POST_VALIDATE,
            status=HookStatus.FAILED,
            command="exit 1",
            exit_code=1,
        )
        err = HookAbortError(HookEvent.POST_VALIDATE, result)
        assert err.event == HookEvent.POST_VALIDATE
        assert err.result is result
        assert "post_validate" in str(err)
