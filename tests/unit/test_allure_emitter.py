"""
Unit tests for cherenkov/execution/emitters/allure.py

Tests verify:
- Allure JSON result files are written to the specified output directory.
- Each passing scenario produces status="passed" with no statusDetails.
- Each failing scenario produces status="failed" with a populated statusDetails.
- File names follow the {uuid}-result.json pattern.
- Required Allure 2 JSON fields are present.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from cherenkov.execution.emitters.allure import emit_allure


_RESULTS_MIXED = {
    "run_id": "test-run-001",
    "reports": [
        {
            "scenario_id": "sc-pass-1",
            "method": "GET",
            "endpoint": "/health",
            "passed": True,
            "error": "",
        },
        {
            "scenario_id": "sc-fail-2",
            "method": "POST",
            "endpoint": "/payments",
            "passed": False,
            "error": "Expected 201, got 400",
        },
    ],
}

_RESULTS_ALL_PASS = {
    "run_id": "test-run-002",
    "reports": [
        {"scenario_id": "sc-ok-1", "method": "GET", "endpoint": "/items", "passed": True, "error": ""},
        {"scenario_id": "sc-ok-2", "method": "GET", "endpoint": "/items/1", "passed": True, "error": ""},
    ],
}

_RESULTS_EMPTY = {
    "run_id": "test-run-003",
    "reports": [],
}


def _load_results(output_dir: str) -> list[dict]:
    """Read all *-result.json files from output_dir and parse them."""
    data = []
    for fname in os.listdir(output_dir):
        if fname.endswith("-result.json"):
            with open(os.path.join(output_dir, fname), encoding="utf-8") as fh:
                data.append(json.load(fh))
    return data


class TestEmitAllure:

    def test_writes_one_file_per_scenario(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = emit_allure(_RESULTS_MIXED, output_dir=tmpdir)
            assert len(paths) == 2
            # Files actually exist on disk
            for p in paths:
                assert os.path.isfile(p), f"Expected file {p} to exist"

    def test_file_name_pattern(self):
        """File names must match {uuid}-result.json"""
        import re
        pattern = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-result\.json"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_MIXED, output_dir=tmpdir)
            for fname in os.listdir(tmpdir):
                assert pattern.match(fname), f"Bad file name: {fname}"

    def test_passed_scenario_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_ALL_PASS, output_dir=tmpdir)
            for item in _load_results(tmpdir):
                assert item["status"] == "passed"
                # statusDetails must be empty for passes
                assert item["statusDetails"] == {}

    def test_failed_scenario_status_and_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_MIXED, output_dir=tmpdir)
            results = _load_results(tmpdir)
            failed = [r for r in results if r["status"] == "failed"]
            passed = [r for r in results if r["status"] == "passed"]
            assert len(failed) == 1
            assert len(passed) == 1
            # statusDetails must include the error message
            assert "Expected 201, got 400" in failed[0]["statusDetails"]["message"]

    def test_required_allure_fields_present(self):
        required_keys = {"uuid", "historyId", "testCaseId", "fullName", "name",
                         "status", "statusDetails", "stage", "labels",
                         "parameters", "steps", "attachments", "start", "stop"}
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_MIXED, output_dir=tmpdir)
            for item in _load_results(tmpdir):
                missing = required_keys - set(item.keys())
                assert not missing, f"Missing Allure fields: {missing}"

    def test_labels_contain_suite_and_tag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_MIXED, output_dir=tmpdir)
            for item in _load_results(tmpdir):
                label_names = [l["name"] for l in item["labels"]]
                assert "suite" in label_names
                assert "tag" in label_names

    def test_spec_path_adds_feature_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            emit_allure(_RESULTS_MIXED, output_dir=tmpdir, spec_path="openapi.yaml")
            for item in _load_results(tmpdir):
                feature_labels = [l["value"] for l in item["labels"] if l["name"] == "feature"]
                assert "openapi.yaml" in feature_labels

    def test_empty_reports_writes_no_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = emit_allure(_RESULTS_EMPTY, output_dir=tmpdir)
            assert paths == []
            assert os.listdir(tmpdir) == []

    def test_creates_output_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as base:
            new_dir = os.path.join(base, "nested", "allure-results")
            paths = emit_allure(_RESULTS_ALL_PASS, output_dir=new_dir)
            assert os.path.isdir(new_dir)
            assert len(paths) == 2
