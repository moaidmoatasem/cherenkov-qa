"""Tests for cherenkov/truth/spec_validator.py"""

import json
import textwrap
import pytest
from pathlib import Path

from cherenkov.truth.spec_validator import validate_spec, Severity, SpecIssue


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


MINIMAL_OPENAPI = """\
    openapi: "3.0.3"
    info:
      title: Test API
      version: "1.0"
    paths:
      /health:
        get:
          operationId: getHealth
          responses:
            "200":
              description: ok
"""

SWAGGER2 = """\
    swagger: "2.0"
    info:
      title: Test
      version: "1.0"
    paths:
      /ping:
        get:
          responses:
            200:
              description: pong
"""

WITH_DANGLING_REF = """\
    openapi: "3.0.3"
    info:
      title: Broken
      version: "1"
    paths:
      /items:
        get:
          responses:
            "200":
              description: items
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Item"
"""

WITH_VALID_REF = """\
    openapi: "3.0.3"
    info:
      title: OK
      version: "1"
    paths:
      /items:
        get:
          responses:
            "200":
              content:
                application/json:
                  schema:
                    $ref: "#/components/schemas/Item"
    components:
      schemas:
        Item:
          type: object
          properties:
            id:
              type: string
"""


# ── Happy path ────────────────────────────────────────────────────────────────

class TestValidSpecPasses:
    def test_minimal_openapi(self, tmp_path):
        path = _write(tmp_path, "api.yaml", MINIMAL_OPENAPI)
        result = validate_spec(path)
        assert result.ok
        assert result.errors == []

    def test_swagger_v2(self, tmp_path):
        path = _write(tmp_path, "swagger.yaml", SWAGGER2)
        result = validate_spec(path)
        assert result.ok

    def test_json_format(self, tmp_path):
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {"/x": {"get": {"responses": {"200": {"description": "ok"}}}}},
        }
        path = str(tmp_path / "api.json")
        Path(path).write_text(json.dumps(spec), encoding="utf-8")
        result = validate_spec(path)
        assert result.ok

    def test_spec_dict_returned(self, tmp_path):
        path = _write(tmp_path, "api.yaml", MINIMAL_OPENAPI)
        result = validate_spec(path)
        assert result.spec is not None
        assert "paths" in result.spec

    def test_valid_ref_resolves(self, tmp_path):
        path = _write(tmp_path, "refs.yaml", WITH_VALID_REF)
        result = validate_spec(path)
        assert result.ok
        assert not any(i.code == "SPEC_PARSE_ERROR" and "Dangling" in i.message
                       for i in result.issues)


# ── File not found ────────────────────────────────────────────────────────────

class TestFileNotFound:
    def test_missing_file_returns_error(self, tmp_path):
        result = validate_spec(str(tmp_path / "nonexistent.yaml"))
        assert not result.ok
        assert any(i.code == "SPEC_NOT_FOUND" for i in result.errors)

    def test_missing_file_no_spec_in_result(self, tmp_path):
        result = validate_spec(str(tmp_path / "missing.yaml"))
        assert result.spec is None


# ── Parse errors ─────────────────────────────────────────────────────────────

class TestParseErrors:
    def test_invalid_yaml(self, tmp_path):
        path = _write(tmp_path, "bad.yaml", ":\n  - broken: [unclosed")
        result = validate_spec(path)
        assert not result.ok
        assert any(i.code == "SPEC_PARSE_ERROR" for i in result.errors)

    def test_invalid_json(self, tmp_path):
        path = str(tmp_path / "bad.json")
        Path(path).write_text("{broken json", encoding="utf-8")
        result = validate_spec(path)
        assert not result.ok

    def test_yaml_scalar_root(self, tmp_path):
        path = _write(tmp_path, "scalar.yaml", "just a string\n")
        result = validate_spec(path)
        assert not result.ok
        assert any("root must be" in i.message.lower() for i in result.errors)

    def test_list_root_rejected(self, tmp_path):
        path = _write(tmp_path, "list.yaml", "- item1\n- item2\n")
        result = validate_spec(path)
        assert not result.ok


# ── Required field checks ─────────────────────────────────────────────────────

class TestRequiredFields:
    def test_missing_openapi_field(self, tmp_path):
        spec = {"info": {"title": "T", "version": "1"}, "paths": {"/x": {"get": {}}}}
        path = str(tmp_path / "no_openapi.yaml")
        import yaml
        Path(path).write_text(yaml.dump(spec), encoding="utf-8")
        result = validate_spec(path)
        assert not result.ok
        assert any("openapi" in i.message.lower() or "swagger" in i.message.lower()
                   for i in result.errors)

    def test_missing_info(self, tmp_path):
        content = "openapi: '3.0.3'\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: ok\n"
        path = _write(tmp_path, "no_info.yaml", content)
        result = validate_spec(path)
        assert not result.ok
        assert any("info" in i.message.lower() for i in result.errors)

    def test_missing_paths(self, tmp_path):
        content = "openapi: '3.0.3'\ninfo:\n  title: T\n  version: '1'\n"
        path = _write(tmp_path, "no_paths.yaml", content)
        result = validate_spec(path)
        assert not result.ok
        assert any("paths" in i.message.lower() for i in result.errors)

    def test_empty_paths(self, tmp_path):
        content = "openapi: '3.0.3'\ninfo:\n  title: T\n  version: '1'\npaths: {}\n"
        path = _write(tmp_path, "empty_paths.yaml", content)
        result = validate_spec(path)
        assert not result.ok
        assert any("empty" in i.message.lower() for i in result.errors)


# ── Warnings ──────────────────────────────────────────────────────────────────

class TestWarnings:
    def test_unknown_version_is_warning(self, tmp_path):
        content = "openapi: '9.9.9'\ninfo:\n  title: T\n  version: '1'\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: ok\n"
        path = _write(tmp_path, "future.yaml", content)
        result = validate_spec(path)
        # ok=True (warnings don't block by default)
        assert result.ok
        assert any(i.severity == Severity.WARNING for i in result.issues)

    def test_fatal_on_warnings_option(self, tmp_path):
        content = "openapi: '9.9.9'\ninfo:\n  title: T\n  version: '1'\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: ok\n"
        path = _write(tmp_path, "future2.yaml", content)
        result = validate_spec(path, fatal_on_warnings=True)
        assert not result.ok

    def test_path_without_ops_is_warning(self, tmp_path):
        content = textwrap.dedent("""\
            openapi: '3.0.3'
            info:
              title: T
              version: '1'
            paths:
              /x:
                parameters:
                  - name: id
                    in: query
                    schema:
                      type: string
              /y:
                get:
                  responses:
                    '200':
                      description: ok
        """)
        path = _write(tmp_path, "no_ops.yaml", content)
        result = validate_spec(path)
        assert result.ok  # not fatal
        assert any("no HTTP operations" in i.message for i in result.warnings)


# ── Dangling $ref ─────────────────────────────────────────────────────────────

class TestDanglingRefs:
    def test_dangling_ref_is_error(self, tmp_path):
        path = _write(tmp_path, "dangling.yaml", WITH_DANGLING_REF)
        result = validate_spec(path)
        assert not result.ok
        assert any("Dangling" in i.message for i in result.errors)

    def test_dangling_ref_shows_path(self, tmp_path):
        path = _write(tmp_path, "dangling2.yaml", WITH_DANGLING_REF)
        result = validate_spec(path)
        ref_issues = [i for i in result.errors if "Dangling" in i.message]
        assert any("#/components/schemas/Item" in i.location for i in ref_issues)

    def test_external_ref_skipped(self, tmp_path):
        content = textwrap.dedent("""\
            openapi: '3.0.3'
            info:
              title: T
              version: '1'
            paths:
              /x:
                get:
                  responses:
                    '200':
                      content:
                        application/json:
                          schema:
                            $ref: 'https://example.com/schema.json'
        """)
        path = _write(tmp_path, "ext_ref.yaml", content)
        result = validate_spec(path)
        # External refs are not checked — should pass
        assert result.ok


# ── CLI integration ───────────────────────────────────────────────────────────

class TestValidateCmdWithSpecValidator:
    def test_bad_spec_causes_exit(self, tmp_path):
        from click.testing import CliRunner
        from cherenkov.cli.commands.validate import validate_cmd

        bad = _write(tmp_path, "bad.yaml", "not an openapi spec\n")
        runner = CliRunner()
        result = runner.invoke(validate_cmd, [
            "--target", "http://localhost:9999",
            "--source", "openapi",
            "--spec", bad,
        ])
        assert result.exit_code == 2
        assert "error" in result.output.lower() or "warn" in result.output.lower()

    def test_good_spec_proceeds_past_validation(self, tmp_path):
        from click.testing import CliRunner
        from cherenkov.cli.commands.validate import validate_cmd
        from unittest.mock import patch

        good = _write(tmp_path, "api.yaml", MINIMAL_OPENAPI)
        runner = CliRunner()

        with patch("cherenkov.cli.commands.validate.ValidationEngine") as MockEngine:
            MockEngine.return_value.validate_suite.return_value = {
                "status": "done",
                "reports": [{"scenario_id": "getHealth", "passed": True, "error": ""}],
            }
            result = runner.invoke(validate_cmd, [
                "--target", "http://localhost:9999",
                "--source", "openapi",
                "--spec", good,
            ])

        # Should not exit(1) — spec is valid
        assert result.exit_code == 0
