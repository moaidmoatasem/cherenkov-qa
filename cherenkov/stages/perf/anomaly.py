"""
CHERENKOV stages/perf/anomaly.py — E8 robust latency anomaly detection.

Dependency-free upgrade over mean+stddev outlier flagging (the existing perf
baseline). Two detectors, no numpy/sklearn so the local-first default never
needs heavy deps:

  • SPIKE — point beyond  median + k * (1.4826 * MAD).
           Median/MAD resist contamination, so one bad warm-up sample doesn't
           inflate the band and cause false negatives (mean/stddev does).
  • DRIFT — the recent window's median sits materially above the baseline
           median even when no single point spikes. Catches gradual saturation
           / latency creep / a leak *before* it crosses a hard threshold.

This is the seam E8 will later swap for seasonal-baseline / isolation-forest
models behind the same `evaluate()` contract.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

_MAD_TO_SIGMA = 1.4826  # makes MAD a consistent estimator of stddev for normal data


@dataclass
class AnomalyVerdict:
    is_anomaly: bool
    kind: str            # "none" | "spike" | "drift" | "insufficient_data"
    value: float
    center: float        # robust baseline (median)
    upper: float         # spike threshold
    detail: str


def _robust_center_scale(xs: list[float]) -> tuple[float, float]:
    center = statistics.median(xs)
    mad = statistics.median([abs(x - center) for x in xs])
    scale = _MAD_TO_SIGMA * mad
    if scale <= 0.0:
        # degenerate (≥half identical): fall back to stdev, then a relative floor
        try:
            scale = statistics.pstdev(xs)
        except statistics.StatisticsError:
            scale = 0.0
        if scale <= 0.0:
            scale = max(abs(center) * 0.10, 1e-9)
    return center, scale


class LatencyAnomalyDetector:
    """Robust spike + drift detection over a latency history.

    Args:
        k:            spike sensitivity (robust sigmas above the median).
        drift_window: how many recent points define "recent".
        drift_ratio:  recent-median / baseline-median that counts as drift.
        min_samples:  below this, we abstain (return "insufficient_data").
    """

    def __init__(
        self,
        k: float = 3.5,
        drift_window: int = 5,
        drift_ratio: float = 1.5,
        min_samples: int = 8,
    ) -> None:
        self.k = k
        self.drift_window = drift_window
        self.drift_ratio = drift_ratio
        self.min_samples = min_samples

    def evaluate(self, history: list[float], value: float) -> AnomalyVerdict:
        """Judge `value` against the prior `history` (excludes `value`)."""
        if len(history) < self.min_samples:
            return AnomalyVerdict(False, "insufficient_data", value, 0.0, 0.0,
                                  f"need ≥{self.min_samples} baseline samples, have {len(history)}")

        center, scale = _robust_center_scale(history)
        upper = center + self.k * scale

        if value > upper:
            return AnomalyVerdict(
                True, "spike", value, center, upper,
                f"{value:.1f} > {upper:.1f} (median {center:.1f} + {self.k}·{scale:.1f})",
            )

        # Drift compares the RECENT window to the EARLY baseline (not the whole
        # history, which the drift itself contaminates and hides).
        recent = (history + [value])[-self.drift_window:]
        recent_center = statistics.median(recent)
        early = history[: max(1, len(history) // 2)]
        early_center = statistics.median(early)
        if early_center > 0 and recent_center >= early_center * self.drift_ratio:
            return AnomalyVerdict(
                True, "drift", value, center, upper,
                f"recent median {recent_center:.1f} ≥ {self.drift_ratio}× early-baseline "
                f"{early_center:.1f} (gradual saturation before any single spike)",
            )

        return AnomalyVerdict(False, "none", value, center, upper,
                              f"{value:.1f} within band (≤ {upper:.1f})")
