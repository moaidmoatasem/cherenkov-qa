"""cherenkov/drift/ledger.py — Append-only JSONL ledger for SpecSuiteSnapshots.

Design choice: JSONL over SQLite for the first cut.
  - Git-diffable, human-inspectable, survives crashes without WAL corruption.
  - brute-force scan is fast enough at tens–low-hundreds of operations (no ANN needed).
  - Each line is one JSON-serialized SpecSuiteSnapshot.

Three execution tiers (spec §2):
  Interactive   — discover latest in ledger (local dev)
  CI-fast       — explicit --baseline-id (known key)
  CI-fastest    — --baseline-file (downloaded artifact, no DB roundtrip)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cherenkov.drift.snapshot import SpecSuiteSnapshot


_DEFAULT_LEDGER_PATH = Path(os.environ.get(
    "CHERENKOV_DRIFT_LEDGER",
    os.path.join(os.getcwd(), ".cherenkov", "drift-ledger.jsonl"),
))


class DriftLedger:
    """Append-only JSONL ledger for drift baselines.

    Each line is a JSON-serialized SpecSuiteSnapshot.
    The file is never rewritten — only appended to.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else _DEFAULT_LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── write ─────────────────────────────────────────────────────────────────

    def seed_baseline(
        self,
        spec: dict[str, Any],
        suite: dict[str, Any],
        generation_profile: str = "default",
    ) -> SpecSuiteSnapshot:
        """Persist a new baseline snapshot and return it.

        If a snapshot with the same spec_hash + suite_hash already exists,
        returns the existing record without duplicating the ledger.
        """
        snapshot = SpecSuiteSnapshot.create(spec, suite, generation_profile)

        # Idempotency check: skip if identical hashes already in ledger
        for existing in self._iter_all():
            if (
                existing.spec_hash == snapshot.spec_hash
                and existing.suite_hash == snapshot.suite_hash
            ):
                return existing

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(snapshot.to_dict()) + "\n")
        return snapshot

    # ── read ──────────────────────────────────────────────────────────────────

    def list_snapshots(
        self,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[SpecSuiteSnapshot]:
        """Return snapshots in reverse-chronological order (newest first).

        Args:
            since: ISO-8601 snapshot_id; return only snapshots created after this.
            limit: Maximum number of results.
        """
        all_snapshots = list(reversed(list(self._iter_all())))
        if since:
            all_snapshots = [s for s in all_snapshots if s.snapshot_id > since]
        if limit is not None:
            all_snapshots = all_snapshots[:limit]
        return all_snapshots

    def get_snapshot(self, snapshot_id: str) -> SpecSuiteSnapshot | None:
        """Retrieve a specific snapshot by its ID."""
        for snapshot in self._iter_all():
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

    def latest(self) -> SpecSuiteSnapshot | None:
        """Return the most recently written snapshot."""
        last = None
        for snapshot in self._iter_all():
            last = snapshot
        return last

    # ── reconcile convenience ─────────────────────────────────────────────────

    def reconcile_from(
        self,
        baseline_id: str | None = None,
        baseline_file: Path | str | None = None,
        current_spec: dict[str, Any] | None = None,
        current_suite: dict[str, Any] | None = None,
        runner_violations: list[dict] | None = None,
    ) -> "DriftReport":  # noqa: F821
        """Run reconcile() using a ledger-looked-up or file-loaded baseline.

        Tier mapping:
          Interactive  — baseline_id=None, discovers latest snapshot in ledger.
          CI-fast      — pass explicit baseline_id.
          CI-fastest   — pass baseline_file path (JSONL single-line or full JSON).
        """
        from cherenkov.drift.reconcile import reconcile

        if current_spec is None or current_suite is None:
            raise ValueError("current_spec and current_suite are required")

        baseline: SpecSuiteSnapshot | None = None

        if baseline_file is not None:
            baseline = self._load_baseline_file(Path(baseline_file))
        elif baseline_id is not None:
            baseline = self.get_snapshot(baseline_id)
            if baseline is None:
                raise KeyError(f"No snapshot with id={baseline_id!r}")
        else:
            baseline = self.latest()
            if baseline is None:
                raise RuntimeError(
                    "No baseline in ledger — run seed_baseline() first"
                )

        return reconcile(baseline, current_spec, current_suite, runner_violations)

    # ── export / import ───────────────────────────────────────────────────────

    def export_snapshot(
        self, snapshot_id: str | None = None, path: Path | str | None = None
    ) -> Path:
        """Write a single snapshot to a file (CI artifact download path)."""
        snapshot = (
            self.get_snapshot(snapshot_id) if snapshot_id else self.latest()
        )
        if snapshot is None:
            raise KeyError("No snapshot found to export")
        out_path = Path(path) if path else Path(f"drift-baseline-{snapshot.snapshot_id}.json")
        out_path.write_text(json.dumps(snapshot.to_dict(), indent=2))
        return out_path

    # ── internal ─────────────────────────────────────────────────────────────

    def _iter_all(self):
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    yield SpecSuiteSnapshot.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    continue

    def _load_baseline_file(self, path: Path) -> SpecSuiteSnapshot:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        # Support both single-snapshot JSON and JSONL (take last line)
        if isinstance(data, list):
            data = data[-1]
        return SpecSuiteSnapshot.from_dict(data)
