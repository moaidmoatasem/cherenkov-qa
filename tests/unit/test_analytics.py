import unittest

from cherenkov.analytics.telemetry import InMemoryTelemetry


class TestInMemoryTelemetry(unittest.TestCase):
    def test_telemetry_aggregation(self):
        telemetry = InMemoryTelemetry()
        telemetry.record_endpoint_test(has_divergence=False, latency_ms=100.0)
        telemetry.record_endpoint_test(has_divergence=True, latency_ms=200.0)

        stats = telemetry.get_statistics()
        self.assertEqual(stats.endpoints_tested, 2)
        self.assertEqual(stats.divergence_count, 1)
        self.assertEqual(stats.divergence_rate, 0.5)
        self.assertEqual(stats.average_latency_ms, 150.0)

    def test_empty_telemetry(self):
        telemetry = InMemoryTelemetry()
        stats = telemetry.get_statistics()
        self.assertEqual(stats.endpoints_tested, 0)
        self.assertEqual(stats.divergence_count, 0)
        self.assertEqual(stats.divergence_rate, 0.0)
        self.assertEqual(stats.average_latency_ms, 0.0)

if __name__ == '__main__':
    unittest.main()
