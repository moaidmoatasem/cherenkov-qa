"""
cherenkov/stages/daemon_cmd.py — E4-4: Daemon mode.
Authority: v3.1 + delta.

Watch sources, keep the Truth Model fresh, queue divergences.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.stages.map_cmd import build_truth_model, render_truth_model


class DivergenceQueue:
    """Persistent divergence queue backed by JSON lines."""

    def __init__(self, path: Path | None = None):
        self._path = path or Path.cwd() / ".cherenkov" / "divergence_queue.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def push(self, entry: dict[str, Any]) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def pop_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        entries = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        self._path.unlink(missing_ok=True)
        return entries

    @property
    def count(self) -> int:
        if not self._path.exists():
            return 0
        count = 0
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count


def run_daemon(interval_seconds: int = 60, max_loops: int = 0) -> int:
    """Execute `cherenkov daemon`.

    Continuously watches sources, rebuilds the Truth Model, and queues divergences.

    Args:
        interval_seconds: Poll interval between rebuilds.
        max_loops: Max rebuild iterations (0 = infinite).

    Returns:
        Exit code.
    """
    log = get_logger("daemon")
    queue = DivergenceQueue()
    loop_count = 0

    log.info("daemon started", interval_seconds=interval_seconds)

    while max_loops == 0 or loop_count < max_loops:
        loop_count += 1
        log.info("rebuilding truth model", loop=loop_count)

        from cherenkov.core.config_loader import load_effective_config
        cfg = load_effective_config()

        sources = {}
        specs = cfg.autodetect_spec()
        if specs:
            sources["openapi"] = specs

        if sources:
            tm = build_truth_model(sources)
            summary = render_truth_model(tm)
            log.info("truth model built", nodes=len(tm.nodes), edges=len(tm.edges))
        else:
            log.warning("no sources configured, skipping rebuild")
            summary = ""

        queue.push({
            "loop": loop_count,
            "timestamp": time.time(),
            "nodes": len(tm.nodes) if sources else 0,
            "edges": len(tm.edges) if sources else 0,
            "summary": summary,
        })

        if max_loops != 0 and loop_count >= max_loops:
            break

        time.sleep(interval_seconds)

    log.info("daemon stopped", total_loops=loop_count)
    return 0
