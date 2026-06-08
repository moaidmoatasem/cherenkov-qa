"""
CHERENKOV healing/visual_heal.py — Epoch 9 Visual Self-Heal.
Suggest-only (Delta D7): analyses visual regression failures and
produces a healing suggestion, never auto-applies.
"""
from __future__ import annotations

import json

from cherenkov.core.errors import get_logger
from cherenkov.core.contracts import VisualGateResult, VisualReport, Verdict
from cherenkov.oracle.visual_oracle import VisualOracle, VisualChangeKind
from cherenkov.substrate.provider import get_vlm_provider
from cherenkov.substrate.router import route
from cherenkov.core.contracts import ReasoningRequest


class VisualHealer:
    """Analyses visual regression failures and produces suggest-only healing.

    Workflow:
    1. When pixel_diff gate fails, run the VisualOracle to classify the change.
    2. If REDESIGN: suggest updating the baseline snapshot.
    3. If ANOMALY: describe the broken elements for a developer to fix.
    4. If HARMLESS_SHIFT: suggest raising threshold or ignoring.
    5. Never auto-commits or auto-applies (Delta D7).
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("VISUAL_HEAL", run_id)
        self.oracle = VisualOracle()

    def suggest_heal(self, report: VisualReport) -> dict:
        """Analyse a failed VisualReport and produce a healing suggestion.

        Returns a structured dict with a 'suggestion' key containing the human-readable text.
        """
        if report.verdict == Verdict.AUTO_APPROVE:
            return {
                "healed": True,
                "healer": "VisualHealer",
                "scenario_id": report.scenario_id,
                "suggestion": "No healing needed — visual check passed.",
            }

        gate = next((g for g in report.gates if g.gate == "pixel_diff"), None)
        if gate is None:
            return {
                "healed": False,
                "healer": "VisualHealer",
                "scenario_id": report.scenario_id,
                "suggestion": "No pixel_diff gate found in report.",
            }

        diff_pixels = gate.diff_pixels

        classification = self._classify_change(
            baseline_path=gate.baseline_path,
            actual_path=gate.actual_path,
            diff_pixels=diff_pixels,
        )

        kind = classification.get("kind", VisualChangeKind.UNKNOWN)
        explanation = classification.get("explanation", "")
        confidence = classification.get("confidence", 0.0)

        lines = [
            f"[VISUAL HEAL] Scenario: {report.scenario_id}",
            f"Change classification: {kind} (confidence={confidence:.2f})",
            f"Explanation: {explanation}",
        ]

        if kind == VisualChangeKind.REDESIGN:
            lines.append("\nSUGGESTION: Intentional redesign detected.")
            lines.append("  → Update baseline snapshot: run with --update-snapshots or init_mode=True")
            lines.append("  → No code change needed — the UI was intentionally changed.")
        elif kind == VisualChangeKind.ANOMALY:
            anomalies = classification.get("anomalies", [])
            lines.append("\nSUGGESTION: Real UI anomaly detected.")
            if anomalies:
                lines.append("  Broken elements:")
                for a in anomalies:
                    lines.append(f"    - {a}")
            lines.append("  → Fix the UI issue, then re-run visual regression.")
        elif kind == VisualChangeKind.HARMLESS_SHIFT:
            lines.append("\nSUGGESTION: Harmless visual shift (anti-aliasing, scrollbar, etc.).")
            lines.append("  → Consider raising threshold_pixels on the VisualScenario.")
            lines.append("  → Or accept the shift — no functional impact.")
        else:
            lines.append("\nSUGGESTION: Cannot classify the change with confidence.")
            lines.append("  → Review the diff manually.")
            lines.append("  → If expected, run with --update-snapshots to rebaseline.")

        lines.append("\nNote: This is a SUGGESTION only (Delta D7). No files were modified.")

        return {
            "healed": False,
            "healer": "VisualHealer",
            "scenario_id": report.scenario_id,
            "kind": kind,
            "confidence": confidence,
            "explanation": explanation,
            "suggestion": "\n".join(lines),
        }

    def _classify_change(
        self,
        baseline_path: str,
        actual_path: str,
        diff_pixels: int,
    ) -> dict:
        """Classify the visual change using the oracle."""
        from cherenkov.core.contracts import Claim, Provenance, ProvenanceType

        claim = Claim(
            id="visual_heal_classify",
            category="visual_diff",
            subject="screenshot",
            value={"diff_pixels": diff_pixels},
            provenance=Provenance(source_type=ProvenanceType.SPEC, source_uri="visual_healer"),
        )
        result = self.oracle.evaluate(
            claim,
            baseline_path=baseline_path,
            actual_path=actual_path,
            diff_pixels=diff_pixels,
        )
        return {
            "kind": result.detail.split(" (confidence")[0] if result.detail else VisualChangeKind.UNKNOWN,
            "explanation": result.detail,
            "confidence": result.confidence,
            "anomalies": [],
            "is_correct": result.is_correct,
        }
