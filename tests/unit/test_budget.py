"""Unit tests for cherenkov/core/budget.py — cost budget enforcer."""

import os
import unittest
from cherenkov.core.budget import RunBudget, BudgetExceededError, get_run_budget, reset_run_budget


class TestRunBudgetBasics(unittest.TestCase):
    def test_initial_spent_is_zero(self):
        b = RunBudget(cap_usd=1.0)
        self.assertEqual(b.spent, 0.0)

    def test_charge_accumulates(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.05)
        b.charge(cost_usd=0.10)
        self.assertAlmostEqual(b.spent, 0.15)

    def test_remaining_decreases(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.30)
        self.assertAlmostEqual(b.remaining, 0.70, places=5)

    def test_no_cap_remaining_is_inf(self):
        b = RunBudget(cap_usd=None)
        self.assertEqual(b.remaining, float("inf"))

    def test_reset_clears_spend(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.50)
        b.reset()
        self.assertEqual(b.spent, 0.0)


class TestPreCheck(unittest.TestCase):
    def test_no_exception_when_under_cap(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.50)
        b.pre_check(0.40)  # 0.90 total < 1.00 cap

    def test_raises_when_request_would_exceed_cap(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.90)
        with self.assertRaises(BudgetExceededError) as ctx:
            b.pre_check(0.20)
        self.assertAlmostEqual(ctx.exception.spent, 0.90, places=4)
        self.assertAlmostEqual(ctx.exception.cap, 1.00, places=4)

    def test_exactly_at_cap_does_not_raise(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.90)
        b.pre_check(0.10)  # exactly 1.00 — should pass

    def test_no_cap_never_raises(self):
        b = RunBudget(cap_usd=None)
        b.charge(cost_usd=999.0)
        b.pre_check(999.0)  # unlimited


class TestWarnThreshold(unittest.TestCase):
    def test_warn_callback_fires_at_threshold(self):
        warned = []
        b = RunBudget(cap_usd=1.0, warn_fraction=0.80, on_warn=lambda s, c: warned.append((s, c)))
        b.charge(cost_usd=0.79)
        self.assertEqual(warned, [])
        b.charge(cost_usd=0.02)  # crosses 80%
        self.assertEqual(len(warned), 1)

    def test_warn_fires_only_once(self):
        warned = []
        b = RunBudget(cap_usd=1.0, warn_fraction=0.80, on_warn=lambda s, c: warned.append(s))
        for _ in range(5):
            b.charge(cost_usd=0.20)
        self.assertEqual(len(warned), 1)


class TestSummary(unittest.TestCase):
    def test_summary_structure(self):
        b = RunBudget(cap_usd=1.0)
        b.charge(cost_usd=0.10, tokens=500, model="gpt-4o-mini", provider="openai")
        b.charge(cost_usd=0.05, tokens=300, model="gpt-4o-mini", provider="openai", cache_hit=True)
        s = b.summary()
        self.assertAlmostEqual(s["spent_usd"], 0.15, places=5)
        self.assertEqual(s["total_requests"], 2)
        self.assertEqual(s["total_tokens"], 800)
        self.assertEqual(s["cache_hits"], 1)
        self.assertIn("openai/gpt-4o-mini", s["by_model"])
        self.assertEqual(s["by_model"]["openai/gpt-4o-mini"]["requests"], 2)

    def test_summary_no_cap(self):
        b = RunBudget()
        s = b.summary()
        self.assertIsNone(s["cap_usd"])
        self.assertIsNone(s["remaining_usd"])
        self.assertIsNone(s["utilization_pct"])


class TestEnvVar(unittest.TestCase):
    def setUp(self):
        os.environ.pop("CHERENKOV_BUDGET_USD", None)

    def tearDown(self):
        os.environ.pop("CHERENKOV_BUDGET_USD", None)

    def test_env_var_overrides_cap(self):
        os.environ["CHERENKOV_BUDGET_USD"] = "0.50"
        b = RunBudget(cap_usd=10.0)
        self.assertAlmostEqual(b.cap_usd, 0.50, places=5)


class TestProcessWideBudget(unittest.TestCase):
    def setUp(self):
        reset_run_budget()

    def test_get_run_budget_returns_same_instance(self):
        b1 = get_run_budget()
        b2 = get_run_budget()
        self.assertIs(b1, b2)

    def test_reset_replaces_instance(self):
        b1 = get_run_budget()
        reset_run_budget()
        b2 = get_run_budget()
        self.assertIsNot(b1, b2)


if __name__ == "__main__":
    unittest.main()
