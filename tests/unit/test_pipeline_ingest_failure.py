"""tests/unit/test_pipeline_ingest_failure.py — pipeline must not vacuously pass.

run_pipeline() previously returned success=True when INGEST failed (e.g. a
missing spec): the FAILED ingest yielded zero endpoints, and the scenarios
phase treats an empty scenario set as success. The mutation-detection test
(tests/test_mutation_validate.py) only masked this by depending on a
mut_spec.json fixture existing. These tests pin the real contract directly,
without a fixture: a genuinely-missing spec must fail the pipeline.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _dev_env_no_ollama():
    with patch.dict(os.environ, {"CHERENKOV_ENV": "development"}), patch(
        "cherenkov.core.settings.CherenkovSettings.detect_ollama_device",
        return_value="cpu",
    ):
        yield


def _run(spec_path: str) -> bool:
    from cherenkov.core.orchestrator import OrchestrationEngine

    return OrchestrationEngine(run_id="ingest-fail-test").run_pipeline(spec_path)


def test_missing_spec_fails_pipeline(tmp_path):
    missing = str(tmp_path / "does_not_exist.json")
    assert _run(missing) is False


def test_missing_spec_is_not_a_vacuous_pass():
    # Absolute path guaranteed not to exist — the pipeline must report failure,
    # not a green "0 scenarios, all passed" result.
    assert _run("/nonexistent/definitely_missing_spec_xyz.json") is False
