"""Unit tests for cherenkov/execution/validate.py — ValidationEngine test scoping.

Regression (#829): stub/generated_tests/ ships intentional demo/golden
fixtures for the catch-the-AI-cheating demos. An unscoped validate run picks
them up and their intentionally-failing assertions drown out real results.
The --tests filter scopes the run without touching the fixtures.
"""
from __future__ import annotations

import pytest

from cherenkov.execution.validate import ValidationEngine


def _make_engine(tmp_path, files):
    engine = ValidationEngine("test_filter")
    engine.tests_dir = str(tmp_path)
    for name in files:
        (tmp_path / name).write_text(
            "import { client } from '../client';\n", encoding="utf-8"
        )
    return engine


def _fake_execute(self, **kwargs):
    return {"passed": True, "trace_path": "", "failure_message": ""}


_FILES = [
    "POST_pet_happy_path.spec.ts",
    "demo_correct.spec.ts",
    "golden_weakened.spec.ts",
]


class TestValidationEngineTestsFilter:
    def test_no_filter_runs_everything(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path, _FILES)
        monkeypatch.setattr(
            "cherenkov.execution.validate.PlaywrightRunner.execute_test", _fake_execute
        )
        results = engine.validate_suite("http://localhost:9999")
        ids = sorted(r["scenario_id"] for r in results["reports"])
        assert ids == ["POST_pet_happy_path", "demo_correct", "golden_weakened"]

    def test_glob_filter_limits_run(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path, _FILES)
        monkeypatch.setattr(
            "cherenkov.execution.validate.PlaywrightRunner.execute_test", _fake_execute
        )
        results = engine.validate_suite("http://localhost:9999", tests_filter="POST_*")
        ids = [r["scenario_id"] for r in results["reports"]]
        assert ids == ["POST_pet_happy_path"]

    def test_substring_filter_limits_run(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path, _FILES)
        monkeypatch.setattr(
            "cherenkov.execution.validate.PlaywrightRunner.execute_test", _fake_execute
        )
        results = engine.validate_suite("http://localhost:9999", tests_filter="pet")
        ids = [r["scenario_id"] for r in results["reports"]]
        assert ids == ["POST_pet_happy_path"]

    def test_filter_no_match_returns_empty(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path, _FILES)
        monkeypatch.setattr(
            "cherenkov.execution.validate.PlaywrightRunner.execute_test", _fake_execute
        )
        results = engine.validate_suite("http://localhost:9999", tests_filter="zzz")
        assert results["status"] == "empty"
        assert results["reports"] == []
        assert "zzz" in results["message"]

    def test_no_tests_dir_with_filter_still_empty(self, tmp_path, monkeypatch):
        engine = _make_engine(tmp_path, [])
        monkeypatch.setattr(
            "cherenkov.execution.validate.PlaywrightRunner.execute_test", _fake_execute
        )
        results = engine.validate_suite("http://localhost:9999", tests_filter="POST_*")
        assert results["status"] == "empty"
