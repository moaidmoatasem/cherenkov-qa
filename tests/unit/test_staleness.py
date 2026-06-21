"""Tests for cherenkov/core/staleness.py and cherenkov/cli/commands/check_stale.py"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cherenkov.core.staleness import TestManifest, _file_sha256


# ── _file_sha256 ──────────────────────────────────────────────────────────────

class TestFileHash:
    def test_hash_is_stable(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("hello")
        assert _file_sha256(str(f)) == _file_sha256(str(f))

    def test_hash_differs_on_content_change(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_text("v1")
        h1 = _file_sha256(str(f))
        f.write_text("v2")
        h2 = _file_sha256(str(f))
        assert h1 != h2

    def test_missing_file_returns_empty(self, tmp_path):
        assert _file_sha256(str(tmp_path / "missing.txt")) == ""


# ── TestManifest.record / check ───────────────────────────────────────────────

class TestManifestRecord:
    def test_record_creates_manifest(self, tmp_path):
        spec = tmp_path / "api.yaml"
        spec.write_text("openapi: 3.0.3")
        t1 = tmp_path / "test1.spec.ts"
        t1.write_text("test")

        m = TestManifest(manifest_path=tmp_path / ".cherenkov/manifest.json")
        m.record(str(spec), [str(t1)])

        assert (tmp_path / ".cherenkov/manifest.json").exists()

    def test_record_stores_correct_hash(self, tmp_path):
        spec = tmp_path / "api.yaml"
        spec.write_text("openapi: 3.0.3")
        m = TestManifest(manifest_path=tmp_path / "manifest.json")
        m.record(str(spec), [])

        data = json.loads((tmp_path / "manifest.json").read_text())
        assert data["spec_hash"] == _file_sha256(str(spec))

    def test_record_stores_test_list(self, tmp_path):
        spec = tmp_path / "api.yaml"
        spec.write_text("x")
        tests = [str(tmp_path / f"t{i}.spec.ts") for i in range(3)]
        m = TestManifest(manifest_path=tmp_path / "manifest.json")
        m.record(str(spec), tests)

        data = json.loads((tmp_path / "manifest.json").read_text())
        assert set(data["tests"]) == set(tests)


class TestManifestCheck:
    def _setup(self, tmp_path, spec_content="openapi: 3.0.3"):
        spec = tmp_path / "api.yaml"
        spec.write_text(spec_content)
        t1 = tmp_path / "test1.spec.ts"
        t1.write_text("test")
        manifest = tmp_path / "manifest.json"
        m = TestManifest(manifest_path=manifest)
        m.record(str(spec), [str(t1)])
        return m, spec, t1

    def test_fresh_manifest_is_not_stale(self, tmp_path):
        m, _, _ = self._setup(tmp_path)
        report = m.check()
        assert not report.stale
        assert "up to date" in report.message.lower()

    def test_spec_change_marks_stale(self, tmp_path):
        m, spec, _ = self._setup(tmp_path)
        spec.write_text("openapi: 3.0.3\n# changed")
        report = m.check()
        assert report.stale
        assert "changed" in report.message.lower()

    def test_missing_test_file_marks_stale(self, tmp_path):
        m, _, t1 = self._setup(tmp_path)
        t1.unlink()
        report = m.check()
        assert report.stale
        assert str(t1) in report.missing_files

    def test_no_manifest_is_stale(self, tmp_path):
        m = TestManifest(manifest_path=tmp_path / "nonexistent.json")
        report = m.check()
        assert report.stale

    def test_stale_files_listed_on_hash_change(self, tmp_path):
        m, spec, t1 = self._setup(tmp_path)
        spec.write_text("changed content")
        report = m.check()
        assert str(t1) in report.stale_files

    def test_hash_values_in_report(self, tmp_path):
        m, spec, _ = self._setup(tmp_path)
        original_hash = _file_sha256(str(spec))
        spec.write_text("v2")
        report = m.check()
        assert report.recorded_hash == original_hash
        assert report.current_hash == _file_sha256(str(spec))


# ── check-stale CLI command ───────────────────────────────────────────────────

class TestCheckStaleCmd:
    def _make_manifest(self, tmp_path, spec_content="openapi: 3.0.3"):
        spec = tmp_path / "api.yaml"
        spec.write_text(spec_content)
        t1 = tmp_path / "test1.spec.ts"
        t1.write_text("code")
        manifest = tmp_path / "manifest.json"
        TestManifest(manifest_path=manifest).record(str(spec), [str(t1)])
        return spec, manifest

    def test_up_to_date_exit_zero(self, tmp_path):
        _, manifest = self._make_manifest(tmp_path)
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, ["--manifest", str(manifest)])
        assert r.exit_code == 0
        assert "UP TO DATE" in r.output

    def test_stale_spec_shows_stale(self, tmp_path):
        spec, manifest = self._make_manifest(tmp_path)
        spec.write_text("changed")
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, ["--manifest", str(manifest)])
        assert "STALE" in r.output

    def test_fail_on_stale_exits_1(self, tmp_path):
        spec, manifest = self._make_manifest(tmp_path)
        spec.write_text("changed")
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, [
            "--manifest", str(manifest), "--fail-on-stale",
        ])
        assert r.exit_code == 1

    def test_json_output(self, tmp_path):
        _, manifest = self._make_manifest(tmp_path)
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, ["--manifest", str(manifest), "--json"])
        data = json.loads(r.output)
        assert "stale" in data
        assert data["stale"] is False

    def test_no_manifest_exits_1_with_fail_on_stale(self, tmp_path):
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, [
            "--manifest", str(tmp_path / "nonexistent.json"),
            "--fail-on-stale",
        ])
        assert r.exit_code == 1

    def test_spec_override_detects_change(self, tmp_path):
        spec, manifest = self._make_manifest(tmp_path)
        spec.write_text("v2 content here")
        from cherenkov.cli.commands.check_stale import check_stale_cmd

        r = CliRunner().invoke(check_stale_cmd, [
            "--manifest", str(manifest),
            "--spec", str(spec),
        ])
        assert "STALE" in r.output
