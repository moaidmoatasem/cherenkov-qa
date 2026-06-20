"""
cherenkov/stages/daemon_cmd.py — E4-4: Daemon mode.

Watch sources, keep the Truth Model fresh, queue divergences.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.stages.map_cmd import build_truth_model


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


def _get_spec_mtimes(spec_paths: list[str]) -> dict[str, float]:
    mtimes = {}
    for p in spec_paths:
        try:
            mtimes[p] = Path(p).stat().st_mtime
        except OSError:
            mtimes[p] = 0.0
    return mtimes


def run_daemon(interval_seconds: int = 60, max_loops: int = 0, target_url: str | None = None) -> int:
    """Execute `cherenkov daemon`.

    Continuously watches sources, rebuilds the Truth Model, and runs divergence
    proof against target_url on each cycle (or when specs change).

    Args:
        interval_seconds: Poll interval between rebuilds.
        max_loops: Max rebuild iterations (0 = infinite).
        target_url: Live server URL to probe each cycle. If omitted, only truth
            model is rebuilt (no live divergence check).

    Returns:
        Exit code.
    """
    log = get_logger("daemon")
    queue = DivergenceQueue()
    loop_count = 0
    last_mtimes: dict[str, float] = {}

    log.info("daemon started", interval_seconds=interval_seconds, target_url=target_url or "none")

    while max_loops == 0 or loop_count < max_loops:
        loop_count += 1

        from cherenkov.core.config_loader import load_effective_config

        cfg = load_effective_config()
        specs = cfg.autodetect_spec() or []
        sources = {"openapi": specs} if specs else {}

        # Detect spec file changes
        current_mtimes = _get_spec_mtimes(specs)
        changed = [p for p, mt in current_mtimes.items() if last_mtimes.get(p, -1) != mt]
        last_mtimes = current_mtimes

        if changed:
            log.info("spec change detected", files=changed)

        log.info("rebuilding truth model", loop=loop_count)

        if sources:
            tm = build_truth_model(sources)
            log.info("truth model built", nodes=len(tm.nodes), edges=len(tm.edges))
        else:
            log.warning("no sources configured, skipping rebuild")
            tm = None  # type: ignore[assignment]

        # Run divergence proof if a target URL is configured
        divergences = []
        if target_url:
            log.info("running divergence proof", url=target_url)
            try:
                import json as _json
                from cherenkov.divergence.proof_run import run_proof

                # Load first spec file as dict if available, else use bundled Petstore
                spec_dict = None
                if specs:
                    try:
                        spec_dict = _json.loads(Path(specs[0]).read_text(encoding="utf-8"))
                    except Exception:
                        spec_dict = None

                divergences = run_proof(base_url=target_url, spec=spec_dict, use_llm=False)

                if divergences:
                    log.warning("divergences found", count=len(divergences))
                    from cherenkov.hitl import HitlItem, HitlQueue
                    import uuid as _uuid

                    hitl = HitlQueue()
                    run_id = f"daemon_{loop_count}_{int(time.time())}"
                    for r in divergences:
                        item = HitlItem(
                            id=str(_uuid.uuid4()),
                            endpoint=r.endpoint,
                            run_id=run_id,
                            mutation_label=r.divergence_class.value,
                            confidence_reason=r.evidence.diff[:200] if r.evidence and r.evidence.diff else r.claim_b[:200],
                        )
                        hitl.enqueue(item)
                else:
                    log.info("no divergences found")
            except Exception as exc:
                log.error("divergence proof failed", error=str(exc))

        queue.push(
            {
                "loop": loop_count,
                "timestamp": time.time(),
                "nodes": len(tm.nodes) if tm else 0,
                "edges": len(tm.edges) if tm else 0,
                "spec_changes": changed,
                "divergences": len(divergences),
            }
        )

        if max_loops != 0 and loop_count >= max_loops:
            break

        time.sleep(interval_seconds)

    log.info("daemon stopped", total_loops=loop_count)
    return 0


def run_guardian_daemon(
    target_url: str,
    spec_path: str,
    source_type: str = "openapi",
    interval_seconds: int = 10,
) -> int:
    """Execute `cherenkov daemon --guardian`.

    Actively monitors the specification file and triggers real CHERENKOV
    conformance generation and validation on change.
    """
    log = get_logger("guardian_daemon")

    from cherenkov.daemon.watcher import SpecGuardianWatcher
    from pathlib import Path

    spec_file = Path(spec_path)
    target_repo = spec_file.parent if spec_file.parent.name else Path(".")
    filename = spec_file.name

    log.info(
        f"Guardian daemon starting on {spec_path} -> {target_url}",
        interval=interval_seconds,
    )
    watcher = SpecGuardianWatcher(
        target_repo=str(target_repo),
        target_url=target_url,
        source_type=source_type,
        watch_files=[filename],
    )

    # We run start_watching which loops indefinitely.
    watcher.start_watching(poll_interval=interval_seconds)

    return 0
