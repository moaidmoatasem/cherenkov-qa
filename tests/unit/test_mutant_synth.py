"""tests/unit/test_mutant_synth.py — pure unit tests for spec-derived mutant synthesis.

No Docker, no LLM, no network: `synthesize_mutant_response` and
`spawn_mutant_server` are pure functions over an in-memory operation dict.
"""
from __future__ import annotations

from cherenkov.divergence.mutant_synth import (
    explain_unmutatable,
    spawn_mutant_server,
    synthesize_mutant_battery,
    synthesize_mutant_response,
)

_OPERATION_GET = {
    "parameters": [
        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
    ],
    "responses": {
        "200": {
            "description": "OK",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["id", "status"],
                        "properties": {
                            "id": {"type": "integer"},
                            "status": {"type": "string"},
                        },
                    }
                }
            },
        }
    },
}

_OPERATION_POST_201 = {
    "responses": {
        "201": {
            "content": {
                "application/json": {"schema": {"type": "object", "properties": {}}}
            }
        }
    }
}

_OPERATION_NO_SUCCESS = {"responses": {"400": {"description": "bad request"}}}


class TestSynthesizeMutantResponse:
    def test_substitutes_path_params_and_mutates_status(self):
        result = synthesize_mutant_response("/orders/{id}", _OPERATION_GET)
        assert result is not None
        path, status, _body = result
        assert path == "/orders/1"
        assert status == 201  # documented success was 200

    def test_drops_first_documented_required_field(self):
        _, _, body = synthesize_mutant_response("/orders/{id}", _OPERATION_GET)
        assert "id" not in body
        assert "status" in body

    def test_status_swap_from_201_goes_to_200(self):
        result = synthesize_mutant_response("/orders", _OPERATION_POST_201)
        assert result is not None
        _, status, _ = result
        assert status == 200

    def test_returns_none_without_documented_success(self):
        assert synthesize_mutant_response("/x", _OPERATION_NO_SUCCESS) is None

    def test_returns_none_when_path_param_unfillable(self):
        # No 'schema' on the path param at all -> _sample_value still fills it,
        # but an operation missing parameter declarations entirely leaves the
        # placeholder unresolved.
        op = {**_OPERATION_GET, "parameters": []}
        result = synthesize_mutant_response("/orders/{id}", op)
        assert result is None


class TestSpawnMutantServer:
    def test_returns_none_without_documented_success(self):
        assert spawn_mutant_server(19999, "/x", _OPERATION_NO_SUCCESS) is None

    def test_builds_broken_impl_server_matching_synthesis(self):
        server = spawn_mutant_server(19999, "/orders/{id}", _OPERATION_GET)
        assert server is not None
        assert server.port == 19999
        assert server.responses == {"/orders/1": (201, {"status": "probe_status"})}


_OPERATION_ENUM = {
    "parameters": [
        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}},
    ],
    "responses": {
        "200": {
            "description": "OK",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["id", "total", "status"],
                        "properties": {
                            "id": {"type": "integer"},
                            "total": {"type": "number"},
                            "status": {"type": "string", "enum": ["paid", "pending"]},
                        },
                    }
                }
            },
        }
    },
}


class TestSynthesizeMutantBattery:
    """One mutant per axis, so a failure is attributable.

    The single coarse mutant perturbs status AND drops a field together, which
    measured zero discrimination on the labelled cheat corpus — every suite
    fails it, so a weakened one scores meaningful.
    See docs/evidence/e0.5e_oracle_discrimination.md.
    """

    RECORDED = (200, {"id": 42, "total": 99.5, "status": "paid"})

    def test_returns_none_when_unmutatable(self):
        assert synthesize_mutant_battery("/x", _OPERATION_NO_SUCCESS) is None

    def test_axes_are_isolated_from_each_other(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM, base=self.RECORDED)
        assert built is not None
        _, battery = built

        base_status, base_body = self.RECORDED
        # status mutant: body untouched, status differs
        assert battery["status"][1] == base_body
        assert battery["status"][0] != base_status
        # value mutant: status untouched, exactly one field differs
        assert battery["value"][0] == base_status
        differing = [k for k, v in battery["value"][1].items() if base_body[k] != v]
        assert len(differing) == 1, differing

    def test_conforming_control_is_the_recorded_response(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM, base=self.RECORDED)
        assert built is not None
        assert built[1]["conforming"] == self.RECORDED

    def test_base_overrides_schema_sampling(self):
        """Schema sampling yields the right types but arbitrary values, which
        makes an honest suite fail the control. `base` is what fixes that."""
        sampled = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM)
        recorded = synthesize_mutant_battery(
            "/orders/{id}", _OPERATION_ENUM, base=self.RECORDED
        )
        assert sampled is not None and recorded is not None
        assert sampled[1]["conforming"] != recorded[1]["conforming"]
        assert recorded[1]["conforming"][1]["total"] == 99.5

    def test_value_mutation_preserves_json_type(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM, base=self.RECORDED)
        assert built is not None
        mutated = built[1]["value"][1]
        for key, original in self.RECORDED[1].items():
            assert isinstance(mutated[key], type(original)), (
                f"{key} changed JSON type — a validator would catch that, which "
                "proves nothing about whether the assertion checked the value"
            )

    def test_enum_mutation_falls_outside_the_allowed_set(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM, base=self.RECORDED)
        assert built is not None
        assert "enum" in built[1]
        assert built[1]["enum"][1]["status"] not in ("paid", "pending")

    def test_no_enum_mutant_without_an_enum_in_the_schema(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_GET, base=self.RECORDED)
        assert built is not None
        assert "enum" not in built[1]

    def test_missing_mutant_drops_a_required_field(self):
        built = synthesize_mutant_battery("/orders/{id}", _OPERATION_ENUM, base=self.RECORDED)
        assert built is not None
        dropped = set(self.RECORDED[1]) - set(built[1]["missing"][1])
        assert len(dropped) == 1


class TestExplainUnmutatable:
    """`synthesize_mutant_response` returns None for two unrelated reasons.

    The gate reported both as "no documented success response", which sent
    readers hunting for a missing 200 on specs that documented one fine.
    """

    def test_names_the_missing_success_response(self):
        reason = explain_unmutatable("/orders", _OPERATION_NO_SUCCESS)
        assert "no 2xx success response" in reason
        assert "400" in reason, "should list what the spec does document"

    def test_names_the_unfillable_path_parameter(self):
        # Documents a 200, but nothing declares {id} — the other None cause.
        undeclared = {k: v for k, v in _OPERATION_GET.items() if k != "parameters"}
        assert synthesize_mutant_response("/orders/{id}", undeclared) is None

        reason = explain_unmutatable("/orders/{id}", undeclared)
        assert "path parameters could not be sampled" in reason
        assert "{id}" in reason
        assert "success response" not in reason, "must not blame the response"

    def test_the_two_causes_do_not_share_a_message(self):
        undeclared = {k: v for k, v in _OPERATION_GET.items() if k != "parameters"}
        assert explain_unmutatable("/orders", _OPERATION_NO_SUCCESS) != explain_unmutatable(
            "/orders/{id}", undeclared
        )
