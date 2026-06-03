"""
test_copilot_e10.py — Unit tests for Epoch 10 (Explorer + Copilot v1).

Covers:
  E10-1  Explorer — HTTP crawl classification + findings → hypotheses
  E10-2  IntentAuthor — NL-intent parse (mocked router) + Playwright emission
  E10-3  SecondPairOfEyes — risk digest assembly + ranking
  E10-4  Triage — FailureClass → bug|flaky|env|intended mapping

All model calls are mocked; no network, no browser, no Ollama required.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from cherenkov.core.contracts import (
    DivergenceClass,
    ExplorerFinding,
    ExplorerFindingKind,
    ReasoningResult,
    Severity,
    Status,
    TriageCategory,
)
from cherenkov.divergence.explorer import Explorer
from cherenkov.copilot.intent import IntentAuthor
from cherenkov.copilot.digest import SecondPairOfEyes
from cherenkov.copilot.triage import Triage, render_triage
from cherenkov.healing.diagnose import FailureClass


def _result(content) -> ReasoningResult:
    return ReasoningResult(content=content, provider="mock", model="mock-model")


# ═══════════════════════════════════════════════════════════════════════════
# E10-1  Explorer
# ═══════════════════════════════════════════════════════════════════════════

class TestExplorer(unittest.TestCase):

    def _probe_map(self, mapping):
        """Build an http_probe that returns canned (status, latency, body) per URL suffix."""
        def probe(url, method):
            for suffix, val in mapping.items():
                if url.endswith(suffix):
                    return val
            return 200, 10, "ok"
        return probe

    def test_5xx_is_critical_server_error(self):
        ex = Explorer(base_url="http://app", http_probe=self._probe_map({"/boom": (500, 12, "stack")}))
        findings = ex.crawl(["/boom"])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, ExplorerFindingKind.SERVER_ERROR)
        self.assertEqual(findings[0].severity, Severity.CRITICAL)
        self.assertEqual(findings[0].status, 500)

    def test_unreachable_when_no_status(self):
        ex = Explorer(base_url="http://app", http_probe=self._probe_map({"/x": (None, 0, "refused")}))
        findings = ex.crawl(["/x"])
        self.assertEqual(findings[0].kind, ExplorerFindingKind.UNREACHABLE)
        self.assertEqual(findings[0].severity, Severity.HIGH)

    def test_unexpected_status_flagged_against_expected(self):
        ex = Explorer(base_url="http://app", http_probe=self._probe_map({"/p": (404, 8, "")}))
        findings = ex.crawl(["/p"], expected_status=200)
        kinds = {f.kind for f in findings}
        self.assertIn(ExplorerFindingKind.CLIENT_ERROR, kinds)

    def test_slow_response_finding(self):
        ex = Explorer(base_url="http://app", slow_ms=100,
                      http_probe=self._probe_map({"/slow": (200, 5000, "")}))
        findings = ex.crawl(["/slow"])
        self.assertTrue(any(f.kind == ExplorerFindingKind.SLOW_RESPONSE for f in findings))

    def test_clean_200_yields_no_findings(self):
        ex = Explorer(base_url="http://app", http_probe=self._probe_map({}))
        self.assertEqual(ex.crawl(["/ok"]), [])

    def test_findings_become_hypotheses_with_classes(self):
        ex = Explorer(base_url="http://app")
        findings = [
            ExplorerFinding(id="1", kind=ExplorerFindingKind.SERVER_ERROR, url="http://app/a", status=500),
            ExplorerFinding(id="2", kind=ExplorerFindingKind.CLIENT_ERROR, url="http://app/b", status=404),
            ExplorerFinding(id="3", kind=ExplorerFindingKind.JS_ERROR, url="http://app/c"),
        ]
        hyps = ex.to_hypotheses(findings)
        self.assertEqual(len(hyps), 3)
        self.assertEqual(hyps[0].divergence_class, DivergenceClass.D2_CODE_PROD)
        self.assertEqual(hyps[1].divergence_class, DivergenceClass.D5_SPEC_PROD)
        self.assertEqual(hyps[2].divergence_class, DivergenceClass.D3_UI_SPEC)
        self.assertTrue(all(h.repro_steps for h in hyps))

    def test_ui_probe_injected(self):
        def ui_probe(url):
            return [(ExplorerFindingKind.JS_ERROR, "Uncaught TypeError", "x is undefined")]
        ex = Explorer(base_url="http://app",
                      http_probe=self._probe_map({}), ui_probe=ui_probe)
        findings = ex.crawl(["/page"])
        self.assertTrue(any(f.kind == ExplorerFindingKind.JS_ERROR for f in findings))

    def test_ui_probe_exception_does_not_crash_crawl(self):
        def bad(url):
            raise RuntimeError("browser died")
        ex = Explorer(base_url="http://app", http_probe=self._probe_map({}), ui_probe=bad)
        # 200 OK + failing ui probe → no findings, no exception
        self.assertEqual(ex.crawl(["/page"]), [])


# ═══════════════════════════════════════════════════════════════════════════
# E10-2  IntentAuthor
# ═══════════════════════════════════════════════════════════════════════════

class TestIntentAuthor(unittest.TestCase):

    def _router_returning(self, payload):
        r = MagicMock()
        r.route.return_value = _result(payload)
        return r

    def test_parse_structured_intent(self):
        payload = {
            "title": "Guest checkout with discount",
            "kind": "ui",
            "target_url": "http://shop",
            "data_hints": {"discount_code": "SAVE10"},
            "steps": [
                {"action": "navigate", "value": "http://shop/cart"},
                {"action": "fill", "target": "the Discount field", "value": "SAVE10"},
                {"action": "click", "target": "the Checkout button"},
                {"action": "expect", "value": "Order confirmed"},
            ],
        }
        author = IntentAuthor(router=self._router_returning(payload))
        spec = author.parse("check guest checkout with a discount", target_url="http://shop")
        self.assertEqual(spec.title, "Guest checkout with discount")
        self.assertEqual(len(spec.steps), 4)
        self.assertEqual(spec.data_hints["discount_code"], "SAVE10")
        self.assertEqual(spec.status, Status.OK)

    def test_parse_falls_back_when_router_raises(self):
        r = MagicMock()
        r.route.side_effect = RuntimeError("no model")
        author = IntentAuthor(router=r)
        spec = author.parse("do a smoke test", target_url="http://x")
        self.assertEqual(spec.status, Status.DEGRADED)
        self.assertTrue(spec.steps)  # still runnable

    def test_playwright_is_selector_free_and_uses_roles(self):
        payload = {
            "title": "Login flow",
            "kind": "ui",
            "steps": [
                {"action": "navigate", "value": "http://x/login"},
                {"action": "fill", "target": "the Email field", "value": "a@b.com"},
                {"action": "click", "target": "the Sign In button"},
                {"action": "expect", "value": "Welcome"},
            ],
        }
        author = IntentAuthor(router=self._router_returning(payload))
        spec = author.parse("log in", target_url="http://x")
        code = author.to_playwright(spec)
        self.assertIn('import { test, expect } from "@playwright/test"', code)
        self.assertIn("getByRole(\"button\"", code)
        self.assertIn("getByLabel", code)
        self.assertIn("getByText(\"Welcome\")", code)
        # no raw CSS/XPath selectors authored by a human
        self.assertNotIn("page.locator(", code)
        self.assertNotIn("xpath=", code)
        self.assertNotIn("css=", code)

    def test_author_writes_ejectable_file(self):
        payload = {"title": "Smoke", "kind": "ui",
                   "steps": [{"action": "navigate", "value": "http://x"}]}
        author = IntentAuthor(router=self._router_returning(payload))
        with tempfile.TemporaryDirectory() as d:
            spec, path = author.author("smoke test", output_dir=d, target_url="http://x")
            self.assertTrue(path.exists())
            self.assertTrue(path.name.endswith(".spec.ts"))
            text = path.read_text()
            self.assertIn("page.goto", text)
            # ejectable: no CHERENKOV runtime imports/requires (comments are fine)
            self.assertNotIn('from "cherenkov', text)
            self.assertNotIn("require(", text)
            self.assertNotIn("import cherenkov", text)


# ═══════════════════════════════════════════════════════════════════════════
# E10-3  SecondPairOfEyes
# ═══════════════════════════════════════════════════════════════════════════

class TestSecondPairOfEyes(unittest.TestCase):

    def test_digest_ranks_critical_first(self):
        findings = [
            ExplorerFinding(id="1", kind=ExplorerFindingKind.SLOW_RESPONSE,
                            url="http://app/slow", severity=Severity.LOW),
            ExplorerFinding(id="2", kind=ExplorerFindingKind.SERVER_ERROR,
                            url="http://app/boom", severity=Severity.CRITICAL),
        ]
        digest = SecondPairOfEyes().build("http://app", findings=findings)
        self.assertEqual(len(digest.items), 2)
        self.assertEqual(digest.items[0].severity, Severity.CRITICAL)
        self.assertGreater(digest.items[0].score, digest.items[1].score)

    def test_digest_empty_renders_cleanly(self):
        digest = SecondPairOfEyes().build("http://app")
        self.assertEqual(digest.items, [])
        self.assertIn("nothing notable", digest.render())

    def test_reflector_rerank_and_idioms_are_used(self):
        reflector = MagicMock()
        # rerank returns hypotheses unchanged; idioms add a prior
        reflector.rerank.side_effect = lambda h, endpoint=None: h
        idiom = MagicMock(pattern="tenant isolation on list endpoints",
                          decay_score=0.9, confirm_count=3, endpoint="GET /list")
        reflector.get_top_idioms.return_value = [idiom]
        digest = SecondPairOfEyes(reflector=reflector).build(
            "http://app",
            findings=[ExplorerFinding(id="1", kind=ExplorerFindingKind.SERVER_ERROR,
                                      url="http://app/x", severity=Severity.HIGH)],
        )
        sources = {it.source for it in digest.items}
        self.assertIn("idiom", sources)
        self.assertIn("explorer", sources)


# ═══════════════════════════════════════════════════════════════════════════
# E10-4  Triage
# ═══════════════════════════════════════════════════════════════════════════

class TestTriage(unittest.TestCase):

    def test_mapping_covers_all_classes(self):
        t = Triage()
        cases = {
            FailureClass.AUTH_EXPIRY: TriageCategory.ENV,
            FailureClass.STATE_SEQUENCE: TriageCategory.ENV,
            FailureClass.FLAKY_SUCCESS: TriageCategory.FLAKY,
            FailureClass.CONTRACT_DRIFT: TriageCategory.BUG,
            FailureClass.DETERMINISTIC_FAILURE: TriageCategory.BUG,
            FailureClass.GENERIC_FAILURE: TriageCategory.BUG,
        }
        for fc, expected in cases.items():
            res = t.triage("s1", fc)
            self.assertEqual(res.category, expected, f"{fc} -> {res.category}")
            self.assertTrue(res.suggested_action)

    def test_retry_pass_forces_flaky(self):
        t = Triage()
        res = t.triage("s1", FailureClass.DETERMINISTIC_FAILURE, retried_pass=True)
        self.assertEqual(res.category, TriageCategory.FLAKY)
        self.assertGreater(res.confidence, 0.9)

    def test_reflector_nudges_bug_to_intended(self):
        reflector = MagicMock()
        reflector.idioms_for.return_value = [MagicMock(pattern="intended drift accepted")]
        t = Triage(reflector=reflector)
        res = t.triage("s1", FailureClass.CONTRACT_DRIFT, endpoint="GET /x")
        self.assertEqual(res.category, TriageCategory.INTENDED)

    def test_from_diagnosis_and_render(self):
        t = Triage()
        diag = MagicMock(failure_class=FailureClass.AUTH_EXPIRY, detail="401 now")
        res = t.from_diagnosis("s2", diag)
        self.assertEqual(res.category, TriageCategory.ENV)
        out = render_triage([res])
        self.assertIn("ENV", out)


if __name__ == "__main__":
    unittest.main()
