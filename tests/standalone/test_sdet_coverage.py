"""
test_sdet_coverage.py — unit tests for Epoch 11 Coverage SDET.

Covers:
  * MeaningfulAssertionGate (E11-2): meaningful / tautological / fails-correct.
  * CoverageLoop (E11-1): first-try coverage, repair path, bounded UNMET,
    early-exit at threshold, and gate-integrated tautology rejection.

All model/server/trace work is injected as fakes — no live Ollama/Prism/Playwright.
"""

import unittest

from cherenkov.core.contracts import CoverageItemState, Status
from cherenkov.sdet.assertion_gate import MeaningfulAssertionGate
from cherenkov.sdet.coverage_loop import CoverageLoop, RunOutcome

CORRECT = "http://correct.mock"
BROKEN = "http://broken.mock"


# ── E11-2: assertion gate ──────────────────────────────────────────────────
class TestMeaningfulAssertionGate(unittest.TestCase):
    def test_meaningful_when_passes_correct_and_fails_broken(self):
        gate = MeaningfulAssertionGate()
        # passes on correct, fails on broken → meaningful
        run = lambda url: (url == CORRECT, f"ran @ {url}")
        res = gate.evaluate("t1", run, CORRECT, BROKEN)
        self.assertTrue(res.meaningful)
        self.assertTrue(res.passed_correct)
        self.assertTrue(res.failed_broken)
        self.assertEqual(res.reason, "")

    def test_tautological_when_passes_both(self):
        gate = MeaningfulAssertionGate()
        run = lambda url: (True, "always passes")
        res = gate.evaluate("t2", run, CORRECT, BROKEN)
        self.assertFalse(res.meaningful)
        self.assertFalse(res.failed_broken)
        self.assertIn("vacuous", res.reason.lower())

    def test_not_meaningful_when_fails_correct(self):
        gate = MeaningfulAssertionGate()
        run = lambda url: (False, "always fails")
        res = gate.evaluate("t3", run, CORRECT, BROKEN)
        self.assertFalse(res.meaningful)
        self.assertIn("spec-conforming", res.reason)

    def test_kill_rate_accumulates(self):
        gate = MeaningfulAssertionGate()
        gate.evaluate("ok", lambda u: (u == CORRECT, ""), CORRECT, BROKEN)  # meaningful
        gate.evaluate("taut", lambda u: (True, ""), CORRECT, BROKEN)  # killed
        self.assertAlmostEqual(gate.kill_rate(), 0.5)
        self.assertIn("kill rate", gate.report())


# ── E11-1: coverage loop ───────────────────────────────────────────────────
class TestCoverageLoop(unittest.TestCase):
    def _loop(self, run_fn, repair_fn=None, **kw):
        gen = lambda t: {"id": t, "fixed": False}
        rep = repair_fn or (lambda t, a, o: a)
        return CoverageLoop(
            generate_fn=gen,
            run_fn=run_fn,
            repair_fn=rep,
            correct_mock_url=CORRECT,
            **kw,
        )

    def test_all_covered_first_try_no_gate(self):
        loop = self._loop(
            lambda a, url: RunOutcome(passed=True, exercised=True), threshold=1.0
        )
        report = loop.run(["a", "b", "c"])
        self.assertEqual(report.covered, 3)
        self.assertEqual(report.coverage, 1.0)
        self.assertTrue(report.threshold_met)
        self.assertEqual(report.status, Status.OK)
        self.assertTrue(all(i.attempts == 1 for i in report.items))

    def test_repair_path_reaches_coverage(self):
        # Fails until repaired; repair flips artifact["fixed"] → next run passes.
        def run_fn(artifact, url):
            return RunOutcome(passed=artifact["fixed"], exercised=True, output="boom")

        def repair_fn(target, artifact, outcome):
            artifact["fixed"] = True
            return artifact

        loop = self._loop(run_fn, repair_fn, threshold=1.0, max_repairs=2)
        report = loop.run(["a"])
        item = report.items[0]
        self.assertEqual(item.state, CoverageItemState.COVERED)
        self.assertEqual(item.attempts, 2)  # 1 generate + 1 repair

    def test_bounded_unmet_when_never_passes(self):
        loop = self._loop(
            lambda a, url: RunOutcome(passed=False, exercised=True, output="nope"),
            threshold=1.0,
            max_repairs=2,
        )
        report = loop.run(["a"])
        item = report.items[0]
        self.assertEqual(item.state, CoverageItemState.UNMET)
        self.assertEqual(item.attempts, 3)  # 1 generate + 2 repairs (bounded)
        self.assertEqual(report.status, Status.DEGRADED)

    def test_not_exercised_is_not_covered(self):
        loop = self._loop(
            lambda a, url: RunOutcome(passed=True, exercised=False),
            threshold=1.0,
            max_repairs=0,
        )
        report = loop.run(["a"])
        item = report.items[0]
        self.assertEqual(item.state, CoverageItemState.UNMET)
        self.assertIn("exercise", item.detail)

    def test_early_exit_at_threshold_leaves_pending(self):
        loop = self._loop(
            lambda a, url: RunOutcome(passed=True, exercised=True), threshold=0.5
        )
        report = loop.run(["a", "b", "c", "d"])
        self.assertTrue(report.threshold_met)
        self.assertEqual(report.covered, 2)  # stops once 2/4 == 0.5
        pending = [i for i in report.items if i.state == CoverageItemState.PENDING]
        self.assertEqual(len(pending), 2)

    def test_gate_rejects_tautological_test(self):
        # Test passes everywhere (tautological) → gate rejects → never covered.
        loop = self._loop(
            lambda a, url: RunOutcome(passed=True, exercised=True),
            threshold=1.0,
            broken_mock_url=BROKEN,
            max_repairs=1,
        )
        report = loop.run(["a"])
        item = report.items[0]
        self.assertEqual(item.state, CoverageItemState.UNMET)
        self.assertFalse(item.meaningful)

    def test_gate_accepts_meaningful_test(self):
        # Passes on correct, fails on broken → meaningful → covered.
        loop = self._loop(
            lambda a, url: RunOutcome(passed=(url == CORRECT), exercised=True),
            threshold=1.0,
            broken_mock_url=BROKEN,
            max_repairs=0,
        )
        report = loop.run(["a"])
        item = report.items[0]
        self.assertEqual(item.state, CoverageItemState.COVERED)
        self.assertTrue(item.meaningful)

    def test_invalid_threshold_raises(self):
        with self.assertRaises(ValueError):
            self._loop(lambda a, url: RunOutcome(passed=True), threshold=1.5)

    def test_invalid_max_repairs_raises(self):
        with self.assertRaises(ValueError):
            self._loop(lambda a, url: RunOutcome(passed=True), max_repairs=-1)

    def test_render_is_readable(self):
        loop = self._loop(
            lambda a, url: RunOutcome(passed=True, exercised=True), threshold=1.0
        )
        report = loop.run(["a"])
        text = report.render()
        self.assertIn("Coverage SDET", text)
        self.assertIn("covered", text)


if __name__ == "__main__":
    unittest.main()
