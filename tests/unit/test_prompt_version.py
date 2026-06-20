"""Tests for cherenkov/evals/prompt_version.py"""

import hashlib
import json
import pytest
from pathlib import Path

from cherenkov.evals.prompt_version import get_prompt_fingerprint, prompt_changed


@pytest.fixture()
def prompts_dir(tmp_path):
    (tmp_path / "generator_system.txt").write_text("You are a test generator.", encoding="utf-8")
    (tmp_path / "graphql_test.j2").write_text("{% for op in ops %}{{ op }}{% endfor %}", encoding="utf-8")
    (tmp_path / "grpc_test.j2").write_text("test grpc {{ method }}", encoding="utf-8")
    # asyncapi_test.j2 and accessibility_test.j2 intentionally absent → "<missing>"
    return tmp_path


class TestGetPromptFingerprint:
    def test_returns_sha256_and_files_keys(self, prompts_dir):
        fp = get_prompt_fingerprint(prompts_dir)
        assert "sha256" in fp
        assert "files" in fp

    def test_sha256_is_16_chars(self, prompts_dir):
        fp = get_prompt_fingerprint(prompts_dir)
        assert len(fp["sha256"]) == 16

    def test_per_file_hashes_are_16_chars(self, prompts_dir):
        fp = get_prompt_fingerprint(prompts_dir)
        for name, h in fp["files"].items():
            assert len(h) == 16, f"{name} hash is not 16 chars"

    def test_missing_file_hashes_to_missing_sentinel(self, prompts_dir):
        expected = hashlib.sha256(b"<missing>").hexdigest()[:16]
        fp = get_prompt_fingerprint(prompts_dir)
        assert fp["files"]["asyncapi_test.j2"] == expected
        assert fp["files"]["accessibility_test.j2"] == expected

    def test_fingerprint_is_stable(self, prompts_dir):
        fp1 = get_prompt_fingerprint(prompts_dir)
        fp2 = get_prompt_fingerprint(prompts_dir)
        assert fp1["sha256"] == fp2["sha256"]
        assert fp1["files"] == fp2["files"]

    def test_fingerprint_changes_on_content_change(self, prompts_dir):
        fp_before = get_prompt_fingerprint(prompts_dir)
        (prompts_dir / "generator_system.txt").write_text("CHANGED", encoding="utf-8")
        fp_after = get_prompt_fingerprint(prompts_dir)
        assert fp_before["sha256"] != fp_after["sha256"]
        assert fp_before["files"]["generator_system.txt"] != fp_after["files"]["generator_system.txt"]

    def test_fingerprint_with_all_missing(self, tmp_path):
        fp = get_prompt_fingerprint(tmp_path)
        expected_sentinel = hashlib.sha256(b"<missing>").hexdigest()[:16]
        for name, h in fp["files"].items():
            assert h == expected_sentinel


class TestPromptChanged:
    def test_no_change_returns_empty_list(self, prompts_dir):
        fp = get_prompt_fingerprint(prompts_dir)
        assert prompt_changed(fp, fp) == []

    def test_detects_single_changed_file(self, prompts_dir):
        baseline = get_prompt_fingerprint(prompts_dir)
        (prompts_dir / "generator_system.txt").write_text("v2", encoding="utf-8")
        current = get_prompt_fingerprint(prompts_dir)
        changed = prompt_changed(baseline, current)
        assert "generator_system.txt" in changed
        assert len(changed) == 1

    def test_detects_multiple_changed_files(self, prompts_dir):
        baseline = get_prompt_fingerprint(prompts_dir)
        (prompts_dir / "generator_system.txt").write_text("v2", encoding="utf-8")
        (prompts_dir / "graphql_test.j2").write_text("v2", encoding="utf-8")
        current = get_prompt_fingerprint(prompts_dir)
        changed = prompt_changed(baseline, current)
        assert set(changed) == {"generator_system.txt", "graphql_test.j2"}

    def test_result_is_sorted(self, prompts_dir):
        baseline = get_prompt_fingerprint(prompts_dir)
        (prompts_dir / "grpc_test.j2").write_text("v2", encoding="utf-8")
        (prompts_dir / "generator_system.txt").write_text("v2", encoding="utf-8")
        current = get_prompt_fingerprint(prompts_dir)
        changed = prompt_changed(baseline, current)
        assert changed == sorted(changed)

    def test_empty_baseline_files_treats_all_as_new(self):
        result = prompt_changed({}, {"files": {"a.txt": "abc"}})
        assert "a.txt" in result

    def test_new_file_in_current_detected(self):
        baseline = {"files": {"a.txt": "aaa"}}
        current = {"files": {"a.txt": "aaa", "b.txt": "bbb"}}
        changed = prompt_changed(baseline, current)
        assert "b.txt" in changed
