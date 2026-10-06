"""#995: `cherenkov diff` must see schema-level breaking changes, not just paths and params."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from click.testing import CliRunner

from cherenkov.cli.commands.simple import diff_cmd
from cherenkov.diff.spec_differ import ChangeType, SpecDiffer

PET = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "status": {"type": "string", "enum": ["available", "sold"]},
    },
}


def _spec(schemas: dict | None = None, request: dict | None = None, response: dict | None = None) -> dict:
    op: dict = {"responses": {"200": {"description": "OK"}}}
    if request is not None:
        op["requestBody"] = {"content": {"application/json": {"schema": request}}}
    if response is not None:
        op["responses"]["200"]["content"] = {"application/json": {"schema": response}}
    return {
        "openapi": "3.0.0", "info": {"title": "T", "version": "1"},
        "paths": {"/pets": {"post": op}},
        "components": {"schemas": schemas if schemas is not None else {"Pet": copy.deepcopy(PET)}},
    }


def _diff(tmp_path: Path, before: dict, after: dict):
    b, a = tmp_path / "b.json", tmp_path / "a.json"
    b.write_text(json.dumps(before))
    a.write_text(json.dumps(after))
    return SpecDiffer().diff(str(b), str(a))


def _types(changes) -> set[ChangeType]:
    return {c.change_type for c in changes}


def test_new_required_field_in_component_schema_is_breaking(tmp_path):
    after = _spec()
    after["components"]["schemas"]["Pet"]["required"].append("name")
    report = _diff(tmp_path, _spec(), after)
    assert ChangeType.ADDED_REQUIRED_FIELD in _types(report.breaking)
    assert "name" in report.breaking[0].detail and "Pet" in report.breaking[0].detail


def test_removed_field_is_breaking(tmp_path):
    after = _spec()
    del after["components"]["schemas"]["Pet"]["properties"]["name"]
    assert ChangeType.REMOVED_FIELD in _types(_diff(tmp_path, _spec(), after).breaking)


def test_field_type_change_is_breaking(tmp_path):
    after = _spec()
    after["components"]["schemas"]["Pet"]["properties"]["id"]["type"] = "string"
    report = _diff(tmp_path, _spec(), after)
    assert ChangeType.CHANGED_FIELD_TYPE in _types(report.breaking)


def test_removed_enum_value_is_breaking_added_is_additive(tmp_path):
    shrunk = _spec()
    shrunk["components"]["schemas"]["Pet"]["properties"]["status"]["enum"] = ["available"]
    assert ChangeType.REMOVED_ENUM_VALUE in _types(_diff(tmp_path, _spec(), shrunk).breaking)
    grown = _spec()
    grown["components"]["schemas"]["Pet"]["properties"]["status"]["enum"].append("pending")
    report = _diff(tmp_path, _spec(), grown)
    assert not report.breaking and ChangeType.ADDED_ENUM_VALUE in _types(report.additive)


def test_removed_schema_is_breaking(tmp_path):
    assert ChangeType.REMOVED_SCHEMA in _types(_diff(tmp_path, _spec(), _spec(schemas={})).breaking)


def test_new_optional_field_is_additive(tmp_path):
    after = _spec()
    after["components"]["schemas"]["Pet"]["properties"]["tag"] = {"type": "string"}
    report = _diff(tmp_path, _spec(), after)
    assert not report.breaking and ChangeType.ADDED_OPTIONAL_FIELD in _types(report.additive)


def test_identical_schemas_are_clean(tmp_path):
    report = _diff(tmp_path, _spec(), _spec())
    assert not (report.breaking or report.additive or report.informational)


def test_inline_request_body_change_is_breaking(tmp_path):
    before = _spec(request={"type": "object", "properties": {"q": {"type": "string"}}})
    after = _spec(request={"type": "object", "required": ["q"], "properties": {"q": {"type": "string"}}})
    report = _diff(tmp_path, before, after)
    breaking = [c for c in report.breaking if c.change_type == ChangeType.ADDED_REQUIRED_FIELD]
    assert breaking and breaking[0].endpoint == "/pets" and breaking[0].method == "POST"


def test_nested_ref_change_is_found_through_the_body_ref(tmp_path):
    before = _spec(response={"$ref": "#/components/schemas/Pet"})
    after = _spec(response={"$ref": "#/components/schemas/Pet"})
    after["components"]["schemas"]["Pet"]["properties"]["id"]["type"] = "string"
    report = _diff(tmp_path, before, after)
    assert ChangeType.CHANGED_FIELD_TYPE in _types(report.breaking)


def test_recursive_schema_does_not_hang(tmp_path):
    node = {"type": "object", "properties": {"next": {"$ref": "#/components/schemas/Node"}, "v": {"type": "integer"}}}
    before = _spec(schemas={"Node": node}, response={"$ref": "#/components/schemas/Node"})
    after = copy.deepcopy(before)
    after["components"]["schemas"]["Node"]["properties"]["v"]["type"] = "string"
    assert ChangeType.CHANGED_FIELD_TYPE in _types(_diff(tmp_path, before, after).breaking)


def test_cli_exits_1_on_schema_only_breaking_change(tmp_path):
    after = _spec()
    after["components"]["schemas"]["Pet"]["required"].append("name")
    b, a = tmp_path / "b.json", tmp_path / "a.json"
    b.write_text(json.dumps(_spec()))
    a.write_text(json.dumps(after))
    result = CliRunner().invoke(diff_cmd, ["--before", str(b), "--after", str(a)])
    assert result.exit_code == 1 and "No changes detected" not in result.output
