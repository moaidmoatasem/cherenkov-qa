"""tests/unit/test_mutant_synth.py — pure unit tests for spec-derived mutant synthesis.

No Docker, no LLM, no network: `synthesize_mutant_response` and
`spawn_mutant_server` are pure functions over an in-memory operation dict.
"""
from __future__ import annotations

from cherenkov.divergence.mutant_synth import (
    explain_unmutatable,
    spawn_mutant_server,
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
