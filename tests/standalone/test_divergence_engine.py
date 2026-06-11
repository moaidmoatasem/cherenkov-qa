"""
test_divergence_engine.py — Unit tests for the Epoch 3 Divergence Engine.

Covers:
  E3-4  contracts (DivergenceReport round-trip, render)
  E3-1  SkepticAgent (hypothesis parsing, schema enforcement)
  E3-2  WitnessAgent (repro_steps parsing, divergence detection, batch)
  E3-3  AdversarialSelfPlay (kill logic, kill rate, BrokenImplServer)
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceEvidence,
    DivergenceHypothesis,
    DivergenceReport,
    ReasoningResult,
    ReproductionResult,
    Severity,
    StageMeta,
    Status,
)
from cherenkov.divergence.skeptic import SkepticAgent
from cherenkov.divergence.witness import WitnessAgent, _parse_repro_steps, _diff
from cherenkov.divergence.self_play import AdversarialSelfPlay, BrokenImplServer


# ── fixtures ──────────────────────────────────────────────────────────────

def _make_hypothesis(
    divergence_class: DivergenceClass = DivergenceClass.D1_SPEC_CODE,
    severity: Severity = Severity.MEDIUM,
    repro_steps: list[str] | None = None,
) -> DivergenceHypothesis:
    return DivergenceHypothesis(
        id="test-id-001",
        divergence_class=divergence_class,
        claim_a="spec: field X is required",
        claim_b="server accepts missing field X",
        predicted_evidence="POST without X returns 200 instead of 422",
        severity=severity,
        endpoint="POST /pet",
        repro_steps=repro_steps if repro_steps is not None else [
            "Send POST /pet with body {}",
            "Expect 422 response",
        ],
    )


def _make_evidence() -> DivergenceEvidence:
    return DivergenceEvidence(
        request_summary="POST http://example.com/pet → 200 (42ms)",
        response_actual={"id": 1, "name": "test"},
        response_expected={"error": "required field missing"},
        diff='status mismatch: expected=422, actual=200',
    )


# ═══════════════════════════════════════════════════════════════════════════
# E3-4  Contracts
# ═══════════════════════════════════════════════════════════════════════════

class TestDivergenceContracts(unittest.TestCase):

    def test_hypothesis_round_trip(self):
        h = _make_hypothesis()
        data = h.model_dump()
        h2 = DivergenceHypothesis(**data)
        self.assertEqual(h.id, h2.id)
        self.assertEqual(h.divergence_class, h2.divergence_class)

    def test_report_round_trip(self):
        report = DivergenceReport(
            id="report-001",
            divergence_class=DivergenceClass.D5_SPEC_PROD,
            claim_a="spec has endpoint",
            claim_b="prod does not",
            evidence=_make_evidence(),
            repro_steps=["step1", "step2"],
            severity=Severity.HIGH,
            endpoint="GET /pet/{petId}",
            metadata=StageMeta(stage="divergence_engine"),
        )
        payload = report.model_dump_json()
        report2 = DivergenceReport.model_validate_json(payload)
        self.assertEqual(report.id, report2.id)
        self.assertEqual(report.divergence_class, report2.divergence_class)
        self.assertEqual(report.severity, report2.severity)

    def test_report_render_contains_key_fields(self):
        report = DivergenceReport(
            id="r-002",
            divergence_class=DivergenceClass.D1_SPEC_CODE,
            claim_a="spec requires photoUrls",
            claim_b="server ignores missing photoUrls",
            evidence=_make_evidence(),
            repro_steps=["Send POST /pet without photoUrls", "Expect 422"],
            severity=Severity.HIGH,
            endpoint="POST /pet",
            metadata=StageMeta(stage="divergence_engine"),
        )
        rendered = report.render()
        self.assertIn("D1_spec_code", rendered)
        self.assertIn("POST /pet", rendered)
        self.assertIn("spec requires photoUrls", rendered)
        self.assertIn("server ignores missing photoUrls", rendered)
        self.assertIn("Send POST /pet without photoUrls", rendered)

    def test_divergence_class_enum_has_five_values(self):
        values = {c.value for c in DivergenceClass}
        self.assertSetEqual(
            values,
            {"D1_spec_code", "D2_code_prod", "D3_ui_spec", "D4_db_code", "D5_spec_prod"},
        )

    def test_reproduction_result_without_evidence(self):
        result = ReproductionResult(
            hypothesis_id="h-001",
            reproduced=False,
            rejection_reason="No divergence observed",
        )
        self.assertFalse(result.reproduced)
        self.assertIsNone(result.evidence)
        self.assertEqual(result.rejection_reason, "No divergence observed")

    def test_reproduction_result_with_evidence(self):
        result = ReproductionResult(
            hypothesis_id="h-002",
            reproduced=True,
            evidence=_make_evidence(),
        )
        self.assertTrue(result.reproduced)
        self.assertIsNotNone(result.evidence)


# ═══════════════════════════════════════════════════════════════════════════
# E3-1  SkepticAgent
# ═══════════════════════════════════════════════════════════════════════════

class TestSkepticAgent(unittest.TestCase):

    def _make_router_mock(self, response_content: str | dict) -> MagicMock:
        mock_router = MagicMock()
        mock_router.route.return_value = ReasoningResult(
            content=response_content,
            provider="ollama",
            model="deepseek-r1:8b",
            cost_usd=0.0,
            latency_ms=100,
        )
        return mock_router

    def test_hypothesise_parses_valid_response(self):
        payload = {
            "hypotheses": [
                {
                    "divergence_class": "D1_spec_code",
                    "claim_a": "spec: photoUrls required",
                    "claim_b": "server accepts missing photoUrls",
                    "predicted_evidence": "POST without photoUrls → 200",
                    "severity": "high",
                    "endpoint": "POST /pet",
                    "repro_steps": ["Send POST /pet without photoUrls", "Expect 422"],
                }
            ]
        }
        agent = SkepticAgent(router=self._make_router_mock(json.dumps(payload)))
        result = agent.hypothesise("/pet", "POST", {"summary": "Add a new pet"})

        self.assertEqual(len(result), 1)
        h = result[0]
        self.assertEqual(h.divergence_class, DivergenceClass.D1_SPEC_CODE)
        self.assertEqual(h.severity, Severity.HIGH)
        self.assertEqual(h.claim_a, "spec: photoUrls required")
        self.assertIsInstance(h.id, str)

    def test_hypothesise_parses_dict_content(self):
        """Router may return a dict directly (structured JSON mode)."""
        payload = {
            "hypotheses": [
                {
                    "divergence_class": "D5_spec_prod",
                    "claim_a": "spec has endpoint",
                    "claim_b": "prod returns 404",
                    "predicted_evidence": "GET /old → 404",
                    "severity": "medium",
                    "repro_steps": ["GET /old", "Expect 200"],
                }
            ]
        }
        agent = SkepticAgent(router=self._make_router_mock(payload))
        result = agent.hypothesise("/old", "GET", {})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].divergence_class, DivergenceClass.D5_SPEC_PROD)

    def test_hypothesise_returns_empty_on_invalid_json(self):
        agent = SkepticAgent(router=self._make_router_mock("not json at all"))
        result = agent.hypothesise("/pet", "GET", {})
        self.assertEqual(result, [])

    def test_hypothesise_skips_malformed_items(self):
        payload = {
            "hypotheses": [
                {"divergence_class": "INVALID_CLASS", "claim_a": "x", "claim_b": "y"},
                {
                    "divergence_class": "D2_code_prod",
                    "claim_a": "code does X",
                    "claim_b": "prod returns Y",
                    "predicted_evidence": "GET /thing → unexpected",
                    "severity": "low",
                    "repro_steps": ["GET /thing"],
                },
            ]
        }
        agent = SkepticAgent(router=self._make_router_mock(payload))
        result = agent.hypothesise("/thing", "GET", {})

        # First item skipped (invalid class), second parsed
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].divergence_class, DivergenceClass.D2_CODE_PROD)

    def test_uses_deep_tier_reasoning_request(self):
        mock_router = MagicMock()
        mock_router.route.return_value = ReasoningResult(
            content=json.dumps({"hypotheses": []}),
            provider="ollama",
            model="deepseek-r1:8b",
        )
        agent = SkepticAgent(router=mock_router)
        agent.hypothesise("/test", "GET", {})

        call_args = mock_router.route.call_args[0][0]
        self.assertEqual(call_args.capability_tier, "deep")
        self.assertIsNotNone(call_args.output_schema)

    def test_build_task_contains_endpoint_and_method(self):
        mock_router = MagicMock()
        mock_router.route.return_value = ReasoningResult(
            content=json.dumps({"hypotheses": []}),
            provider="ollama",
            model="test",
        )
        agent = SkepticAgent(router=mock_router)
        agent.hypothesise("/pet/{petId}", "DELETE", {"summary": "Delete a pet"})

        task_text = mock_router.route.call_args[0][0].task
        self.assertIn("/pet/{petId}", task_text)
        self.assertIn("DELETE", task_text)


# ═══════════════════════════════════════════════════════════════════════════
# E3-2  WitnessAgent — helpers
# ═══════════════════════════════════════════════════════════════════════════

class TestParseReproSteps(unittest.TestCase):

    def test_parses_get_with_path(self):
        steps = ["Send GET /pet/findByStatus?status=available", "Expect 200"]
        method, path, payload, expected = _parse_repro_steps(steps)
        self.assertEqual(method, "GET")
        self.assertTrue(path.startswith("/pet/findByStatus"))
        self.assertIsNone(payload)
        self.assertEqual(expected, 200)

    def test_parses_post_with_json_body(self):
        steps = ['Send POST /pet with body {"name": "test", "photoUrls": []}', "Expect 200"]
        method, path, payload, expected = _parse_repro_steps(steps)
        self.assertEqual(method, "POST")
        self.assertEqual(path, "/pet")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["name"], "test")

    def test_parses_expected_404(self):
        steps = ["GET /pet/99999999", "Assert 404 response"]
        _, _, _, expected = _parse_repro_steps(steps)
        self.assertEqual(expected, 404)

    def test_defaults_to_get_slash(self):
        method, path, payload, expected = _parse_repro_steps([])
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/")
        self.assertIsNone(payload)
        self.assertIsNone(expected)


class TestDiff(unittest.TestCase):

    def test_status_mismatch(self):
        result = _diff({"error": "not found"}, 200, 404)
        self.assertIn("200", result)
        self.assertIn("404", result)

    def test_status_match(self):
        result = _diff({"ok": True}, 200, 200)
        self.assertEqual(result, "no structural diff")

    def test_dict_missing_keys(self):
        actual = {"id": 1}
        expected = {"id": 1, "name": "test"}
        result = _diff(actual, expected, 200)
        self.assertIn("missing keys", result)
        self.assertIn("name", result)

    def test_dict_value_mismatch(self):
        actual = {"status": "sold"}
        expected = {"status": "available"}
        result = _diff(actual, expected, 200)
        self.assertIn("status", result)
        self.assertIn("sold", result)
        self.assertIn("available", result)

    def test_no_diff_identical_dicts(self):
        result = _diff({"a": 1}, {"a": 1}, 200)
        self.assertEqual(result, "no structural diff")


class TestWitnessAgent(unittest.TestCase):

    def test_reproduce_rejects_when_no_repro_steps(self):
        agent = WitnessAgent(base_url="http://localhost:9999")
        h = _make_hypothesis(repro_steps=[])
        result = agent.reproduce(h)
        self.assertFalse(result.reproduced)
        self.assertIn("No repro_steps", result.rejection_reason)

    def test_reproduce_rejects_on_connection_error(self):
        agent = WitnessAgent(base_url="http://127.0.0.1:19876", timeout=0.1)
        h = _make_hypothesis(repro_steps=["Send GET /pet/1", "Expect 200"])
        result = agent.reproduce(h)
        self.assertFalse(result.reproduced)
        self.assertIn("Execution error", result.rejection_reason)

    def test_reproduce_batch_returns_one_per_hypothesis(self):
        agent = WitnessAgent(base_url="http://127.0.0.1:19876", timeout=0.1)
        hypotheses = [
            _make_hypothesis(repro_steps=["GET /pet/1", "Expect 200"]),
            _make_hypothesis(repro_steps=["GET /pet/2", "Expect 200"]),
        ]
        results = agent.reproduce_batch(hypotheses)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].hypothesis_id, hypotheses[0].id)
        self.assertEqual(results[1].hypothesis_id, hypotheses[1].id)

    def test_reproduce_confirmed_when_diff_non_empty(self):
        """Use BrokenImplServer to give the Witness a real server to call."""
        import time
        responses = {"/pet/1": (200, {"id": 1, "name": "fluffy"})}
        with BrokenImplServer(port=19990, responses=responses) as server:
            time.sleep(0.05)   # ensure serve_forever() is running
            agent = WitnessAgent(base_url=server.url)
            h = DivergenceHypothesis(
                id="h-live",
                divergence_class=DivergenceClass.D1_SPEC_CODE,
                claim_a="spec says GET /pet/1 returns 404",
                claim_b="server returns 200 with data",
                predicted_evidence="200 instead of expected 404",
                severity=Severity.HIGH,
                endpoint="GET /pet/1",
                repro_steps=["Send GET /pet/1", "Expect 404 response"],
            )
            result = agent.reproduce(h)
            # The server returns 200 but we expected 404 → divergence confirmed
            self.assertTrue(result.reproduced, msg=f"rejection_reason={result.rejection_reason}")
            self.assertIsNotNone(result.evidence)
            self.assertIn("200", result.evidence.request_summary)


# ═══════════════════════════════════════════════════════════════════════════
# E3-3  AdversarialSelfPlay + BrokenImplServer
# ═══════════════════════════════════════════════════════════════════════════

class TestBrokenImplServer(unittest.TestCase):

    def test_serves_configured_responses(self):
        import httpx
        responses = {"/pet/1": (404, {"error": "deleted"})}
        with BrokenImplServer(port=19991, responses=responses) as server:
            resp = httpx.get(f"{server.url}/pet/1")
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.json(), {"error": "deleted"})

    def test_serves_default_for_unknown_path(self):
        import httpx
        with BrokenImplServer(port=19992, responses={}) as server:
            resp = httpx.get(f"{server.url}/unknown/path")
            self.assertEqual(resp.status_code, 500)

    def test_all_verbs_work(self):
        import httpx
        responses = {"/x": (200, {"ok": True})}
        with BrokenImplServer(port=19993, responses=responses) as server:
            for method in ("get", "post", "put", "delete", "patch"):
                resp = getattr(httpx, method)(f"{server.url}/x")
                self.assertEqual(resp.status_code, 200)

    def test_url_property(self):
        server = BrokenImplServer(port=19994, responses={})
        self.assertEqual(server.url, "http://127.0.0.1:19994")


class TestAdversarialSelfPlay(unittest.TestCase):

    def test_tautological_test_is_killed(self):
        """A test that always passes — even against broken impl — is tautological."""
        always_pass = lambda url: (True, "ok")
        sp = AdversarialSelfPlay()
        result = sp.validate(
            test_id="always_pass",
            run_test=always_pass,
            correct_mock_url="http://unused-correct",
            broken_mock_url="http://unused-broken",
        )
        self.assertTrue(result.tautological)
        self.assertIn("tautological", result.kill_reason.lower())
        self.assertTrue(result.passed_correct)
        self.assertFalse(result.failed_broken)

    def test_good_test_is_not_killed(self):
        """A test that passes correct mock but fails broken impl is good."""
        def selective(url: str) -> tuple[bool, str]:
            return ("correct" in url, "output")

        sp = AdversarialSelfPlay()
        result = sp.validate(
            test_id="good_test",
            run_test=selective,
            correct_mock_url="http://correct-server",
            broken_mock_url="http://broken-server",
        )
        self.assertFalse(result.tautological)
        self.assertTrue(result.passed_correct)
        self.assertTrue(result.failed_broken)
        self.assertEqual(result.kill_reason, "")

    def test_test_that_always_fails_is_not_tautological_but_useless(self):
        """A test that fails even the correct mock is broken, not tautological."""
        always_fail = lambda url: (False, "failed")
        sp = AdversarialSelfPlay()
        result = sp.validate(
            test_id="always_fail",
            run_test=always_fail,
            correct_mock_url="http://correct",
            broken_mock_url="http://broken",
        )
        self.assertFalse(result.tautological)
        self.assertFalse(result.passed_correct)

    def test_kill_rate_zero_when_no_tautological(self):
        sp = AdversarialSelfPlay()
        selective = lambda url: ("correct" in url, "out")
        for _ in range(5):
            sp.validate("t", selective, "http://correct", "http://broken")
        self.assertEqual(sp.kill_rate(), 0.0)

    def test_kill_rate_one_when_all_tautological(self):
        sp = AdversarialSelfPlay()
        always_pass = lambda url: (True, "out")
        for _ in range(4):
            sp.validate("t", always_pass, "http://c", "http://b")
        self.assertEqual(sp.kill_rate(), 1.0)

    def test_kill_rate_partial(self):
        sp = AdversarialSelfPlay()
        always_pass = lambda url: (True, "out")
        selective   = lambda url: ("c" in url, "out")

        sp.validate("taut",  always_pass, "http://c", "http://b")   # killed
        sp.validate("good1", selective,   "http://c", "http://b")   # kept
        sp.validate("good2", selective,   "http://c", "http://b")   # kept
        sp.validate("taut2", always_pass, "http://c", "http://b")   # killed

        self.assertAlmostEqual(sp.kill_rate(), 0.5)

    def test_report_string(self):
        sp = AdversarialSelfPlay()
        always_pass = lambda url: (True, "out")
        sp.validate("t", always_pass, "http://c", "http://b")
        report = sp.report()
        self.assertIn("1 tests evaluated", report)
        self.assertIn("1 killed", report)
        self.assertIn("100.0%", report)

    def test_kill_rate_zero_when_empty(self):
        sp = AdversarialSelfPlay()
        self.assertEqual(sp.kill_rate(), 0.0)

    def test_self_play_with_real_server(self):
        """Integration test: BrokenImplServer + AdversarialSelfPlay together."""
        import httpx

        def run_test(base_url: str) -> tuple[bool, str]:
            """Test: GET /status must return 200 with {"ok": True}."""
            try:
                resp = httpx.get(f"{base_url}/status", timeout=2.0)
                body = resp.json()
                passed = resp.status_code == 200 and body.get("ok") is True
                return passed, f"status={resp.status_code}, body={body}"
            except Exception as e:
                return False, str(e)

        correct_responses   = {"/status": (200, {"ok": True})}
        broken_responses    = {"/status": (500, {"ok": False})}

        with BrokenImplServer(port=19995, responses=correct_responses) as correct_server, \
             BrokenImplServer(port=19996, responses=broken_responses)   as broken_server:

            sp = AdversarialSelfPlay()
            result = sp.validate(
                test_id="real_server_test",
                run_test=run_test,
                correct_mock_url=correct_server.url,
                broken_mock_url=broken_server.url,
            )

        self.assertFalse(result.tautological)
        self.assertTrue(result.passed_correct)
        self.assertTrue(result.failed_broken)


if __name__ == "__main__":
    unittest.main()
