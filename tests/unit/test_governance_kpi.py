"""Unit tests for cherenkov/governance/kpi.py — GovernanceKPI and GovernanceReport."""
import unittest


class TestGovernanceKPI(unittest.TestCase):
    def _make(self, **kwargs):
        from cherenkov.governance.kpi import GovernanceKPI
        return GovernanceKPI(**kwargs)

    def test_defaults_produce_valid_health_score(self):
        kpi = self._make()
        hs = kpi.health_score
        self.assertGreaterEqual(hs, 0.0)
        self.assertLessEqual(hs, 1.0)

    def test_perfect_kpi_gives_high_health_score(self):
        kpi = self._make(
            escape_rate=0.0,
            false_positive_rate=0.0,
            coverage=1.0,
            maintenance_score=1.0,
        )
        self.assertAlmostEqual(kpi.health_score, 1.0, places=3)

    def test_worst_case_kpi_gives_low_health_score(self):
        kpi = self._make(
            escape_rate=1.0,
            false_positive_rate=1.0,
            coverage=0.0,
            maintenance_score=0.0,
        )
        self.assertAlmostEqual(kpi.health_score, 0.0, places=3)

    def test_health_score_is_weighted_average(self):
        kpi = self._make(
            escape_rate=0.5,
            false_positive_rate=0.5,
            coverage=0.5,
            maintenance_score=0.5,
        )
        self.assertAlmostEqual(kpi.health_score, 0.5, places=3)

    def test_health_score_rounded_to_4_places(self):
        kpi = self._make(escape_rate=0.3333, coverage=0.6667, maintenance_score=0.5)
        hs = kpi.health_score
        self.assertEqual(hs, round(hs, 4))


class TestGovernanceReport(unittest.TestCase):
    def _make(self, **kpi_kwargs):
        from cherenkov.governance.kpi import GovernanceKPI, GovernanceReport
        return GovernanceReport(kpi=GovernanceKPI(**kpi_kwargs))

    def test_render_contains_health_score_label(self):
        report = self._make()
        text = report.render()
        self.assertIn("Health Score", text)
        self.assertIn("Escape Rate", text)
        self.assertIn("False Positive", text)
        self.assertIn("Coverage", text)

    def test_render_json_keys(self):
        report = self._make(total_tests=100, passed_tests=80, escaped_defects=2)
        j = report.render_json()
        for key in ("health_score", "escape_rate", "coverage", "total_tests", "passed_tests"):
            self.assertIn(key, j)
        self.assertEqual(j["total_tests"], 100)
        self.assertEqual(j["passed_tests"], 80)

    def test_render_json_history_count_zero_by_default(self):
        from cherenkov.governance.kpi import GovernanceReport
        report = GovernanceReport()
        self.assertEqual(report.render_json()["history_count"], 0)
