"""
CHERENKOV divergence/self_play.py — E3-3 Adversarial self-play (anti reward-hacking).

A candidate test must pass a correct mock AND fail a deliberately-broken
implementation. A test that passes both is tautological (true==true) and is
killed. This directly attacks the existential failure mode of autonomous QA.

Usage pattern:
    broken = BrokenImplServer(port=19999, responses={"/pet/1": (500, {"error": "gone"})})
    with broken:
        result = self_play.validate(
            test_id="test_get_pet",
            run_test=lambda url: run_playwright_or_httpx_test(url),
            correct_mock_url="http://localhost:4010",
            broken_mock_url="http://localhost:19999",
        )
    if result.tautological:
        print(f"KILLED: {result.kill_reason}")
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable


@dataclass
class SelfPlayResult:
    """Outcome of one adversarial self-play validation."""
    test_id: str
    passed_correct: bool        # test passed against the spec-conforming mock
    failed_broken: bool         # test failed against the deliberately-broken server
    tautological: bool          # True → kill this test
    kill_reason: str = ""
    correct_mock_output: str = ""
    broken_impl_output: str = ""


class BrokenImplServer:
    """
    A minimal HTTP server that returns deliberately incorrect responses.

    Use as a context manager:
        with BrokenImplServer(port=19999, responses={"/pet/1": (500, {"err": "x"})}) as s:
            ...

    responses: mapping of path → (status_code, body)
      body can be a dict (serialised as JSON) or a plain string.
    All HTTP verbs (GET, POST, PUT, DELETE, PATCH) hit the same response map.
    """

    def __init__(
        self,
        port: int,
        responses: dict[str, tuple[int, str | dict]],
        default: tuple[int, str | dict] = (500, {"error": "not configured"}),
    ) -> None:
        self.port = port
        self.responses = responses
        self.default = default
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "BrokenImplServer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def start(self) -> None:
        responses = self.responses
        default = self.default

        class _Handler(BaseHTTPRequestHandler):
            def _respond(self) -> None:
                status, body = responses.get(self.path, default)
                body_bytes = (
                    json.dumps(body).encode()
                    if isinstance(body, dict)
                    else str(body).encode()
                )
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body_bytes)))
                self.end_headers()
                self.wfile.write(body_bytes)

            def log_message(self, *_: object) -> None:
                pass  # suppress server log noise

            do_GET    = _respond
            do_POST   = _respond
            do_PUT    = _respond
            do_DELETE = _respond
            do_PATCH  = _respond

        self._server = HTTPServer(("127.0.0.1", self.port), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True, name=f"broken-impl-{self.port}"
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
            self._thread = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


class AdversarialSelfPlay:
    """
    Validates candidate tests via adversarial self-play:

      1. Run test against correct_mock_url  → must PASS
      2. Run test against broken_mock_url   → must FAIL
      3. If test passes both               → tautological → kill

    Tracks kill rate across the session for reporting.
    """

    def __init__(self) -> None:
        self._log: list[bool] = []   # True = tautological (killed)

    def mobile_gate(self, app_id: str, platform: str, flows: list[dict]) -> dict:
        from cherenkov.sources.mobile.contracts import MobileFlow

        passed = 0
        failed = 0

        for flow_data in flows:
            flow = MobileFlow(
                flow_id=flow_data.get("flow_id", "unknown"),
                name=flow_data.get("name", "unnamed"),
                screens=flow_data.get("screens", []),
                actions=flow_data.get("actions", []),
            )
            # Validate flow structure
            if flow.screens and flow.actions:
                passed += 1
            else:
                failed += 1

        total = passed + failed
        return {
            "app_id": app_id,
            "platform": platform,
            "flows": len(flows),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "gate_status": "passed" if failed == 0 else "blocked",
        }

    def validate(
        self,
        test_id: str,
        run_test: Callable[[str], tuple[bool, str]],
        correct_mock_url: str,
        broken_mock_url: str,
    ) -> SelfPlayResult:
        """
        Args:
            test_id:          Identifier for the candidate test (for reporting).
            run_test:         callable(base_url: str) → (passed: bool, output: str)
                              Return True if the test suite passed, False if it failed.
            correct_mock_url: Base URL of a spec-conforming mock (e.g. Prism).
            broken_mock_url:  Base URL of a deliberately-broken server.

        Returns:
            SelfPlayResult — check .tautological to decide whether to kill the test.
        """
        passed_correct, correct_out = run_test(correct_mock_url)
        passed_broken,  broken_out  = run_test(broken_mock_url)

        failed_broken = not passed_broken   # we WANT the test to fail on a broken impl

        tautological = passed_correct and not failed_broken

        result = SelfPlayResult(
            test_id=test_id,
            passed_correct=passed_correct,
            failed_broken=failed_broken,
            tautological=tautological,
            kill_reason=(
                "Test passes both the correct mock and the broken implementation "
                "— assertions are vacuous (tautological)"
                if tautological
                else ""
            ),
            correct_mock_output=correct_out,
            broken_impl_output=broken_out,
        )
        self._log.append(tautological)
        return result

    def kill_rate(self) -> float:
        """Fraction of validated tests that were killed as tautological."""
        if not self._log:
            return 0.0
        return sum(self._log) / len(self._log)

    def report(self) -> str:
        """One-line summary of self-play session."""
        total  = len(self._log)
        killed = sum(self._log)
        rate   = self.kill_rate()
        return (
            f"Self-play: {total} tests evaluated, "
            f"{killed} killed (tautological), "
            f"kill rate={rate:.1%}"
        )
