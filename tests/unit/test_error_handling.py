import unittest
from cherenkov.core.error_handling import (
    GracefulDegradation, DegradationLevel, HealthStatus, get_degradation
)


class TestDegradationLevel(unittest.TestCase):
    def test_levels(self):
        self.assertIn(DegradationLevel.HEALTHY, DegradationLevel)
        self.assertIn(DegradationLevel.DEGRADED, DegradationLevel)
        self.assertIn(DegradationLevel.CRITICAL, DegradationLevel)
        self.assertIn(DegradationLevel.DOWN, DegradationLevel)


class TestHealthStatus(unittest.TestCase):
    def test_starts_healthy(self):
        h = HealthStatus()
        self.assertEqual(h.level, DegradationLevel.HEALTHY)

    def test_update_all_pass(self):
        h = HealthStatus()
        h.update("ollama", True)
        h.update("redis", True)
        self.assertEqual(h.level, DegradationLevel.HEALTHY)

    def test_update_half_fail(self):
        h = HealthStatus()
        h.update("ollama", True)
        h.update("redis", False)
        self.assertEqual(h.level, DegradationLevel.DEGRADED)

    def test_update_all_fail(self):
        h = HealthStatus()
        h.update("ollama", False)
        h.update("redis", False)
        self.assertEqual(h.level, DegradationLevel.DOWN)

    def test_to_dict(self):
        h = HealthStatus()
        h.update("ollama", True)
        d = h.to_dict()
        self.assertIn("level", d)
        self.assertIn("checks", d)
        self.assertIn("last_checked", d)
        self.assertTrue(d["checks"]["ollama"])


class TestGracefulDegradation(unittest.TestCase):
    def test_singleton(self):
        gd1 = get_degradation()
        gd2 = get_degradation()
        self.assertIs(gd1, gd2)

    def test_initial_healthy(self):
        gd = GracefulDegradation()
        self.assertFalse(gd.degraded_or_worse())
        self.assertFalse(gd.critical_or_worse())

    def test_check_success(self):
        gd = GracefulDegradation()
        ok = gd.check("test", lambda: True)
        self.assertTrue(ok)
        self.assertFalse(gd.degraded_or_worse())

    def test_check_failure(self):
        gd = GracefulDegradation()
        ok = gd.check("test", lambda: False)
        self.assertFalse(ok)
        self.assertTrue(gd.degraded_or_worse())

    def test_check_exception(self):
        gd = GracefulDegradation()
        ok = gd.check("test", lambda: (_ for _ in ()).throw(Exception("fail")))
        self.assertFalse(ok)

    def test_wrap_degraded_blocks(self):
        gd = GracefulDegradation()
        gd.check("vital", lambda: False)
        gd.check("other", lambda: False)
        wrapped = gd.wrap("blocked", lambda: "called")
        self.assertIsNone(wrapped())

    def test_wrap_healthy_passes(self):
        gd = GracefulDegradation()
        wrapped = gd.wrap("ok", lambda: "called")
        self.assertEqual(wrapped(), "called")
