"""
R1 — spec-derived probe planner tests.

Proves `cherenkov verify` works on an arbitrary (non-Petstore) OpenAPI spec:
  1. unit: the planner emits the expected hypothesis classes from the spec,
     in the exact repro-step wire format the Witness parses;
  2. end-to-end (mutation-test pattern): a conformant in-process server
     yields ZERO divergences, a mutant server (accepts anything) yields
     several — on a spec containing no Petstore path;
  3. regression: the zero-config Petstore demo path is untouched.
"""
from __future__ import annotations

import copy
import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from cherenkov.divergence.probe_planner import (
    UnprobedEndpoint,
    plan_probes,
    spec_hypotheses,
    unprobed_endpoints,
)
from cherenkov.divergence.proof_run import PROOF_RUN_PROBES, run_proof
from cherenkov.divergence.witness import _parse_repro_steps

# ── synthetic non-Petstore spec ────────────────────────────────────────────────

ORDERS_SPEC: dict = {
    "openapi": "3.1.0",
    "info": {"title": "Orders API", "version": "1.0.0"},
    "paths": {
        "/orders": {
            "get": {
                "summary": "List orders",
                "parameters": [
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["open", "closed"]},
                    }
                ],
                "responses": {"200": {"description": "ok"}, "400": {"description": "bad"}},
            },
            "post": {
                "summary": "Create order",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Order"}
                        }
                    }
                },
                "responses": {"201": {"description": "created"}, "422": {"description": "invalid"}},
            },
        },
        "/orders/{orderId}": {
            "get": {
                "summary": "Get order",
                "parameters": [
                    {
                        "name": "orderId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {"200": {"description": "ok"}, "404": {"description": "missing"}},
            }
        },
        "/healthz": {
            "get": {
                "summary": "Health",
                "responses": {
                    "200": {
                        "description": "ok",
                        "headers": {"X-Service-Version": {"schema": {"type": "string"}}},
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["status"],
                                    "properties": {
                                        "status": {"type": "string"},
                                        "uptime_s": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
    },
    "components": {
        "schemas": {
            "Order": {
                "type": "object",
                "required": ["item", "quantity"],
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "integer"},
                },
            }
        }
    },
}


# ── in-process servers (mutation-test pattern) ────────────────────────────────

class _ConformantOrders(BaseHTTPRequestHandler):
    """Honors the Orders spec exactly."""

    def log_message(self, *_: object) -> None:
        """Placeholder docstring.

:param *_: <description>
:return: <description>"""
        pass

    def do_GET(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/orders":
            status = qs.get("status", [None])[0]
            if status is not None and status not in ("open", "closed"):
                self._respond(400, {"error": "invalid status"})
            else:
                self._respond(200, [])
        elif parsed.path.startswith("/orders/"):
            try:
                order_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self._respond(404, {"error": "missing"})
                return
            if order_id <= 0:
                self._respond(404, {"error": "missing"})
            else:
                self._respond(200, {"id": order_id, "item": "x", "quantity": 1})
        elif parsed.path == "/healthz":
            self._respond(200, {"status": "ok", "uptime_s": 1}, headers={"X-Service-Version": "test"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}
        if self.path == "/orders":
            if "item" not in body or "quantity" not in body:
                self._respond(422, {"error": "item and quantity are required"})
            else:
                self._respond(201, {"id": 1, **body})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, payload: object, headers: dict | None = None) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)


class _MutantOrders(_ConformantOrders):
    """Ignores every constraint — always 200."""

    def do_GET(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        self._respond(200, {"status": "ok", "data": []})

    def do_POST(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._respond(200, {"id": 99})


@contextmanager
def _serve(handler_cls: type) -> Generator[str, None, None]:
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
    """Placeholder docstring.

<description>"""


# ── unit: planner output ──────────────────────────────────────────────────────

class TestPlanProbes:
    def test_probes_cover_spec_endpoints_not_petstore(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        probes = plan_probes(ORDERS_SPEC)
        paths = {p for p, _, _, _ in probes}
        assert "/orders" in paths
        assert "/healthz" in paths
        assert not any(p.startswith("/pet") for p in paths)

    def test_max_probes_cap(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        assert len(plan_probes(ORDERS_SPEC, max_probes=2)) == 2
    """Placeholder docstring.

<description>"""

    def test_include_bare_covers_all_operations(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        bare = plan_probes(ORDERS_SPEC, include_bare=True)
        assert len(bare) >= len(plan_probes(ORDERS_SPEC))


class TestSpecHypotheses:
    def _all(self) -> list:
        out = []
        for path, item in ORDERS_SPEC["paths"].items():
            for method, op in item.items():
                out.extend(spec_hypotheses(path, method, op, ORDERS_SPEC))
        return out

    def test_required_field_omission_emitted(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        hyps = spec_hypotheses(
            "/orders", "post", ORDERS_SPEC["paths"]["/orders"]["post"], ORDERS_SPEC
        )
        omission = [h for h in hyps if "required" in h.claim_a]
        assert omission, "expected a required-field omission hypothesis"
        method, path, payload, expected = _parse_repro_steps(omission[0].repro_steps)
        assert (method, path, expected) == ("POST", "/orders", 422)
        assert payload is not None and "item" not in payload and "quantity" in payload

    def test_enum_violation_emitted(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        hyps = spec_hypotheses(
            "/orders", "get", ORDERS_SPEC["paths"]["/orders"]["get"], ORDERS_SPEC
        )
        enum = [h for h in hyps if "enum" in h.claim_a]
        assert enum
        method, path, _, expected = _parse_repro_steps(enum[0].repro_steps)
        assert method == "GET"
        assert path.startswith("/orders?status=INVALID_VALUE")
        assert expected == 400

    def test_documented_error_code_for_path_param(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        hyps = spec_hypotheses(
            "/orders/{orderId}",
            "get",
            ORDERS_SPEC["paths"]["/orders/{orderId}"]["get"],
            ORDERS_SPEC,
        )
        pathparam = [h for h in hyps if "invalid" in h.claim_a.lower()]
        assert pathparam
        method, path, _, expected = _parse_repro_steps(pathparam[0].repro_steps)
        assert (method, path, expected) == ("GET", "/orders/0", 404)

    def test_happy_path_emitted_for_healthz(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        hyps = spec_hypotheses(
            "/healthz", "get", ORDERS_SPEC["paths"]["/healthz"]["get"], ORDERS_SPEC
        )
        assert hyps
        _, path, _, expected = _parse_repro_steps(hyps[-1].repro_steps)
    """Placeholder docstring.

<description>"""
        assert (path, expected) == ("/healthz", 200)

    def test_every_hypothesis_is_witness_parseable(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        for h in self._all():
            _method, path, _, expected = _parse_repro_steps(h.repro_steps)
            assert path.startswith("/"), h.repro_steps
            assert expected is not None, h.repro_steps


# ── end-to-end: run_proof on a non-Petstore spec ─────────────────────────────

class TestRunProofSpecDerived:
    def test_conformant_server_zero_divergences(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with _serve(_ConformantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert reports == []

    def test_mutant_server_yields_divergences(self) -> None:
        """Placeholder docstring.

:return: <description>"""
    """Placeholder docstring.

<description>"""
        with _serve(_MutantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert len(reports) >= 3, [r.claim_a for r in reports]
        endpoints = {r.endpoint for r in reports}
        assert any("/orders" in (e or "") for e in endpoints)

    def test_max_probes_limits_execution(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with _serve(_MutantOrders) as base:
            capped = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False, max_probes=1)
        assert len(capped) <= 2  # at most the hypotheses of a single probe


# ── V2 oracles: response fields + headers ─────────────────────────────────────

class TestV2Oracles:
    def test_happy_path_carries_field_and_header_steps(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        hyps = spec_hypotheses(
            "/healthz", "get", ORDERS_SPEC["paths"]["/healthz"]["get"], ORDERS_SPEC
        )
        steps = [s for h in hyps for s in h.repro_steps]
        assert any("response contains fields: status" in s for s in steps), steps
        assert any("response header X-Service-Version" in s for s in steps), steps

    def test_header_step_does_not_parse_as_HEAD_method(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        method, path, _, expected = _parse_repro_steps(
            [
                "Send GET /healthz",
                "Expect 200 response per spec",
                "Expect response header X-Service-Version",
            ]
        )
        assert (method, path, expected) == ("GET", "/healthz", 200)

    def test_mutant_missing_field_and_header_caught(self) -> None:
    """Placeholder docstring.

<description>"""
        """Placeholder docstring.

:return: <description>"""
        # Mutant returns 200 {"status": "ok", "data": []} without the header:
        # status matches, so the V2 oracles must carry the divergence.
        with _serve(_MutantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        healthz = [r for r in reports if "healthz" in (r.endpoint or "")]
        assert healthz, [r.endpoint for r in reports]
        diff = healthz[0].evidence.diff
        assert "missing documented response headers" in diff, diff

    def test_conformant_still_zero_divergences_with_v2_oracles(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        with _serve(_ConformantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert reports == []


# ── regression: Petstore demo path untouched ──────────────────────────────────

class TestPetstoreDemoRegression:
    def test_demo_probes_are_still_the_hardcoded_five(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        assert len(PROOF_RUN_PROBES) == 5
        assert all(p.startswith(("/pet", "/store", "/user")) for p, _, _, _ in PROOF_RUN_PROBES)

    def test_spec_none_uses_demo_probes_without_error(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        # Dead port: every reproduction fails to execute → no reports, no raise.
        reports = run_proof(base_url="http://127.0.0.1:1", spec=None, use_llm=False)
        assert reports == []


# ── unprobed coverage reporting ───────────────────────────────────────────────


class TestUnprobedEndpoints:
    """A zero-probe endpoint yields zero divergences, which is indistinguishable
    from a conformant one. Whatever planning declines to cover must be said out
    loud, and the stated reason must be the real one.
    """

    def test_every_operation_is_either_planned_or_reported(self) -> None:
        """The accounting invariant. If this drifts, coverage is being lost
        somewhere that nothing reports."""
        operations = {
            (path, method.upper())
            for path, item in ORDERS_SPEC["paths"].items()
            for method in item
            if method.lower() in {"get", "put", "post", "delete", "patch"}
        }
        planned = {(p, m) for p, m, _, _ in plan_probes(ORDERS_SPEC)}
        reported = {(u.path, u.method) for u in unprobed_endpoints(ORDERS_SPEC)}

        assert planned | reported == operations
        assert not (planned & reported), "an endpoint cannot be both probed and unprobed"

    def test_non_get_is_attributed_to_the_get_only_guard(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/things": {
                    "post": {"responses": {"200": {"description": "ok"}}},
                }
            },
        }
        missing = unprobed_endpoints(spec)
        assert len(missing) == 1
        assert "GET-only" in missing[0].reason
        assert "mutate state" in missing[0].reason

    def test_required_query_param_guard_names_the_parameter(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/search": {
                    "get": {
                        "parameters": [
                            {"name": "q", "in": "query", "required": True,
                             "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "ok"}},
                    }
                }
            },
        }
        missing = unprobed_endpoints(spec)
        assert len(missing) == 1
        assert "query parameters are required" in missing[0].reason
        assert "q" in missing[0].reason

    def test_templated_get_is_not_blamed_on_missing_status_codes(self) -> None:
        """Regression on a wrong diagnosis: this endpoint documents 200/400/404,
        so 'documents no status code' was false. The real cause is the
        templated-path guard."""
        spec = {
            "openapi": "3.0.0",
            "paths": {
                "/user/{name}": {
                    "get": {
                        "parameters": [
                            {"name": "name", "in": "path", "required": True,
                             "schema": {"type": "string"}}
                        ],
                        "responses": {
                            "200": {"description": "ok"},
                            "400": {"description": "bad"},
                            "404": {"description": "missing"},
                        },
                    }
                }
            },
        }
        missing = unprobed_endpoints(spec)
        assert len(missing) == 1
        reason = missing[0].reason
        assert "templated paths" in reason
        assert "status code" not in reason, f"misattributed: {reason}"

    def test_cap_truncation_is_reported_not_silent(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        missing = unprobed_endpoints(ORDERS_SPEC, max_probes=1)
        capped = [m for m in missing if "max_probes" in m.reason]
        assert capped, "a silent cap is a silent loss of coverage"

    def test_str_is_human_readable(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        item = UnprobedEndpoint(path="/x", method="POST", reason="because")
        assert str(item) == "POST /x — because"

    def test_fully_probeable_spec_reports_nothing(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = {
            "openapi": "3.0.0",
    """Placeholder docstring.

<description>"""
            "paths": {"/healthz": {"get": {"responses": {"200": {"description": "ok"}}}}},
        }
        assert unprobed_endpoints(spec) == []


# ── PathItem-level parameters (OpenAPI 3.x shared-parameter form) ─────────────

def _hoist_params_to_path_item(spec: dict) -> dict:
    """Move every operation's `parameters` up onto its PathItem.

    Same API, the other legal spelling. Reading only `operation.parameters`
    made `{orderId}` unfillable, so the endpoint was dropped from planning
    entirely and `verify` reported a clean run on an unprobed endpoint.
    """
    out = copy.deepcopy(spec)
    for path_item in out["paths"].values():
        hoisted: list[dict] = []
        for method, operation in path_item.items():
            if method.lower() not in {"get", "put", "post", "delete", "patch"}:
                continue
            hoisted.extend(operation.pop("parameters", []) or [])
        if hoisted:
            path_item["parameters"] = hoisted
    return out


class TestPathItemLevelParameters:
    def test_path_param_on_path_item_still_plans_probes(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        assert not shared["paths"]["/orders/{orderId}"]["get"].get("parameters")

        planned = {p for p, _, _, _ in plan_probes(shared)}
        assert "/orders/{orderId}" in planned, (
            "endpoint silently dropped — verify would report it clean without probing it"
        )

    def test_hypotheses_match_the_operation_level_spelling(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        own = spec_hypotheses(
            "/orders/{orderId}", "get", ORDERS_SPEC["paths"]["/orders/{orderId}"]["get"], ORDERS_SPEC
        )
        inherited = spec_hypotheses(
            "/orders/{orderId}", "get", shared["paths"]["/orders/{orderId}"]["get"], shared
        )
        assert {h.claim_a for h in inherited} == {h.claim_a for h in own}

    def test_enum_query_param_on_path_item_is_probed(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        hyps = spec_hypotheses("/orders", "get", shared["paths"]["/orders"]["get"], shared)
        assert [h for h in hyps if "enum" in h.claim_a.lower()]
    """Placeholder docstring.

<description>"""
    def test_unprobed_report_names_the_inheritance_failure(self) -> None:
        """The false-clean this whole class exists for: before the merge, this
        endpoint vanished from planning with no warning at all."""
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        # Strip the declaration entirely — the shape the demo spec actually has.
        del shared["paths"]["/orders/{orderId}"]["parameters"]

        missing = unprobed_endpoints(shared)
        orders = [m for m in missing if m.path == "/orders/{orderId}"]
        assert orders, "an endpoint dropped from planning must be reported"
        assert "could not be sampled" in orders[0].reason
        assert "{orderId}" in orders[0].reason

    def test_operation_level_wins_on_collision(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = copy.deepcopy(ORDERS_SPEC)
        item = spec["paths"]["/orders/{orderId}"]
        # A shared param that would fill the same placeholder with a different value.
        item["parameters"] = [
            {"name": "orderId", "in": "path", "schema": {"type": "string", "default": "SHARED"}}
    """Placeholder docstring.

<description>"""
        ]
        hyps = spec_hypotheses("/orders/{orderId}", "get", item["get"], spec)
        pathparam = [h for h in hyps if "invalid" in h.claim_a.lower()]
        assert pathparam
        _, path, _, _ = _parse_repro_steps(pathparam[0].repro_steps)
        assert path == "/orders/0", "operation-level parameter must take precedence"


# ── Known Identifiers and Mutations ──────────────────────────────────────────

class TestKnownIdentifiers:
    def test_known_identifiers_used_for_path_generation(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = copy.deepcopy(ORDERS_SPEC)

        # Even with schema, default is 0. If we provide known_identifiers, it should use that instead.
        hyps = spec_hypotheses(
            "/orders/{orderId}", "get", spec["paths"]["/orders/{orderId}"]["get"], spec,
            known_identifiers={"orderId": ["42"]}
        )
        # Find the happy path hypothesis
        happy = [h for h in hyps if "Expect 200 response" in h.repro_steps[1]]
        assert happy
        method, path, _, _ = _parse_repro_steps(happy[0].repro_steps)
        assert path == "/orders/42"

        # Test planning with it
        probes_with = plan_probes(spec, known_identifiers={"orderId": ["99"]})
        assert "/orders/{orderId}" in {p for p, _, _, _ in probes_with}


class TestAllowMutations:
    def test_allow_mutations_generates_post_happy_path(self) -> None:
        """Placeholder docstring.

:return: <description>"""
        spec = copy.deepcopy(ORDERS_SPEC)

        # Without allow_mutations, no happy path hypothesis for POST
        hyps_without = spec_hypotheses(
            "/orders", "post", spec["paths"]["/orders"]["post"], spec, allow_mutations=False
        )
        assert not any("per spec" in h.repro_steps[1] for h in hyps_without)

        # With allow_mutations, happy path hypothesis is generated
        hyps_with = spec_hypotheses(
            "/orders", "post", spec["paths"]["/orders"]["post"], spec, allow_mutations=True
        )
        assert any("per spec" in h.repro_steps[1] for h in hyps_with)
