from unittest.mock import patch
from cherenkov.execution.perf_analyzer import PerformanceAnalyzer


@patch("cherenkov.execution.perf_analyzer.os.path.abspath")
def test_baseline_stats_calculation(mock_abspath, tmp_path):
    # Setup isolated test DB
    mock_abspath.return_value = str(tmp_path / "perf_store.db")
    analyzer = PerformanceAnalyzer("test_run")

    # Insert mock latencies (10, 20, 30 -> mean 20, variance 100, stddev 10)
    analyzer.record_latency("/test", "GET", 10.0)
    analyzer.record_latency("/test", "GET", 20.0)
    analyzer.record_latency("/test", "GET", 30.0)

    stats = analyzer.get_baseline_stats("/test", "GET")
    assert stats["count"] == 3
    assert stats["mean"] == 20.0
    assert stats["stddev"] == 8.16


@patch("cherenkov.execution.perf_analyzer.os.path.abspath")
def test_anomaly_detection(mock_abspath, tmp_path):
    mock_abspath.return_value = str(tmp_path / "perf_store.db")
    analyzer = PerformanceAnalyzer("test_run")

    # Insert 3 base latencies
    for val in [50.0, 52.0, 48.0]:
        analyzer.record_latency("/test", "POST", val)

    # Base mean is 50.0, variance is ((0)^2 + (2)^2 + (-2)^2) / 3 = 8/3 = 2.66
    # Stddev = sqrt(2.66) = ~1.63

    # Within threshold (2 stddev ~3.26)
    analysis_pass = analyzer.analyze_anomaly("/test", "POST", 52.5)
    assert analysis_pass["status"] == "passed"
    assert not analysis_pass["anomaly_detected"]

    # Outside threshold (50 + 2*1.63 = 53.26 limit)
    analysis_fail = analyzer.analyze_anomaly("/test", "POST", 60.0)
    assert analysis_fail["status"] == "anomaly_detected"
    assert analysis_fail["anomaly_detected"]
