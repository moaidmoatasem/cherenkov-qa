"""tests/unit/test_playbooks.py

Tests for the Playbooks system — the "Skills" analogue in cherenkov-qa,
inspired by RedPlanetHQ/core's reusable, auto-triggering skill rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cherenkov.playbooks.models import Playbook, PlaybookFinding, PlaybookTrigger
from cherenkov.playbooks.matcher import PlaybookMatcher
from cherenkov.playbooks.registry import PlaybookRegistry
from cherenkov.playbooks.runner import PlaybookRunner


# ── Model tests ───────────────────────────────────────────────────────────────

class TestPlaybookTrigger:
    def test_empty_trigger(self):
        t = PlaybookTrigger()
        assert t.is_empty()

    def test_non_empty_trigger(self):
        t = PlaybookTrigger(path_prefix="/auth")
        assert not t.is_empty()

    def test_from_dict(self):
        t = PlaybookTrigger.from_dict(
            {"path_prefix": "/api", "methods": ["get", "post"], "tags": ["auth"]}
        )
        assert t.path_prefix == "/api"
        assert t.methods == ["GET", "POST"]
        assert t.tags == ["auth"]


class TestPlaybook:
    def test_from_dict_minimal(self):
        pb = Playbook.from_dict({"name": "test-pb"})
        assert pb.name == "test-pb"
        assert pb.severity == "warn"
        assert pb.trigger.is_empty()

    def test_from_dict_full(self):
        pb = Playbook.from_dict(
            {
                "name": "auth-strict",
                "description": "Auth enforcement",
                "trigger": {"path_prefix": "/auth", "methods": ["POST"]},
                "required_headers": ["Authorization"],
                "expected_status": [200, 401],
                "forbidden_response_fields": ["password"],
                "severity": "error",
            }
        )
        assert pb.trigger.path_prefix == "/auth"
        assert pb.required_headers == ["Authorization"]
        assert pb.expected_status == [200, 401]
        assert pb.severity == "error"

    def test_to_dict_round_trip(self):
        pb = Playbook.from_dict(
            {"name": "round-trip", "required_headers": ["X-Api-Key"], "severity": "info"}
        )
        d = pb.to_dict()
        assert d["name"] == "round-trip"
        assert d["required_headers"] == ["X-Api-Key"]

    def test_finding_to_dict(self):
        f = PlaybookFinding(
            playbook_name="test", endpoint="/api", method="GET", level="warn", message="bad"
        )
        d = f.to_dict()
        assert d["playbook"] == "test"
        assert d["level"] == "warn"


# ── Registry tests ────────────────────────────────────────────────────────────

class TestPlaybookRegistry:
    def test_empty_registry_when_no_dirs(self):
        registry = PlaybookRegistry(search_dirs=["/nonexistent/path"])
        assert registry.playbooks == []

    def test_load_file(self, tmp_path):
        yaml_file = tmp_path / "my-pb.yaml"
        yaml_file.write_text(
            "name: my-pb\ndescription: test\ntrigger:\n  path_prefix: /v1\nseverity: warn\n"
        )
        registry = PlaybookRegistry(search_dirs=[])
        pb = registry.load_file(yaml_file)
        assert pb is not None
        assert pb.name == "my-pb"
        assert len(registry.playbooks) == 1

    def test_load_file_missing_name(self, tmp_path):
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("description: no name field\n")
        registry = PlaybookRegistry(search_dirs=[])
        result = registry.load_file(yaml_file)
        assert result is None

    def test_load_dir(self, tmp_path):
        (tmp_path / "a.yaml").write_text("name: a\n")
        (tmp_path / "b.yaml").write_text("name: b\n")
        registry = PlaybookRegistry(search_dirs=[tmp_path])
        assert len(registry.playbooks) == 2

    def test_get_by_name(self, tmp_path):
        (tmp_path / "named.yaml").write_text("name: named-pb\nseverity: error\n")
        registry = PlaybookRegistry(search_dirs=[tmp_path])
        pb = registry.get("named-pb")
        assert pb is not None
        assert pb.severity == "error"

    def test_get_missing(self):
        registry = PlaybookRegistry(search_dirs=[])
        assert registry.get("nonexistent") is None

    def test_add(self):
        registry = PlaybookRegistry(search_dirs=[])
        pb = Playbook(name="manual")
        registry.add(pb)
        assert registry.get("manual") is not None

    def test_builtin_playbooks_load(self):
        """Builtin YAML files should load cleanly."""
        builtin_dir = Path(__file__).parent.parent.parent / "cherenkov/playbooks/builtins"
        if not builtin_dir.exists():
            pytest.skip("builtins dir not found")
        registry = PlaybookRegistry(search_dirs=[builtin_dir])
        assert len(registry.playbooks) >= 3
        names = {pb.name for pb in registry.playbooks}
        assert "auth-strict" in names
        assert "health-check" in names
        assert "no-pii-leak" in names


# ── Matcher tests ─────────────────────────────────────────────────────────────

class TestPlaybookMatcher:
    def _make(self, **trigger_kwargs) -> Playbook:
        return Playbook(name="test", trigger=PlaybookTrigger(**trigger_kwargs))

    def test_empty_trigger_matches_everything(self):
        pb = self._make()
        m = PlaybookMatcher([pb])
        assert m.match("/anything", "GET") == [pb]

    def test_path_prefix_match(self):
        pb = self._make(path_prefix="/auth")
        m = PlaybookMatcher([pb])
        assert m.match("/auth/login", "POST") == [pb]
        assert m.match("/users", "GET") == []

    def test_path_contains_match(self):
        pb = self._make(path_contains="health")
        m = PlaybookMatcher([pb])
        assert m.match("/api/health/live", "GET") == [pb]
        assert m.match("/api/users", "GET") == []

    def test_method_filter(self):
        pb = self._make(methods=["POST"])
        m = PlaybookMatcher([pb])
        assert m.match("/api", "POST") == [pb]
        assert m.match("/api", "GET") == []

    def test_tag_filter(self):
        pb = self._make(tags=["auth"])
        m = PlaybookMatcher([pb])
        assert m.match("/api", "GET", tags=["auth", "v2"]) == [pb]
        assert m.match("/api", "GET", tags=["public"]) == []

    def test_multiple_playbooks(self):
        pb_auth = self._make(path_prefix="/auth")
        pb_all = self._make()
        m = PlaybookMatcher([pb_auth, pb_all])
        result = m.match("/auth/login", "POST")
        assert pb_auth in result
        assert pb_all in result

    def test_combined_conditions_must_all_match(self):
        pb = self._make(path_prefix="/auth", methods=["POST"])
        m = PlaybookMatcher([pb])
        assert m.match("/auth/login", "POST") == [pb]
        assert m.match("/auth/login", "GET") == []
        assert m.match("/users", "POST") == []


# ── Runner tests ──────────────────────────────────────────────────────────────

class TestPlaybookRunner:
    def setup_method(self):
        self.runner = PlaybookRunner()

    def _make_pb(self, **kwargs) -> Playbook:
        return Playbook(name="test-runner", **kwargs)

    def test_no_actions_no_findings(self):
        pb = self._make_pb()
        findings = self.runner.run(pb, endpoint="/api", method="GET")
        assert findings == []

    def test_required_header_present(self):
        pb = self._make_pb(required_headers=["Authorization"])
        findings = self.runner.run(
            pb,
            endpoint="/auth",
            method="GET",
            request_headers={"Authorization": "Bearer tok"},
        )
        assert findings == []

    def test_required_header_missing(self):
        pb = self._make_pb(required_headers=["Authorization"], severity="error")
        findings = self.runner.run(pb, endpoint="/auth", method="GET", request_headers={})
        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "Authorization" in findings[0].message

    def test_expected_status_ok(self):
        pb = self._make_pb(expected_status=[200, 201])
        findings = self.runner.run(pb, endpoint="/api", method="POST", status_code=201)
        assert findings == []

    def test_expected_status_mismatch(self):
        pb = self._make_pb(expected_status=[200], severity="warn")
        findings = self.runner.run(pb, endpoint="/api", method="GET", status_code=500)
        assert len(findings) == 1
        assert "500" in findings[0].message
        assert findings[0].level == "warn"

    def test_forbidden_field_absent(self):
        pb = self._make_pb(forbidden_response_fields=["password"])
        findings = self.runner.run(
            pb, endpoint="/users/1", method="GET", response_body={"id": 1, "name": "Alice"}
        )
        assert findings == []

    def test_forbidden_field_present(self):
        pb = self._make_pb(forbidden_response_fields=["password"])
        findings = self.runner.run(
            pb,
            endpoint="/users/1",
            method="GET",
            response_body={"id": 1, "password": "s3cr3t"},
        )
        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_forbidden_nested_field(self):
        pb = self._make_pb(forbidden_response_fields=["user.password"])
        body = {"user": {"id": 1, "password": "oops"}}
        findings = self.runner.run(pb, endpoint="/me", method="GET", response_body=body)
        assert len(findings) == 1

    def test_required_response_field_present(self):
        pb = self._make_pb(required_response_fields=["id", "status"])
        findings = self.runner.run(
            pb,
            endpoint="/health",
            method="GET",
            response_body={"id": 1, "status": "ok"},
        )
        assert findings == []

    def test_required_response_field_missing(self):
        pb = self._make_pb(required_response_fields=["status"], severity="warn")
        findings = self.runner.run(
            pb, endpoint="/health", method="GET", response_body={"message": "up"}
        )
        assert len(findings) == 1
        assert "status" in findings[0].message

    def test_non_dict_body_with_required_fields(self):
        pb = self._make_pb(required_response_fields=["id"])
        findings = self.runner.run(
            pb, endpoint="/items", method="GET", response_body=[1, 2, 3]
        )
        assert len(findings) == 1
        assert "not a dict" in findings[0].message

    def test_multiple_findings_accumulated(self):
        pb = self._make_pb(
            required_headers=["X-Key"],
            expected_status=[200],
            forbidden_response_fields=["secret"],
        )
        findings = self.runner.run(
            pb,
            endpoint="/api",
            method="GET",
            request_headers={},
            status_code=500,
            response_body={"secret": "exposed"},
        )
        assert len(findings) == 3

    def test_header_matching_is_case_insensitive(self):
        pb = self._make_pb(required_headers=["Authorization"])
        findings = self.runner.run(
            pb,
            endpoint="/api",
            method="GET",
            request_headers={"authorization": "Bearer x"},
        )
        assert findings == []
