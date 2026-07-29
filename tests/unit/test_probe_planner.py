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

from cherenkov.divergence.probe_planner import plan_probes, spec_hypotheses
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
        pass

    def do_GET(self) -> None:
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
        self._respond(200, {"status": "ok", "data": []})

    def do_POST(self) -> None:
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


# ── unit: planner output ──────────────────────────────────────────────────────

class TestPlanProbes:
    def test_probes_cover_spec_endpoints_not_petstore(self) -> None:
        probes = plan_probes(ORDERS_SPEC)
        paths = {p for p, _, _, _ in probes}
        assert "/orders" in paths
        assert "/healthz" in paths
        assert not any(p.startswith("/pet") for p in paths)

    def test_max_probes_cap(self) -> None:
        assert len(plan_probes(ORDERS_SPEC, max_probes=2)) == 2

    def test_include_bare_covers_all_operations(self) -> None:
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
        hyps = spec_hypotheses(
            "/orders", "post", ORDERS_SPEC["paths"]["/orders"]["post"], ORDERS_SPEC
        )
        omission = [h for h in hyps if "required" in h.claim_a]
        assert omission, "expected a required-field omission hypothesis"
        method, path, payload, expected = _parse_repro_steps(omission[0].repro_steps)
        assert (method, path, expected) == ("POST", "/orders", 422)
        assert payload is not None and "item" not in payload and "quantity" in payload

    def test_enum_violation_emitted(self) -> None:
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
        hyps = spec_hypotheses(
            "/healthz", "get", ORDERS_SPEC["paths"]["/healthz"]["get"], ORDERS_SPEC
        )
        assert hyps
        _, path, _, expected = _parse_repro_steps(hyps[-1].repro_steps)
        assert (path, expected) == ("/healthz", 200)

    def test_every_hypothesis_is_witness_parseable(self) -> None:
        for h in self._all():
            _method, path, _, expected = _parse_repro_steps(h.repro_steps)
            assert path.startswith("/"), h.repro_steps
            assert expected is not None, h.repro_steps


# ── end-to-end: run_proof on a non-Petstore spec ─────────────────────────────

class TestRunProofSpecDerived:
    def test_conformant_server_zero_divergences(self) -> None:
        with _serve(_ConformantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert reports == []

    def test_mutant_server_yields_divergences(self) -> None:
        with _serve(_MutantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert len(reports) >= 3, [r.claim_a for r in reports]
        endpoints = {r.endpoint for r in reports}
        assert any("/orders" in (e or "") for e in endpoints)

    def test_max_probes_limits_execution(self) -> None:
        with _serve(_MutantOrders) as base:
            capped = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False, max_probes=1)
        assert len(capped) <= 2  # at most the hypotheses of a single probe


# ── V2 oracles: response fields + headers ─────────────────────────────────────

class TestV2Oracles:
    def test_happy_path_carries_field_and_header_steps(self) -> None:
        hyps = spec_hypotheses(
            "/healthz", "get", ORDERS_SPEC["paths"]["/healthz"]["get"], ORDERS_SPEC
        )
        steps = [s for h in hyps for s in h.repro_steps]
        assert any("response contains fields: status" in s for s in steps), steps
        assert any("response header X-Service-Version" in s for s in steps), steps

    def test_header_step_does_not_parse_as_HEAD_method(self) -> None:
        method, path, _, expected = _parse_repro_steps(
            [
                "Send GET /healthz",
                "Expect 200 response per spec",
                "Expect response header X-Service-Version",
            ]
        )
        assert (method, path, expected) == ("GET", "/healthz", 200)

    def test_mutant_missing_field_and_header_caught(self) -> None:
        # Mutant returns 200 {"status": "ok", "data": []} without the header:
        # status matches, so the V2 oracles must carry the divergence.
        with _serve(_MutantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        healthz = [r for r in reports if "healthz" in (r.endpoint or "")]
        assert healthz, [r.endpoint for r in reports]
        diff = healthz[0].evidence.diff
        assert "missing documented response headers" in diff, diff

    def test_conformant_still_zero_divergences_with_v2_oracles(self) -> None:
        with _serve(_ConformantOrders) as base:
            reports = run_proof(base_url=base, spec=ORDERS_SPEC, use_llm=False)
        assert reports == []


# ── regression: Petstore demo path untouched ──────────────────────────────────

class TestPetstoreDemoRegression:
    def test_demo_probes_are_still_the_hardcoded_five(self) -> None:
        assert len(PROOF_RUN_PROBES) == 5
        assert all(p.startswith(("/pet", "/store", "/user")) for p, _, _, _ in PROOF_RUN_PROBES)

    def test_spec_none_uses_demo_probes_without_error(self) -> None:
        # Dead port: every reproduction fails to execute → no reports, no raise.
        reports = run_proof(base_url="http://127.0.0.1:1", spec=None, use_llm=False)
        assert reports == []


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
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        assert not shared["paths"]["/orders/{orderId}"]["get"].get("parameters")

        planned = {p for p, _, _, _ in plan_probes(shared)}
        assert "/orders/{orderId}" in planned, (
            "endpoint silently dropped — verify would report it clean without probing it"
        )

    def test_hypotheses_match_the_operation_level_spelling(self) -> None:
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        own = spec_hypotheses(
            "/orders/{orderId}", "get", ORDERS_SPEC["paths"]["/orders/{orderId}"]["get"], ORDERS_SPEC
        )
        inherited = spec_hypotheses(
            "/orders/{orderId}", "get", shared["paths"]["/orders/{orderId}"]["get"], shared
        )
        assert {h.claim_a for h in inherited} == {h.claim_a for h in own}

    def test_enum_query_param_on_path_item_is_probed(self) -> None:
        shared = _hoist_params_to_path_item(ORDERS_SPEC)
        hyps = spec_hypotheses("/orders", "get", shared["paths"]["/orders"]["get"], shared)
        assert [h for h in hyps if "enum" in h.claim_a.lower()]

    def test_operation_level_wins_on_collision(self) -> None:
        spec = copy.deepcopy(ORDERS_SPEC)
        item = spec["paths"]["/orders/{orderId}"]
        # A shared param that would fill the same placeholder with a different value.
        item["parameters"] = [
            {"name": "orderId", "in": "path", "schema": {"type": "string", "default": "SHARED"}}
        ]
        hyps = spec_hypotheses("/orders/{orderId}", "get", item["get"], spec)
        pathparam = [h for h in hyps if "invalid" in h.claim_a.lower()]
        assert pathparam
        _, path, _, _ = _parse_repro_steps(pathparam[0].repro_steps)
        assert path == "/orders/0", "operation-level parameter must take precedence"
