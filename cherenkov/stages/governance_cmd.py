from __future__ import annotations

import json
import sys

from cherenkov.governance.kpi import GovernanceCollector


def run_governance(json_out: bool = False, trend: str | None = None) -> int:
    collector = GovernanceCollector(run_id="cli_governance")
    report = collector.collect()

    if trend:
        values = collector.get_trend(metric=trend, limit=20)
        if json_out:
            print(json.dumps({"metric": trend, "values": values}))
        else:
            print(f"Trend for '{trend}' (last {len(values)} snapshots):")
            if values:
                bar_width = 40
                for i, v in enumerate(values):
                    bar_len = max(1, int(v * bar_width))
                    bar = "█" * bar_len
                    print(f"  {i:>2}: {bar} {v:.3f}")
            else:
                print("  (no history yet - run governance period)")

    elif json_out:
        print(json.dumps(report.render_json(), indent=2))
    else:
        print(report.render())

    return 0
