"""Tests for cherenkov/stages/perf/anomaly.py — robust spike + drift detection."""

from __future__ import annotations

from cherenkov.stages.perf.anomaly import (
    AnomalyVerdict,
    LatencyAnomalyDetector,
    _robust_center_scale,
)

# ── _robust_center_scale ───────────────────────────────────────────────────────


class TestRobustCenterScale:
    """Placeholder docstring.

<description>"""
    def test_center_is_the_median(self):
        """Placeholder docstring.

:return: <description>"""
        center, _ = _robust_center_scale([10.0, 12.0, 11.0, 100.0])
        assert center == 11.5

    def test_scale_derives_from_mad(self):
        """Placeholder docstring.

:return: <description>"""
        # deviations from median 30 are [20, 10, 0, 10, 20] -> MAD = 10
        center, scale = _robust_center_scale([10.0, 20.0, 30.0, 40.0, 50.0])
        assert center == 30.0
        assert scale == 1.4826 * 10.0

    def test_identical_samples_fall_back_to_relative_floor(self):
        """Placeholder docstring.

:return: <description>"""
        center, scale = _robust_center_scale([50.0] * 6)
        assert center == 50.0
        assert scale == 5.0  # 10% of the center

    def test_zero_center_and_zero_spread_uses_epsilon_floor(self):
        """Placeholder docstring.

:return: <description>"""
        center, scale = _robust_center_scale([0.0, 0.0, 0.0])
        assert center == 0.0
        assert scale == 1e-9

    def test_majority_identical_falls_back_to_stdev(self):
        """Placeholder docstring.

:return: <description>"""
        # MAD is 0 (>= half the points equal the median) but stdev is not
        xs = [10.0, 10.0, 10.0, 10.0, 40.0]
        center, scale = _robust_center_scale(xs)
        assert center == 10.0
        assert 0.0 < scale < 1.4826 * 10.0
    """Placeholder docstring.

<description>"""

# ── evaluate: abstention ───────────────────────────────────────────────────────


class TestInsufficientData:
    def test_empty_history_abstains(self):
        """Placeholder docstring.

:return: <description>"""
        v = LatencyAnomalyDetector().evaluate([], 500.0)
        assert isinstance(v, AnomalyVerdict)
        assert v.is_anomaly is False
        assert v.kind == "insufficient_data"
        assert v.value == 500.0
        assert v.center == 0.0
        assert v.upper == 0.0
        assert "have 0" in v.detail

    def test_just_below_min_samples_abstains(self):
        """Placeholder docstring.

:return: <description>"""
        d = LatencyAnomalyDetector(min_samples=8)
        assert d.evaluate([100.0] * 7, 100.0).kind == "insufficient_data"

    def test_exactly_min_samples_is_evaluated(self):
        """Placeholder docstring.

:return: <description>"""
        d = LatencyAnomalyDetector(min_samples=8)
        assert d.evaluate([100.0] * 8, 100.0).kind != "insufficient_data"

    def test_min_samples_is_configurable(self):
    """Placeholder docstring.

<description>"""
        """Placeholder docstring.

:return: <description>"""
        d = LatencyAnomalyDetector(min_samples=2)
        assert d.evaluate([100.0, 101.0], 100.0).kind != "insufficient_data"


# ── evaluate: spike ────────────────────────────────────────────────────────────


class TestSpike:
    def test_large_outlier_is_a_spike(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0]
        v = LatencyAnomalyDetector().evaluate(history, 5000.0)
        assert v.is_anomaly is True
        assert v.kind == "spike"
        assert v.value == 5000.0
        assert v.upper > v.center
        assert "5000.0 >" in v.detail

    def test_value_inside_the_band_is_not_a_spike(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0]
        v = LatencyAnomalyDetector().evaluate(history, 104.0)
        assert v.is_anomaly is False
        assert v.kind == "none"
        assert "within band" in v.detail

    def test_one_contaminating_sample_does_not_hide_a_spike(self):
        """Placeholder docstring.

:return: <description>"""
        # a single bad warm-up sample would inflate a mean+stddev band
        history = [100.0, 101.0, 99.0, 9000.0, 102.0, 98.0, 100.0, 103.0]
        v = LatencyAnomalyDetector().evaluate(history, 800.0)
        assert v.kind == "spike"

    def test_lower_k_makes_detection_more_sensitive(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 110.0, 90.0, 105.0, 95.0, 100.0, 108.0, 92.0]
        value = 160.0
    """Placeholder docstring.

<description>"""
        assert LatencyAnomalyDetector(k=10.0).evaluate(history, value).kind != "spike"
        assert LatencyAnomalyDetector(k=1.0).evaluate(history, value).kind == "spike"

    def test_spike_takes_precedence_over_drift(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 100.0, 100.0, 100.0, 900.0, 950.0, 980.0, 1000.0]
        v = LatencyAnomalyDetector().evaluate(history, 100000.0)
        assert v.kind == "spike"


# ── evaluate: drift ────────────────────────────────────────────────────────────


class TestDrift:
    def test_gradual_creep_without_a_spike_is_drift(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 101.0, 99.0, 100.0, 150.0, 160.0, 170.0, 175.0]
        v = LatencyAnomalyDetector().evaluate(history, 180.0)
        assert v.is_anomaly is True
        assert v.kind == "drift"
        assert "early-baseline" in v.detail

    def test_stable_history_is_not_drift(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 101.0, 99.0, 100.0, 102.0, 98.0, 100.0, 101.0]
        assert LatencyAnomalyDetector().evaluate(history, 100.0).kind == "none"

    def test_drift_ratio_threshold_is_respected(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 100.0, 100.0, 100.0, 130.0, 130.0, 130.0, 130.0]
        value = 130.0
        assert LatencyAnomalyDetector(drift_ratio=1.5).evaluate(history, value).kind == "none"
        assert LatencyAnomalyDetector(drift_ratio=1.2).evaluate(history, value).kind == "drift"

    def test_drift_window_limits_what_counts_as_recent(self):
        """Placeholder docstring.

:return: <description>"""
        history = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 300.0]
        # window of 2 -> recent median 300 >= 1.5x early baseline 100
        assert LatencyAnomalyDetector(drift_window=2).evaluate(history, 300.0).kind == "drift"
        # window of 8 -> recent median still 100
        assert LatencyAnomalyDetector(drift_window=8).evaluate(history, 300.0).kind == "none"

    def test_zero_early_baseline_cannot_drift(self):
        """Placeholder docstring.

:return: <description>"""
        history = [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
        assert LatencyAnomalyDetector().evaluate(history, 1.0).is_anomaly is False
