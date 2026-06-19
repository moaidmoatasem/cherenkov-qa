"""
Smoke test for E12 Governance KPI panel (C12 #127).

Verifies:
  1. GovernanceKPI dataclass with all fields
  2. health_score calculation
  3. GovernanceReport render() and render_json()
  4. GovernanceCollector collects and persists
  5. Trend retrieval
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.governance.kpi import (
    GovernanceKPI,
    GovernanceReport,
    GovernanceCollector,
)


errors: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [OK] {msg}")


print("1. GovernanceKPI fields")
kpi = GovernanceKPI(
    escape_rate=0.1,
    false_positive_rate=0.05,
    coverage=0.85,
    maintenance_score=0.9,
    total_tests=100,
    passed_tests=85,
    failed_tests=15,
    escaped_defects=10,
    false_positives=5,
    idiom_count=12,
    total_endpoints=20,
    covered_endpoints=17,
)
check(abs(kpi.escape_rate - 0.1) < 0.001, f"escape_rate={kpi.escape_rate}")
check(
    abs(kpi.false_positive_rate - 0.05) < 0.001,
    f"false_positive_rate={kpi.false_positive_rate}",
)
check(abs(kpi.coverage - 0.85) < 0.001, f"coverage={kpi.coverage}")
check(kpi.total_tests == 100, f"total_tests={kpi.total_tests}")

print("\n2. health_score calculation")
score = kpi.health_score
check(0.0 <= score <= 1.0, f"health_score in range: {score}")
check(abs(score - 0.895) < 0.01, f"health_score={score:.3f} ~= 0.895")

print("\n3. GovernanceReport")
report = GovernanceReport(kpi=kpi)
rendered = report.render()
check("E12 Governance KPI Panel" in rendered, "render() contains header")
check("Escape Rate" in rendered, "render() contains escape rate")
check("Coverage" in rendered, "render() contains coverage")
check("Pass Rate" in rendered, "render() contains pass rate")

json_report = report.render_json()
check(json_report["health_score"] == score, "render_json() has health_score")
check(json_report["escape_rate"] == 0.1, "render_json() has escape_rate")
check(json_report["passed_tests"] == 85, "render_json() has passed_tests")

print("\n4. GovernanceCollector")
db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db.close()
collector = GovernanceCollector(db_path=db.name, run_id="smoke_test")
collected = collector.collect()
check(isinstance(collected, GovernanceReport), "collect() returns GovernanceReport")
check(isinstance(collected.kpi, GovernanceKPI), "report has kpi")
check(collected.kpi.last_run_ts > 0, "has timestamp")

print("\n5. Trend retrieval")
trend = collector.get_trend(metric="health_score", limit=5)
check(isinstance(trend, list), "get_trend returns list")
for v in trend:
    check(0.0 <= v <= 1.0, f"trend value in range: {v}")

if os.path.exists(db.name):
    os.unlink(db.name)

print(f"\n{'='*40}")
if errors:
    print(f"FAILED ({len(errors)} check(s))")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
