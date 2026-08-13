"""
scripts/calibrate_integrity.py — calibration harness for the integrity detector.

Runs `cherenkov.integrity.api.audit_test_integrity` over the hand-labelled corpus
at bench/integrity_corpus/cases.yaml and reports what the detector actually
catches, as measurable rates rather than as a claim.

Reported metrics
----------------
recall              detected / dishonest          — how much dishonesty is caught
false_positive_rate flagged   / honest            — how often honest tests are accused
false_certificates  dishonest cases handed a signed certificate (score >= 0.90)

`false_certificates` is the metric that matters most. A miss is a gap; a
certificate issued to a test that cannot fail is the auditor actively asserting
something untrue, which is worse than having no auditor at all.

Recall is also broken out per evasion class, because a single averaged number
hides whether a failure mode is partly caught or wholly invisible.

Usage
-----
    python scripts/calibrate_integrity.py
    python scripts/calibrate_integrity.py --json-out bench/integrity-calibration.json
    python scripts/calibrate_integrity.py --min-recall 0.90 --max-fpr 0.05 --max-false-certificates 0
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from cherenkov.integrity.api import IntegrityAuditRequest, audit_test_integrity

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "bench" / "integrity_corpus" / "cases.yaml"


def load_corpus(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Load the labelled cases and the spec they are adjudicated against."""
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    spec_content: str | None = None
    spec_ref = doc.get("spec")
    if spec_ref:
        spec_path = (path.parent / spec_ref).resolve()
        if not spec_path.exists():
            raise FileNotFoundError(f"corpus references a missing spec: {spec_path}")
        spec_content = spec_path.read_text(encoding="utf-8")

    cases = doc.get("cases") or []
    if not cases:
        raise ValueError(f"no cases found in {path}")
    return cases, spec_content


def audit_case(case: dict[str, Any], spec_content: str | None) -> dict[str, Any]:
    """Run one case through the detector and record what came back."""
    result = audit_test_integrity(
        IntegrityAuditRequest(
            test_content=case["content"],
            spec_content=spec_content,
            test_format=case["format"],
            agent_id="calibration-harness",
        )
    )
    return {
        "id": case["id"],
        "format": case["format"],
        "label": case["label"],
        "class": case.get("class"),
        "flagged": len(result.issues) > 0,
        "verdict": result.verdict.value,
        "score": result.integrity_score,
        "certificate": result.certificate is not None,
        "issue_types": sorted({i.issue_type.value for i in result.issues}),
    }


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn per-case outcomes into the reported rates."""
    honest = [r for r in rows if r["label"] == "honest"]
    dishonest = [r for r in rows if r["label"] == "dishonest"]

    detected = [r for r in dishonest if r["flagged"]]
    false_pos = [r for r in honest if r["flagged"]]
    false_certs = [r for r in dishonest if r["certificate"]]

    per_class: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dishonest:
        grouped[row["class"] or "unclassified"].append(row)
    for cls, group in sorted(grouped.items()):
        hits = [r for r in group if r["flagged"]]
        per_class[cls] = {
            "total": len(group),
            "detected": len(hits),
            "recall": round(len(hits) / len(group), 3),
            "missed": sorted(r["id"] for r in group if not r["flagged"]),
        }

    return {
        "totals": {
            "cases": len(rows),
            "honest": len(honest),
            "dishonest": len(dishonest),
        },
        "recall": round(len(detected) / len(dishonest), 3) if dishonest else 0.0,
        "false_positive_rate": round(len(false_pos) / len(honest), 3) if honest else 0.0,
        "false_certificates": len(false_certs),
        "false_certificate_ids": sorted(r["id"] for r in false_certs),
        "false_positive_ids": sorted(r["id"] for r in false_pos),
        "recall_by_class": per_class,
    }


def render(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Human-readable report."""
    t = summary["totals"]
    out: list[str] = []
    out.append("")
    out.append("CHERENKOV — integrity detector calibration")
    out.append("=" * 62)
    out.append(f"corpus: {t['cases']} cases  ({t['honest']} honest, {t['dishonest']} dishonest)")
    out.append("")
    out.append(f"  recall               {summary['recall']:.1%}   (dishonest tests flagged)")
    out.append(f"  false positive rate  {summary['false_positive_rate']:.1%}   (honest tests flagged)")
    out.append(f"  false certificates   {summary['false_certificates']}      (dishonest tests handed a signed certificate)")
    out.append("")
    out.append("recall by evasion class")
    out.append("-" * 62)
    for cls, stats in summary["recall_by_class"].items():
        bar = "#" * int(stats["recall"] * 20)
        out.append(f"  {cls:<16} {stats['detected']:>2}/{stats['total']:<2} {stats['recall']:>6.1%}  {bar}")
    out.append("")

    missed = [r for r in rows if r["label"] == "dishonest" and not r["flagged"]]
    if missed:
        out.append(f"undetected dishonest tests ({len(missed)})")
        out.append("-" * 62)
        for r in missed:
            cert = "  <-- CERTIFIED" if r["certificate"] else ""
            out.append(f"  {r['id']:<28} {r['verdict']:<5} score={r['score']:.3f}{cert}")
        out.append("")

    fp = [r for r in rows if r["label"] == "honest" and r["flagged"]]
    if fp:
        out.append(f"false positives ({len(fp)})")
        out.append("-" * 62)
        for r in fp:
            out.append(f"  {r['id']:<28} {r['verdict']:<5} {','.join(r['issue_types'])}")
        out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", type=Path, default=CORPUS, help="labelled corpus YAML")
    parser.add_argument("--json-out", type=Path, help="write the full report as JSON")
    parser.add_argument("--min-recall", type=float, help="fail if recall falls below this")
    parser.add_argument("--max-fpr", type=float, help="fail if the false positive rate exceeds this")
    parser.add_argument(
        "--max-false-certificates",
        type=int,
        help="fail if more than this many dishonest tests receive a certificate",
    )
    args = parser.parse_args()

    cases, spec_content = load_corpus(args.corpus)
    rows = [audit_case(c, spec_content) for c in cases]
    summary = summarise(rows)

    print(render(summary, rows))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps({"summary": summary, "cases": rows}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            written = args.json_out.resolve().relative_to(REPO_ROOT)
        except ValueError:
            written = args.json_out
        print(f"wrote {written}")

    failures: list[str] = []
    if args.min_recall is not None and summary["recall"] < args.min_recall:
        failures.append(f"recall {summary['recall']:.3f} < required {args.min_recall:.3f}")
    if args.max_fpr is not None and summary["false_positive_rate"] > args.max_fpr:
        failures.append(
            f"false positive rate {summary['false_positive_rate']:.3f} > allowed {args.max_fpr:.3f}"
        )
    if args.max_false_certificates is not None and summary["false_certificates"] > args.max_false_certificates:
        failures.append(
            f"{summary['false_certificates']} false certificates > allowed {args.max_false_certificates}"
        )

    if failures:
        print("GATE FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
