"""
cherenkov/truth/emitters/spec_patch.py — E4-2: Spec-patch emitter.
Authority: v3.1 + delta.

Emit a unified diff patch against the OpenAPI spec when a spec divergence
is better resolved by updating the spec than by generating a test.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import DivergenceClass, DivergenceReport
from cherenkov.core.truth_model import TruthModel, NodeType
from cherenkov.truth.emitters.interface import Emitter


class SpecPatchEmitter(Emitter):
    """Emits a unified diff patch for spec divergences (D1, D4)."""

    def emit(
        self,
        truth_model: TruthModel,
        output_path: Path,
        divergences: list[DivergenceReport] | None = None,
        **kwargs: Any,
    ) -> Path:
        if not divergences:
            spec_divergences = []
        else:
            spec_divergences = [
                d for d in divergences
                if d.divergence_class in (DivergenceClass.D1_SPEC_CODE, DivergenceClass.D4_SPEC_DB)
            ]

        if not spec_divergences:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("", encoding="utf-8")
            return output_path

        patch_lines = []
        for d in spec_divergences:
            patch_lines.append(f"--- a/spec divergence: {d.endpoint_id}")
            patch_lines.append(f"+++ b/suggested fix: {d.description}")
            patch_lines.append(f"@@ -0,0 +1 @@")
            patch_lines.append(f"+# {d.description}")
            patch_lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(patch_lines), encoding="utf-8")
        return output_path
