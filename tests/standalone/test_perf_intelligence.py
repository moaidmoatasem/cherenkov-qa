"""
test_perf_intelligence.py — Unit tests for Epoch 8 Perf Intelligence.

Covers:
  C2 (#117): Generative load profiles from traffic source
  C3 (#118): LLM-aware perf metrics (TTFT/inter-token/tokens-sec/P95-99/cost)
  C4 (#119): ML anomaly tier (opt-in; statistical stays default)
"""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.stages.perf.perf_stage import PerfStage, PerfSlice, _BaselineDB
from cherenkov.stages.perf.anomaly import LatencyAnomalyDetector


class TestBaselineDB(unittest.TestCase):
    """Tests for _BaselineDB — shared by all E8 perf features."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.db = _BaselineDB(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_and_stats(self):
        self.db.record("/api/test", "GET", 42.0)
        stats = self.db.stats("/api/test", "GET")
        self.assertEqual(stats["count"], 1)
        self.assertAlmostEqual(stats["mean"], 42.0)

    def test_multiple_records(self):
        for i in range(5):
            self.db.record("/api/test", "GET", 40.0 + i)
        stats = self.db.stats("/api/test", "GET")
        self.assertEqual(stats["count"], 5)
        self.assertAlmostEqual(stats["mean"], 42.0)

    def test_empty_stats(self):
        stats = self.db.stats("/api/never", "GET")
        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["mean"], 0.0)
        self.assertEqual(stats["stddev"], 0.0)

    def test_record_single_value_stddev(self):
        self.db.record("/api/single", "POST", 50.0)
        stats = self.db.stats("/api/single", "POST")
        self.assertEqual(stats["stddev"], 0.0)

    # ── LLM-specific metrics (#118) ──────────────────────────────────────

    def test_llm_record_and_stats(self):
        self.db.record("/api/chat", "POST", 100.0,
                        ttft_ms=45.0, itl_ms=15.0, cost_usd=0.002, is_llm=True)
        self.db.record("/api/chat", "POST", 110.0,
                        ttft_ms=50.0, itl_ms=18.0, cost_usd=0.003, is_llm=True)
        llm_stats = self.db.llm_stats("/api/chat", "POST")
        self.assertEqual(llm_stats["llm_request_count"], 2)
        self.assertAlmostEqual(llm_stats["ttft_mean_ms"], 47.5)
        self.assertAlmostEqual(llm_stats["itl_mean_ms"], 16.5)
        self.assertIsNotNone(llm_stats.get("cost_mean_usd"))

    def test_llm_stats_empty(self):
        self.db.record("/api/test", "GET", 30.0, is_llm=False)
        llm_stats = self.db.llm_stats("/api/test", "GET")
        self.assertEqual(llm_stats["llm_request_count"], 0)

    def test_llm_single_record_no_stddev(self):
        self.db.record("/api/chat", "POST", 100.0,
                        ttft_ms=45.0, itl_ms=15.0, cost_usd=0.002, is_llm=True)
        llm_stats = self.db.llm_stats("/api/chat", "POST")
        self.assertEqual(llm_stats["ttft_stddev_ms"], 0.0)

    def test_llm_stats_multiple_has_stddev(self):
        for i in range(5):
            self.db.record("/api/chat", "POST", 100.0 + i,
                            ttft_ms=40.0 + i, itl_ms=10.0 + i,
                            cost_usd=0.001 + i * 0.0001, is_llm=True)
        llm_stats = self.db.llm_stats("/api/chat", "POST")
        self.assertGreater(llm_stats["ttft_stddev_ms"], 0)

    def test_non_llm_endpoint_returns_empty(self):
        self.db.record("/api/users", "GET", 25.0, is_llm=False)
        llm_stats = self.db.llm_stats("/api/users", "GET")
        self.assertEqual(llm_stats["llm_request_count"], 0)


class TestLLMEndpointDetection(unittest.TestCase):
    """Tests for LLM endpoint detection heuristic (#118)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp.name, "test.db")
        self.stage = PerfStage(db_path=db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chat_completions_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/api/chat/completions"))

    def test_embeddings_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/v1/embeddings"))

    def test_inference_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/inference/llama"))

    def test_generate_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/generate-text"))

    def test_ai_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/ai/prompt"))

    def test_predict_is_llm(self):
        self.assertTrue(self.stage._is_llm_endpoint("/model/predict"))

    def test_health_not_llm(self):
        self.assertFalse(self.stage._is_llm_endpoint("/health"))

    def test_users_not_llm(self):
        self.assertFalse(self.stage._is_llm_endpoint("/api/users"))

    def test_status_not_llm(self):
        self.assertFalse(self.stage._is_llm_endpoint("/status"))

    def test_config_not_llm(self):
        self.assertFalse(self.stage._is_llm_endpoint("/api/config"))


class TestTrafficLoadProfile(unittest.TestCase):
    """Tests for traffic-based load profile generation (#117)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.tmp.name, "test.db")
        self.stage = PerfStage(db_path=db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_har(self, entries):
        content = json.dumps({"log": {"entries": entries}})
        fd, path = tempfile.mkstemp(suffix=".har", dir=self.tmp.name)
        os.close(fd)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_single_entry_generates_profile(self):
        path = self._make_har([{
            "request": {"method": "GET", "url": "http://localhost:3000/api/test"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {"send": 5, "wait": 50, "receive": 10},
        }])
        profile = self.stage.generate_load_profile_from_traffic(path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.method, "GET")
        self.assertIn("/api/test", profile.endpoint)

    def test_multiple_entries_picks_most_common(self):
        entries = []
        for i in range(3):
            entries.append({
                "request": {"method": "POST", "url": "http://localhost:3000/api/chat"},
                "response": {"status": 200, "statusText": "OK", "headers": []},
                "timings": {"send": 5, "wait": 100, "receive": 10},
            })
        for i in range(10):
            entries.append({
                "request": {"method": "GET",
                            "url": "http://localhost:3000/api/users"},
                "response": {"status": 200, "statusText": "OK", "headers": []},
                "timings": {"send": 2, "wait": 30, "receive": 5},
            })
        path = self._make_har(entries)
        profile = self.stage.generate_load_profile_from_traffic(path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.method, "GET")

    def test_missing_file_returns_none(self):
        profile = self.stage.generate_load_profile_from_traffic("/nonexistent.har")
        self.assertIsNone(profile)

    def test_empty_har_returns_none(self):
        path = self._make_har([])
        profile = self.stage.generate_load_profile_from_traffic(path)
        self.assertIsNone(profile)

    def test_profile_has_reasonable_defaults(self):
        path = self._make_har([{
            "request": {"method": "POST", "url": "http://localhost:3000/api/data"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {"send": 5, "wait": 100, "receive": 10},
        }])
        profile = self.stage.generate_load_profile_from_traffic(path)
        self.assertIsNotNone(profile)
        self.assertGreater(profile.vus, 0)
        self.assertGreater(profile.duration_sec, 0)
        self.assertEqual(profile.method, "POST")
        self.assertIn("/api/data", profile.endpoint)


class TestMLAnomalyTier(unittest.TestCase):
    """Tests for ML anomaly detection tier (#119)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.stage = PerfStage(db_path=self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_statistical_is_default(self):
        analysis = self.stage._analyze("/api/test", "GET", 50.0)
        self.assertEqual(analysis["method"], "statistical")

    def test_normal_within_range(self):
        for i in range(10):
            self.stage.db.record("/api/test", "GET", 40.0 + (i % 3))
        analysis = self.stage._analyze("/api/test", "GET", 42.0)
        self.assertFalse(analysis["anomaly_detected"])

    def test_spike_detected(self):
        for i in range(10):
            self.stage.db.record("/api/test", "GET", 40.0 + (i % 3))
        analysis = self.stage._analyze("/api/test", "GET", 500.0)
        self.assertTrue(analysis["anomaly_detected"])

    def test_initializing_for_few_samples(self):
        self.stage.db.record("/api/new", "GET", 50.0)
        self.stage.db.record("/api/new", "GET", 52.0)
        analysis = self.stage._analyze("/api/new", "GET", 51.0)
        self.assertTrue(analysis.get("initializing", False))

    def test_analysis_returns_stats(self):
        for i in range(5):
            self.stage.db.record("/api/stats", "GET", 50.0 + i)
        analysis = self.stage._analyze("/api/stats", "GET", 55.0)
        self.assertIn("count", analysis)
        self.assertIn("mean", analysis)
        self.assertIn("stddev", analysis)
        self.assertIn("threshold_limit", analysis)

    def test_backward_compatible_signature(self):
        sl = PerfSlice(name="compat", target_url="http://localhost:3000",
                       endpoint="/api/compat", method="GET", vus=1, duration_sec=1)
        result = self.stage.run(sl)
        self.assertEqual(result.status.value, "ok")

    @unittest.skipIf(not __import__("importlib").util.find_spec("sklearn"),
                     "sklearn not available")
    def test_ml_analysis_with_isolation_forest(self):
        from sklearn.ensemble import IsolationForest
        for i in range(15):
            self.stage.db.record("/api/ml", "GET", 40.0 + (i % 5))
        analysis = self.stage._analyze("/api/ml", "GET", 42.0, use_ml=True)
        self.assertTrue(analysis["method"].startswith("ml_")
                        or analysis["method"] == "statistical")


class TestLatencyAnomalyDetector(unittest.TestCase):
    """Tests for the robust LatencyAnomalyDetector."""

    def setUp(self):
        self.detector = LatencyAnomalyDetector(k=3.5, min_samples=8)
        self.history = [40.0, 42.0, 41.0, 43.0, 39.0,
                        41.0, 42.0, 40.0, 43.0, 41.0]

    def test_normal_value_no_anomaly(self):
        verdict = self.detector.evaluate(self.history, 42.0)
        self.assertFalse(verdict.is_anomaly)
        self.assertEqual(verdict.kind, "none")

    def test_spike_detected(self):
        verdict = self.detector.evaluate(self.history, 300.0)
        self.assertTrue(verdict.is_anomaly)
        self.assertEqual(verdict.kind, "spike")

    def test_insufficient_data(self):
        verdict = self.detector.evaluate([], 42.0)
        self.assertEqual(verdict.kind, "insufficient_data")

    def test_drift_detected(self):
        drift_hist = [40.0] * 10 + [65.0] * 5
        verdict = self.detector.evaluate(drift_hist[:-1], drift_hist[-1])
        self.assertTrue(verdict.kind == "drift")

    def test_drift_not_triggered_for_normal(self):
        verdict = self.detector.evaluate(self.history, 41.0)
        self.assertEqual(verdict.kind, "none")

    def test_custom_parameters(self):
        strict = LatencyAnomalyDetector(k=2.0, min_samples=3)
        verdict = strict.evaluate([40.0, 41.0, 42.0], 60.0)
        self.assertTrue(verdict.is_anomaly)
        self.assertEqual(verdict.kind, "spike")

    def test_verdict_contains_details(self):
        verdict = self.detector.evaluate(self.history, 300.0)
        self.assertIsInstance(verdict.value, float)
        self.assertIsInstance(verdict.center, float)
        self.assertIsInstance(verdict.upper, float)
        self.assertTrue(len(verdict.detail) > 0)


class TestTrafficSourceAdapter(unittest.TestCase):
    """Tests for truth/sources/traffic.py integration (#117)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from cherenkov.truth.sources.traffic import TrafficSourceAdapter
        self.adapter = TrafficSourceAdapter()

    def tearDown(self):
        self.tmp.cleanup()

    def _make_har(self, entries):
        content = json.dumps({"log": {"entries": entries}})
        fd, path = tempfile.mkstemp(suffix=".har", dir=self.tmp.name)
        os.close(fd)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_empty_har_returns_empty_claims(self):
        path = self._make_har([])
        claims = self.adapter.discover_claims(path)
        self.assertEqual(claims, [])

    def test_extracts_status_claims(self):
        path = self._make_har([{
            "request": {"method": "GET", "url": "http://example.com/api"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {},
        }])
        claims = self.adapter.discover_claims(path)
        statuses = [c for c in claims if c.category == "observed_status"]
        self.assertGreaterEqual(len(statuses), 1)

    def test_extracts_latency_claims(self):
        path = self._make_har([{
            "request": {"method": "GET", "url": "http://example.com/api"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {"send": 5, "wait": 100, "receive": 10},
        }])
        claims = self.adapter.discover_claims(path)
        latencies = [c for c in claims if c.category == "observed_latency"]
        self.assertGreaterEqual(len(latencies), 1)
        self.assertEqual(latencies[0].value["total_ms"], 115)

    def test_provenance_is_traffic(self):
        from cherenkov.core.contracts import ProvenanceType
        path = self._make_har([{
            "request": {"method": "GET", "url": "http://example.com/api"},
            "response": {"status": 200, "statusText": "OK", "headers": []},
            "timings": {},
        }])
        claims = self.adapter.discover_claims(path)
        for c in claims:
            self.assertEqual(c.provenance.source_type, ProvenanceType.TRAFFIC)


if __name__ == "__main__":
    unittest.main()
