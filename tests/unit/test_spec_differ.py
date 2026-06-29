"""Unit tests for cherenkov/diff/spec_differ.py and `cherenkov diff` CLI command."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cherenkov.diff.spec_differ import (
    ChangeType,
    SpecChange,
    SpecDiffer,
    SpecDiffReport,
    print_diff_report,
)
from cherenkov.cli.commands.simple import diff_cmd


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_json(path: Path, data: dict) -> str:
    path.write_text(json.dumps(data))
    return str(path)


def _write_yaml(path: Path, data: dict) -> str:
    import yaml
    path.write_text(yaml.dump(data))
    return str(path)


def _spec(paths: dict) -> dict:
    return {"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": paths}


def _op(params: list | None = None, responses: dict | None = None) -> dict:
    return {
        "parameters": params or [],
        "responses": responses or {"200": {"description": "OK"}},
    }


def _param(name: str, required: bool = False, type_: str = "string") -> dict:
    return {"name": name, "in": "query", "required": required, "schema": {"type": type_}}


# ── SpecDiffReport ─────────────────────────────────────────────────────────────

class TestSpecDiffReport:
    def test_has_breaking_changes_false_when_empty(self) -> None:
        r = SpecDiffReport()
        assert not r.has_breaking_changes

    def test_has_breaking_changes_true(self) -> None:
        r = SpecDiffReport()
        r.breaking.append(
            SpecChange(ChangeType.REMOVED_ENDPOINT, True, "/x", "GET", "removed")
        )
        assert r.has_breaking_changes

    def test_to_dict_structure(self) -> None:
        r = SpecDiffReport()
        d = r.to_dict()
        assert d["has_breaking_changes"] is False
        assert d["summary"]["breaking_count"] == 0
        assert "breaking" in d and "additive" in d and "informational" in d

    def test_to_dict_counts(self) -> None:
        r = SpecDiffReport()
        r.breaking.append(SpecChange(ChangeType.REMOVED_ENDPOINT, True, "/x", "GET", "d"))
        r.additive.append(SpecChange(ChangeType.ADDED_ENDPOINT, False, "/y", "POST", "d"))
        d = r.to_dict()
        assert d["summary"]["breaking_count"] == 1
        assert d["summary"]["additive_count"] == 1


# ── SpecDiffer ─────────────────────────────────────────────────────────────────

class TestSpecDifferRemovedEndpoints:
    def test_removed_endpoint_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({"/pets": {"get": _op()}}))
        after = _write_json(tmp_path / "a.json", _spec({}))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any(c.change_type == ChangeType.REMOVED_ENDPOINT for c in report.breaking)
        assert any(c.endpoint == "/pets" for c in report.breaking)

    def test_removed_method_from_existing_path_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(), "post": _op()}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op()}
        }))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any(c.method == "POST" and c.endpoint == "/pets" for c in report.breaking)

    def test_no_change_is_clean(self, tmp_path: Path) -> None:
        spec = _spec({"/health": {"get": _op()}})
        before = _write_json(tmp_path / "b.json", spec)
        after = _write_json(tmp_path / "a.json", spec)
        report = SpecDiffer().diff(before, after)
        assert not report.has_breaking_changes
        assert not report.breaking and not report.additive and not report.informational


class TestSpecDifferAddedEndpoints:
    def test_added_endpoint_is_additive(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({}))
        after = _write_json(tmp_path / "a.json", _spec({"/v2/pets": {"get": _op()}}))
        report = SpecDiffer().diff(before, after)
        assert not report.has_breaking_changes
        assert any(c.change_type == ChangeType.ADDED_ENDPOINT for c in report.additive)


class TestSpecDifferParameters:
    def test_removed_required_param_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(params=[_param("limit", required=True)])}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op(params=[])}
        }))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any(c.change_type == ChangeType.REMOVED_REQUIRED_PARAM for c in report.breaking)

    def test_removed_optional_param_is_additive(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(params=[_param("verbose", required=False)])}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op(params=[])}
        }))
        report = SpecDiffer().diff(before, after)
        assert not report.has_breaking_changes
        assert any(c.change_type == ChangeType.ADDED_OPTIONAL_PARAM for c in report.additive)

    def test_new_required_param_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(params=[])}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op(params=[_param("api_key", required=True)])}
        }))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any("api_key" in c.detail for c in report.breaking)

    def test_param_type_change_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(params=[_param("limit", type_="string")])}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op(params=[_param("limit", type_="integer")])}
        }))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any(c.change_type == ChangeType.CHANGED_PARAM_TYPE for c in report.breaking)
        breaking = next(c for c in report.breaking if c.change_type == ChangeType.CHANGED_PARAM_TYPE)
        assert breaking.before == "string"
        assert breaking.after == "integer"

    def test_unchanged_params_emit_nothing(self, tmp_path: Path) -> None:
        spec = _spec({"/pets": {"get": _op(params=[_param("limit", type_="integer")])}})
        before = _write_json(tmp_path / "b.json", spec)
        after = _write_json(tmp_path / "a.json", spec)
        report = SpecDiffer().diff(before, after)
        assert not report.breaking and not report.additive


class TestSpecDifferResponseCodes:
    def test_removed_response_code_is_breaking(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({
            "/pets": {"get": _op(responses={"200": {"description": "OK"}, "404": {"description": "NF"}})}
        }))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op(responses={"200": {"description": "OK"}})}
        }))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes
        assert any(c.change_type == ChangeType.REMOVED_RESPONSE_CODE for c in report.breaking)
        assert any("404" in c.detail for c in report.breaking)


class TestSpecDifferYamlLoading:
    def test_loads_yaml_spec(self, tmp_path: Path) -> None:
        before = _write_yaml(tmp_path / "b.yaml", _spec({"/a": {"get": _op()}}))
        after = _write_yaml(tmp_path / "a.yaml", _spec({"/a": {"get": _op()}}))
        report = SpecDiffer().diff(before, after)
        assert not report.has_breaking_changes

    def test_cross_format_json_yaml(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({"/x": {"delete": _op()}}))
        after = _write_yaml(tmp_path / "a.yaml", _spec({}))
        report = SpecDiffer().diff(before, after)
        assert report.has_breaking_changes


# ── print_diff_report ──────────────────────────────────────────────────────────

class TestPrintDiffReport:
    def test_no_changes_message(self, capsys) -> None:
        print_diff_report(SpecDiffReport(), fmt="text")
        assert "No changes" in capsys.readouterr().out

    def test_json_format(self, capsys) -> None:
        r = SpecDiffReport()
        r.breaking.append(SpecChange(ChangeType.REMOVED_ENDPOINT, True, "/x", "GET", "removed"))
        print_diff_report(r, fmt="json")
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["has_breaking_changes"] is True
        assert data["summary"]["breaking_count"] == 1

    def test_text_format_shows_breaking(self, capsys) -> None:
        r = SpecDiffReport()
        r.breaking.append(SpecChange(ChangeType.REMOVED_ENDPOINT, True, "/pets", "GET", "removed"))
        print_diff_report(r, fmt="text")
        out = capsys.readouterr().out
        assert "BREAKING" in out
        assert "/pets" in out


# ── diff CLI command ───────────────────────────────────────────────────────────

class TestDiffCmd:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(diff_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--before" in result.output
        assert "--after" in result.output

    def test_identical_specs_exit_0(self, tmp_path: Path) -> None:
        spec = _spec({"/pets": {"get": _op()}})
        before = _write_json(tmp_path / "b.json", spec)
        after = _write_json(tmp_path / "a.json", spec)
        runner = CliRunner()
        result = runner.invoke(diff_cmd, ["--before", before, "--after", after])
        assert result.exit_code == 0

    def test_breaking_change_exits_1(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({"/pets": {"get": _op()}}))
        after = _write_json(tmp_path / "a.json", _spec({}))
        runner = CliRunner()
        result = runner.invoke(diff_cmd, ["--before", before, "--after", after])
        assert result.exit_code == 1

    def test_additive_only_exits_0(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({"/pets": {"get": _op()}}))
        after = _write_json(tmp_path / "a.json", _spec({
            "/pets": {"get": _op()},
            "/v2/pets": {"get": _op()},
        }))
        runner = CliRunner()
        result = runner.invoke(diff_cmd, ["--before", before, "--after", after])
        assert result.exit_code == 0

    def test_json_format_flag(self, tmp_path: Path) -> None:
        before = _write_json(tmp_path / "b.json", _spec({"/x": {"delete": _op()}}))
        after = _write_json(tmp_path / "a.json", _spec({}))
        runner = CliRunner()
        result = runner.invoke(diff_cmd, ["--before", before, "--after", after, "--format", "json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["has_breaking_changes"] is True
