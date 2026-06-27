"""
cherenkov/divergence/report_diff.py — Diff two divergence report snapshots.

Compares a baseline (previous run) against a current run to surface:
  - NEW divergences (in current, not in baseline)
  - RESOLVED divergences (in baseline, not in current)
  - UNCHANGED divergences (same in both)

Divergences are matched by a stable key: (endpoint, divergence_class, claim_a[:80]).
This is deterministic and survives minor evidence wording changes between runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _stable_key(div: dict) -> str:
    """Stable identity key for a divergence record."""
    endpoint = div.get("endpoint", "")
    dc = div.get("divergence_class", "")
    claim_a = (div.get("claim_a") or "")[:80]
    return f"{endpoint}|{dc}|{claim_a}"


@dataclass
class ReportDiff:
    new: list[dict] = field(default_factory=list)
    resolved: list[dict] = field(default_factory=list)
    unchanged: list[dict] = field(default_factory=list)

    @property
    def has_new(self) -> bool:
        return len(self.new) > 0

    @property
    def summary_line(self) -> str:
        parts = []
        if self.new:
            parts.append(f"+{len(self.new)} new")
        if self.resolved:
            parts.append(f"-{len(self.resolved)} resolved")
        if self.unchanged:
            parts.append(f"{len(self.unchanged)} unchanged")
        return ", ".join(parts) if parts else "no change"


def diff_reports(baseline: list[dict], current: list[dict]) -> ReportDiff:
    """Return a ReportDiff comparing baseline → current divergence lists."""
    baseline_keys: dict[str, dict] = {_stable_key(d): d for d in baseline}
    current_keys: dict[str, dict] = {_stable_key(d): d for d in current}

    new = [current_keys[k] for k in current_keys if k not in baseline_keys]
    resolved = [baseline_keys[k] for k in baseline_keys if k not in current_keys]
    unchanged = [current_keys[k] for k in current_keys if k in baseline_keys]

    return ReportDiff(new=new, resolved=resolved, unchanged=unchanged)
