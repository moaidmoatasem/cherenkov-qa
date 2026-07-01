"""
Mutation test for the divergence-detection engine.

Two minimal HTTP servers are spun up in-process:
  _ConformantHandler — validates enum and required-field constraints (returns 400/422 on bad input)
  _MutantHandler     — silently accepts bad input (always 200)

Tests confirm that WitnessAgent detects divergences on the mutant but NOT on the conformant server,
proving the detector has real teeth.
"""
from __future__ import annotations

import json
import threading
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Generator
from urllib.parse import parse_qs, urlparse

import pytest

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    Severity,
)
from cherenkov.divergence.witness import WitnessAgent


# ── minimal in-process servers ─────────────────────────────────────────────────

class _ConformantHandler(BaseHTTPRequestHandler):
    """Validates enum and required fields — behaves as spec demands."""

    def log_message(self, *_: object) -> None:
        pass  # suppress test output

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/pet/findByStatus":
            status_vals = qs.get("status", [])
            valid = {"available", "pending", "sold"}
            if not status_vals or status_vals[0] not in valid:
                self._respond(400, {"error": "Invalid status value"})
            else:
                self._respond(200, [])
        elif parsed.path.startswith("/pet/"):
            try:
                pet_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self._respond(400, {"error": "Invalid petId"})
                return
            if pet_id <= 0:
                self._respond(400, {"error": "Invalid ID supplied"})
            else:
                self._respond(200, {"id": pet_id, "name": "test"})
        elif parsed.path == "/store/inventory":
            self._respond(200, {"available": 1})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length else b""
        try:
            body = json.loads(body_bytes) if body_bytes else {}
        except Exception:
            body = {}

        if self.path == "/pet":
            if "photoUrls" not in body:
                self._respond(400, {"error": "photoUrls is required"})
            else:
                self._respond(200, {"id": 1, **body})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, payload: object) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class _MutantHandler(BaseHTTPRequestHandler):
    """Ignores validation — always 200, proving the detector catches the gap."""

    def log_message(self, *_: object) -> None:
        pass

    def do_GET(self) -> None:
        self._respond(200, {"status": "ok", "data": []})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)  # drain body
        self._respond(200, {"id": 99, "name": "mutant"})

    def _respond(self, code: int, payload: object) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@contextmanager
def _serve(handler_cls: type) -> Generator[str, None, None]:
    """Start an HTTPServer on a free port and yield its base URL."""
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


# ── hypothesis factories ───────────────────────────────────────────────────────

def _enum_hyp() -> DivergenceHypothesis:
    """Hypothesis: server must reject invalid enum value for ?status=."""
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="GET /pet/findByStatus with status=invalid_value should return 400",
        claim_b="server accepts any status value and returns 200",
        predicted_evidence="status mismatch: expected=400, actual=200",
        severity=Severity.HIGH,
        endpoint="GET /pet/findByStatus",
        repro_steps=[
            "Send GET /pet/findByStatus?status=invalid_value",
            "Expect 400",
        ],
    )


def _required_field_hyp() -> DivergenceHypothesis:
    """Hypothesis: POST /pet without photoUrls should return 4xx."""
    return DivergenceHypothesis(
        id=str(uuid.uuid4()),
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        claim_a="POST /pet without required field 'photoUrls' should return 400",
        claim_b="server accepts pets without photoUrls and returns 200",
        predicted_evidence="status mismatch: expected=400, actual=200",
        severity=Severity.HIGH,
        endpoint="POST /pet",
        repro_steps=[
            'Send POST /pet with body {"name": "rover"}',
            "Expect 400",
        ],
    )


# ── WitnessAgent-level tests ───────────────────────────────────────────────────

class TestWitnessAgentMutation:
    def test_conformant_enum_not_divergence(self) -> None:
        """Conformant server returns 400 → witness should NOT flag as divergence."""
        with _serve(_ConformantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            result = agent.reproduce(_enum_hyp())
        assert result.reproduced is False, (
            f"Expected no divergence on conformant server; got: {result}"
        )

    def test_mutant_enum_is_divergence(self) -> None:
        """Mutant server returns 200 on invalid enum → witness MUST flag as divergence."""
        with _serve(_MutantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            result = agent.reproduce(_enum_hyp())
        assert result.reproduced is True, (
            f"Expected divergence on mutant server; got: {result}"
        )

    def test_conformant_required_field_not_divergence(self) -> None:
        """Conformant server returns 422 → witness should NOT flag as divergence."""
        with _serve(_ConformantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            result = agent.reproduce(_required_field_hyp())
        assert result.reproduced is False, (
            f"Expected no divergence on conformant server; got: {result}"
        )

    def test_mutant_required_field_is_divergence(self) -> None:
        """Mutant server returns 200 on missing required field → witness MUST flag divergence."""
        with _serve(_MutantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            result = agent.reproduce(_required_field_hyp())
        assert result.reproduced is True, (
            f"Expected divergence on mutant server; got: {result}"
        )

    def test_mutant_evidence_contains_status_mismatch(self) -> None:
        """Evidence diff must describe the status mismatch, not be empty."""
        with _serve(_MutantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            result = agent.reproduce(_enum_hyp())
        assert result.evidence is not None
        assert "status mismatch" in result.evidence.diff or "400" in result.evidence.diff, (
            f"Unexpected diff content: {result.evidence.diff!r}"
        )

    def test_conformant_batch_no_divergences(self) -> None:
        """Batch reproduction: neither hypothesis diverges on the conformant server."""
        hyps = [_enum_hyp(), _required_field_hyp()]
        with _serve(_ConformantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            results = agent.reproduce_batch(hyps)
        assert len(results) == 2
        diverged = [r for r in results if r.reproduced]
        assert diverged == [], f"Unexpected divergences on conformant server: {diverged}"

    def test_mutant_batch_all_divergences(self) -> None:
        """Batch reproduction: both hypotheses diverge on the mutant server."""
        hyps = [_enum_hyp(), _required_field_hyp()]
        with _serve(_MutantHandler) as base_url:
            agent = WitnessAgent(base_url=base_url)
            results = agent.reproduce_batch(hyps)
        assert len(results) == 2
        diverged = [r for r in results if r.reproduced]
        assert len(diverged) == 2, (
            f"Expected both hypotheses to diverge on mutant server; got: {results}"
        )


# ── run_proof-level tests ──────────────────────────────────────────────────────

class TestRunProofMutation:
    def test_conformant_server_no_probed_endpoint_divergences(self) -> None:
        """
        run_proof against a conformant server: the two endpoints our server
        handles (/pet/findByStatus, /pet POST) should produce zero divergences.
        """
        from cherenkov.divergence.proof_run import run_proof

        with _serve(_ConformantHandler) as base_url:
            reports = run_proof(base_url=base_url, use_llm=False)

        handled_endpoints = {"/pet/findByStatus", "/pet"}
        diverged_handled = [
            r for r in reports
            if any(ep in (r.endpoint or "") for ep in handled_endpoints)
        ]
        assert diverged_handled == [], (
            f"Conformant server produced unexpected divergences: {diverged_handled}"
        )

    def test_mutant_server_triggers_at_least_one_divergence(self) -> None:
        """
        run_proof against the mutant server must find ≥1 divergence on the
        endpoints our mutant mishandles (/pet/findByStatus, /pet POST).
        """
        from cherenkov.divergence.proof_run import run_proof

        with _serve(_MutantHandler) as base_url:
            reports = run_proof(base_url=base_url, use_llm=False)

        assert len(reports) >= 1, (
            "Mutant server should produce at least one divergence report; got zero."
        )
