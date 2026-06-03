"""
CHERENKOV reflector/cli.py — inspect the E7 Reflector's learned memory.

Isolated module surface (run via `python -m cherenkov.reflector.cli`), kept off
the cherenkov.py argparse tree so it adds zero docs-drift surface and no coupling
to the main CLI.

Usage:
    python -m cherenkov.reflector.cli                 # everything
    python -m cherenkov.reflector.cli --stats
    python -m cherenkov.reflector.cli --idioms --limit 10
    python -m cherenkov.reflector.cli --audit         # memory self-audit
    python -m cherenkov.reflector.cli --db /path/to/verdicts.db ...
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

from cherenkov.reflector.introspect import audit_memory
from cherenkov.reflector.reflector import Reflector
from cherenkov.reflector.store import VerdictStore


def build_report(
    db_path: str | None = None,
    *,
    stats: bool = True,
    idioms: bool = True,
    audit: bool = True,
    limit: int = 20,
) -> str:
    """Render a human-readable view of the Reflector's memory. Read-only."""
    store = VerdictStore(db_path=db_path) if db_path else VerdictStore()
    reflector = Reflector(store)
    out: list[str] = []

    if stats:
        s = reflector.get_stats()
        out += [
            "Reflector stats",
            f"  verdicts : {s['verdict_count']}",
            f"  idioms   : {s['idiom_count']}",
            f"  store    : {s['store_path']}",
        ]

    if idioms:
        tops = reflector.get_top_idioms(min_decay=0.0, limit=limit)
        out.append(f"\nTop idioms ({len(tops)})")
        if not tops:
            out.append("  (none yet — confirmed divergences create idioms)")
        for i in tops:
            out.append(
                f"  [{i.decay_score:.2f} x{i.confirm_count}] "
                f"{i.divergence_class.value} {i.endpoint or '*'}: {i.pattern[:70]}"
            )

    if audit:
        out.append("\n" + audit_memory(store).render())

    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="cherenkov.reflector.cli",
        description="Inspect the Reflector's learned memory (E7).",
    )
    p.add_argument("--db", default=None, help="verdict store path (default .cherenkov/verdicts.db)")
    p.add_argument("--stats", action="store_true", help="show verdict/idiom counts")
    p.add_argument("--idioms", action="store_true", help="list ranked idioms")
    p.add_argument("--audit", action="store_true", help="run the memory self-audit")
    p.add_argument("--limit", type=int, default=20, help="max idioms to list")
    args = p.parse_args(argv)

    any_flag = args.stats or args.idioms or args.audit  # no flag → show all
    try:
        print(build_report(
            args.db,
            stats=args.stats or not any_flag,
            idioms=args.idioms or not any_flag,
            audit=args.audit or not any_flag,
            limit=args.limit,
        ))
    except sqlite3.OperationalError as e:
        # the verdict store is local SQLite; a concurrent run may hold the lock
        print(f"reflector store unavailable ({e}); another run may hold the lock — "
              "retry shortly.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
