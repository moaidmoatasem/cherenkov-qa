"""
scripts/audit_repo_suites.py — run the integrity detector over every real test
file in this repository.

Why this exists
---------------
`scripts/calibrate_integrity.py` scores the detector against a corpus written
alongside it, so a perfect result there proves only that known evasions stay
caught. This script points the same detector at ~600 test files that nobody
wrote to exercise its rules, which is the only way to see the failure modes the
corpus cannot contain.

It earned its place: on first run it exposed three detector defects that the
corpus scored 100% through.

  * `test.beforeEach` / `test.beforeAll` were matched as test declarations, so
    lifecycle hooks — which correctly contain no assertions — were reported as
    empty tests.
  * unittest.TestCase assertions are calls, not `assert` statements, so most of
    this repo's own pytest files were reported as having no assertions at all.
  * `toBeGreaterThan(0)` was conflated with `toBeGreaterThanOrEqual(0)`, so
    every generated test asserting a non-empty collection was flagged.

Not a gate
----------
This reports; it does not fail. A nonzero flag rate here is expected and
correct — the repo deliberately ships weakened and cheat fixtures for its own
demos, and they *should* be flagged. Turning this into a pass/fail threshold
would either freeze in today's false positives or pressure someone into
weakening the detector to make a number go green, which is the exact failure
this whole subsystem exists to catch. Read the split and judge.

Usage
-----
    PYTHONPATH=. python scripts/audit_repo_suites.py
    PYTHONPATH=. python scripts/audit_repo_suites.py --samples 10
    PYTHONPATH=. python scripts/audit_repo_suites.py --json-out /tmp/audit.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cherenkov.integrity.api import IntegrityAuditRequest, audit_test_integrity

REPO_ROOT = Path(__file__).resolve().parents[1]

_SKIP_PARTS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", "target"}

# Written to exercise the detector — excluded so this stays held-out.
_OWN = ("bench/integrity_corpus", "tests/unit/test_integrity_calibration.py")

# Fixtures this repo ships *deliberately* broken, for its own demos and golden
# tests. Flagging them is the detector working, not failing, so they are
# reported separately rather than mixed into the headline rate.
_DELIBERATE = re.compile(
    r"weaken|cheat|deleted|broken|bad_|_bad|mutant|demo_|golden_|dishonest|tamper",
    re.IGNORECASE,
)


def collect(root: Path) -> list[tuple[Path, str]]:
    """Every Playwright spec and pytest module in the tree, with its format."""
    found: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in _SKIP_PARTS for part in path.parts):
            continue
        relative = str(path.relative_to(root))
        if any(own in relative for own in _OWN):
            continue
        if path.suffix == ".ts" and (".spec." in path.name or ".test." in path.name):
            found.append((path, "playwright"))
        elif path.suffix == ".py" and path.name.startswith("test_"):
            found.append((path, "pytest"))
    return found


def run(root: Path, sample_limit: int) -> dict[str, Any]:
    verdicts: Counter[str] = Counter()
    issue_types: Counter[str] = Counter()
    by_tree: dict[str, Counter[str]] = defaultdict(Counter)
    by_intent: dict[str, Counter[str]] = defaultdict(Counter)
    samples: dict[str, list[str]] = defaultdict(list)
    crashes: list[str] = []

    for path, fmt in collect(root):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not content.strip():
            continue

        relative = path.relative_to(root)
        try:
            result = audit_test_integrity(
                IntegrityAuditRequest(test_content=content, test_format=fmt)
            )
        except Exception as exc:  # a crash is itself a finding
            crashes.append(f"{relative}: {type(exc).__name__}: {exc}")
            continue

        intent = "deliberate" if _DELIBERATE.search(path.name) else "ordinary"
        flagged = "flagged" if result.issues else "clean"
        verdicts[result.verdict.value] += 1
        by_tree[relative.parts[0]][flagged] += 1
        by_intent[intent][flagged] += 1

        for issue in result.issues:
            issue_types[issue.issue_type.value] += 1
            bucket = samples[issue.issue_type.value]
            if len(bucket) < sample_limit:
                bucket.append(f"{relative}:{issue.line} — {issue.detail[:90]}")

    total = sum(verdicts.values())
    return {
        "total": total,
        "verdicts": dict(verdicts),
        "issue_types": dict(issue_types.most_common()),
        "by_tree": {k: dict(v) for k, v in by_tree.items()},
        "by_intent": {k: dict(v) for k, v in by_intent.items()},
        "samples": dict(samples),
        "crashes": crashes,
    }


def _rate(counts: dict[str, int]) -> tuple[int, int, float]:
    flagged = counts.get("flagged", 0)
    total = flagged + counts.get("clean", 0)
    return flagged, total, (flagged / total if total else 0.0)


def render(report: dict[str, Any]) -> str:
    out: list[str] = ["", "=" * 74]
    out.append(f"HELD-OUT AUDIT — {report['total']} real test files")
    out.append("=" * 74)

    for verdict in ("PASS", "WEAK", "FAIL"):
        count = report["verdicts"].get(verdict, 0)
        share = count / report["total"] if report["total"] else 0.0
        out.append(f"  {verdict:<5} {count:>5}  {share:>6.1%}")

    out.append("")
    out.append("flag rate by intent  (the split that matters)")
    out.append("-" * 74)
    for intent in ("deliberate", "ordinary"):
        counts = report["by_intent"].get(intent, {})
        if not counts:
            continue
        flagged, total, rate = _rate(counts)
        note = (
            "fixtures shipped broken on purpose — flagging these is correct"
            if intent == "deliberate"
            else "ordinary tests — every flag here needs adjudicating by hand"
        )
        out.append(f"  {intent:<12} {flagged:>4}/{total:<4} {rate:>6.1%}   {note}")

    out.append("")
    out.append("issues by type")
    out.append("-" * 74)
    for issue_type, count in report["issue_types"].items():
        out.append(f"  {issue_type:<24} {count:>5}")

    out.append("")
    out.append("flag rate by tree")
    out.append("-" * 74)
    trees = sorted(report["by_tree"].items(), key=lambda kv: -sum(kv[1].values()))
    for tree, counts in trees:
        flagged, total, rate = _rate(counts)
        out.append(f"  {tree:<28} {flagged:>4}/{total:<4} {rate:>6.1%}")

    if report["crashes"]:
        out.append("")
        out.append(f"CRASHES ({len(report['crashes'])}) — the auditor failing is a finding")
        out.append("-" * 74)
        out.extend(f"  {c}" for c in report["crashes"][:20])

    out.append("")
    out.append("samples")
    out.append("-" * 74)
    for issue_type, entries in report["samples"].items():
        out.append(f"\n[{issue_type}]")
        out.extend(f"  {entry}" for entry in entries)

    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--samples", type=int, default=6, help="samples per issue type")
    parser.add_argument("--json-out", type=Path, help="write the full report as JSON")
    args = parser.parse_args()

    report = run(args.root, args.samples)
    if not report["total"]:
        print("no test files found")
        return 1

    print(render(report))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
