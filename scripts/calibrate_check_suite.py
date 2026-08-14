#!/usr/bin/env python3
"""Calibrate `check-suite`'s detector against the shared integrity corpus.

Companion to `scripts/calibrate_integrity.py`, which scores
`cherenkov.integrity.api`. CHERENKOV ships **two** integrity detectors; #989
measured one and #990 rebuilt the other, neither against the other's data. This
scores the second one on the first one's corpus.

Why this is not just `calibrate_integrity.py` with a different import
-------------------------------------------------------------------
The two detectors answer different questions.

  `integrity/api.py`   absolute   — "can this test fail when the API is broken?"
                                    Needs only the test (plus optionally a spec).
  `check-suite`        differential — "did this test get *worse* than a baseline?"
                                    Needs a (baseline, candidate) pair.

The corpus is a set of individually-labelled tests. It has no baselines, so only
`check-suite`'s baseline-free path — HALLUCINATED, which is adjudicated against
the spec — can be exercised. Reporting one averaged recall across all nine
evasion classes would therefore be a dishonest headline: it would read as "this
detector is 7% accurate" when most of the corpus is asking a question this
detector was never built to answer.

So this harness partitions the classes by *why* a miss happened, and gates only
on what is actually in scope:

  IMPLEMENTED    check-suite claims this and is measured on it. Gated.
  UNIMPLEMENTED  a baseline-free detector could catch it; check-suite does not.
                 `integrity/api.py` does — this is the overlap where the two
                 detectors genuinely duplicate, and the input to any decision
                 about converging them. Reported, not gated.
  NEEDS_BASELINE structurally invisible without a baseline. Not a defect, and a
                 miss here is not evidence of anything. Reported, not gated.

False positives are gated across *all* classes: an honest test flagged is a
false positive no matter which question was being asked.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from cherenkov.cli.commands.check_suite import (  # noqa: E402
    _check_typescript,
    check_integrity,
)

CORPUS = REPO / "bench" / "integrity_corpus" / "cases.yaml"

# Why each evasion class is or is not check-suite's job. Keyed by the corpus's
# own `class` values so a new class added there shows up as unmapped rather than
# being silently averaged in.
SCOPE: dict[str, str] = {
    "hallucinated": "IMPLEMENTED",
    "spec_mismatch": "UNIMPLEMENTED",
    "tautology": "UNIMPLEMENTED",
    "no_assertion": "UNIMPLEMENTED",
    "disabled": "UNIMPLEMENTED",
    "swallowed": "UNIMPLEMENTED",
    "always_true": "UNIMPLEMENTED",
    "weakened_status": "NEEDS_BASELINE",
    "deleted_coverage": "NEEDS_BASELINE",
}


def load_corpus(path: Path) -> tuple[list[dict[str, Any]], Path]:
    """Load the labelled cases and resolve the spec they are adjudicated against."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    spec_ref = doc.get("spec")
    if not spec_ref:
        raise ValueError(f"corpus has no `spec:` key: {path}")
    spec_path = (path.parent / spec_ref).resolve()
    if not spec_path.exists():
        raise FileNotFoundError(f"corpus references a missing spec: {spec_path}")
    cases = doc.get("cases") or []
    if not cases:
        raise ValueError(f"no cases found in {path}")
    return cases, spec_path


def audit_case(case: dict[str, Any], spec_path: Path) -> dict[str, Any]:
    """Run one case through check-suite's baseline-free path."""
    content = case["content"]
    fmt = case["format"]
    try:
        if fmt == "playwright":
            findings = _check_typescript(content, None, spec_path)
        else:
            # Empty baseline: the differential comparison yields nothing, so only
            # the spec-adjudicated HALLUCINATED path can fire.
            findings = check_integrity(spec_path, "", content)
        error = None
    except Exception as exc:  # noqa: BLE001 — a crash is a result worth reporting
        findings, error = [], f"{type(exc).__name__}: {exc}"

    cls = case.get("class")
    return {
        "id": case["id"],
        "format": fmt,
        "label": case["label"],
        "class": cls,
        "scope": SCOPE.get(cls, "UNMAPPED") if cls else None,
        "flagged": bool(findings),
        "findings": findings,
        "error": error,
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-class outcomes, partitioned by scope."""
    honest = [r for r in rows if r["label"] == "honest"]
    dishonest = [r for r in rows if r["label"] == "dishonest"]
    false_pos = [r for r in honest if r["flagged"]]

    by_class: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dishonest:
        grouped[row["class"] or "unclassified"].append(row)
    for cls, group in sorted(grouped.items()):
        hits = [r for r in group if r["flagged"]]
        by_class[cls] = {
            "scope": SCOPE.get(cls, "UNMAPPED"),
            "total": len(group),
            "detected": len(hits),
            "recall": round(len(hits) / len(group), 3),
            "missed": sorted(r["id"] for r in group if not r["flagged"]),
        }

    in_scope = [r for r in dishonest if r["scope"] == "IMPLEMENTED"]
    in_scope_hits = [r for r in in_scope if r["flagged"]]

    return {
        "totals": {
            "cases": len(rows),
            "honest": len(honest),
            "dishonest": len(dishonest),
        },
        "in_scope_recall": (
            round(len(in_scope_hits) / len(in_scope), 3) if in_scope else 0.0
        ),
        "in_scope_total": len(in_scope),
        "in_scope_detected": len(in_scope_hits),
        "false_positive_rate": (
            round(len(false_pos) / len(honest), 3) if honest else 0.0
        ),
        "false_positive_ids": sorted(r["id"] for r in false_pos),
        "errors": sorted(r["id"] for r in rows if r["error"]),
        "by_class": by_class,
    }


def render(summary: dict[str, Any]) -> str:
    t = summary["totals"]
    out: list[str] = ["", "CHERENKOV — check-suite detector calibration", "=" * 66]
    out.append(
        f"corpus: {t['cases']} cases  ({t['honest']} honest, {t['dishonest']} dishonest)"
    )
    out.append("")
    out.append(
        f"  in-scope recall      {summary['in_scope_recall']:.1%}   "
        f"({summary['in_scope_detected']}/{summary['in_scope_total']} "
        f"IMPLEMENTED-class cases)"
    )
    out.append(
        f"  false positive rate  {summary['false_positive_rate']:.1%}   "
        f"(honest tests flagged — gated across all classes)"
    )
    out.append("")
    out.append("  per class:")
    order = {"IMPLEMENTED": 0, "UNIMPLEMENTED": 1, "NEEDS_BASELINE": 2, "UNMAPPED": 3}
    for cls, d in sorted(
        summary["by_class"].items(), key=lambda kv: (order.get(kv[1]["scope"], 9), kv[0])
    ):
        out.append(
            f"    {d['scope']:<15s} {cls:<18s} {d['detected']}/{d['total']}"
        )
    if summary["false_positive_ids"]:
        out.append("")
        out.append("  FALSE POSITIVES:")
        out.extend(f"    {i}" for i in summary["false_positive_ids"])
    if summary["errors"]:
        out.append("")
        out.append("  ERRORED:")
        out.extend(f"    {i}" for i in summary["errors"])
    out.append("")
    out.append(
        "  NEEDS_BASELINE misses are not defects: check-suite is a differential\n"
        "  detector and the corpus carries no baselines. UNIMPLEMENTED is the\n"
        "  overlap with cherenkov/integrity/api.py — see HANDOVER.md."
    )
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--min-in-scope-recall",
        type=float,
        help="fail if recall over IMPLEMENTED-class cases falls below this",
    )
    parser.add_argument(
        "--max-fpr", type=float, help="fail if the false positive rate exceeds this"
    )
    args = parser.parse_args()

    cases, spec_path = load_corpus(args.corpus)
    rows = [audit_case(c, spec_path) for c in cases]
    summary = summarise(rows)
    print(render(summary))

    if args.json_out:
        args.json_out.write_text(
            json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n",
            encoding="utf-8",
        )

    failed = False
    if args.max_fpr is not None and summary["false_positive_rate"] > args.max_fpr:
        print(
            f"GATE FAIL: false positive rate {summary['false_positive_rate']:.1%} "
            f"exceeds {args.max_fpr:.1%}"
        )
        failed = True
    if (
        args.min_in_scope_recall is not None
        and summary["in_scope_recall"] < args.min_in_scope_recall
    ):
        print(
            f"GATE FAIL: in-scope recall {summary['in_scope_recall']:.1%} "
            f"below {args.min_in_scope_recall:.1%}"
        )
        failed = True
    if summary["errors"]:
        print(f"GATE FAIL: {len(summary['errors'])} case(s) crashed the detector")
        failed = True

    unmapped = sorted(
        {c for c, d in summary["by_class"].items() if d["scope"] == "UNMAPPED"}
    )
    if unmapped:
        print(
            "GATE FAIL: corpus classes with no scope mapping — add them to SCOPE "
            f"in this script: {', '.join(unmapped)}"
        )
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
