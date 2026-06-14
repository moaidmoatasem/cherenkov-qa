"""
cherenkov/truth/emitters/unit_test.py — E11-3: Unit-test emitter (pytest/jest).

Follows the Emitter SPI from interface.py. Wraps the existing UnitTestEmitter
from cherenkov/coverage/emitter.py to produce standalone pytest/jest tests
from the Truth Model endpoints. Anti-lock-in: generated tests have zero
CHERENKOV dependency.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import DivergenceReport
from cherenkov.core.errors import get_logger
from cherenkov.core.truth_model import TruthModel
from cherenkov.coverage.emitter import UnitTestEmitter as CoreEmitter
from cherenkov.truth.emitters.interface import Emitter


class UnitTestEmitter(Emitter):
    """Emits standalone unit tests (pytest/jest) from the Truth Model.

    Supports two output frameworks:
    - ``pytest``: Python unittest-style with requests library
    - ``jest``: TypeScript with node-fetch

    Generated tests are designed to eject with zero CHERENKOV dependency.
    """

    def __init__(self, run_id: str | None = None) -> None:
        self._run_id = run_id
        self._log = get_logger("UNIT_EMITTER", run_id)
        self._core = CoreEmitter(run_id=run_id)

    def emit(
        self,
        truth_model: TruthModel,
        output_path: Path,
        divergences: list[DivergenceReport] | None = None,
        **kwargs: Any,
    ) -> Path:
        framework = kwargs.get("framework", "pytest")
        base_url = kwargs.get("base_url", "")
        if framework not in ("pytest", "jest"):
            raise ValueError(
                f"Unknown framework '{framework}'. Use 'pytest' or 'jest'."
            )

        output_dir = str(output_path)
        endpoints = truth_model.get_endpoints()

        slice_data_list = []
        for ep in endpoints:
            label = ep.label
            parts = label.split(" ", 1)
            method = parts[0].lower() if len(parts) == 2 else "get"
            path = parts[1] if len(parts) == 2 else label
            operation = ep.properties.get("operation", ep.properties)

            slice_data_list.append(
                {
                    "path": path,
                    "method": method,
                    "operation": operation,
                    "summary": ep.properties.get("summary", ""),
                }
            )

        self._log.info(
            "emitting unit tests",
            count=len(slice_data_list),
            framework=framework,
            output_dir=output_dir,
        )

        results = self._core.emit(
            endpoint_slices=slice_data_list,
            output_dir=output_dir,
            framework=framework,
            base_url=base_url,
        )

        # Return the path to the first generated file, or the output dir
        if results:
            for r in results:
                if r.status.value == "ok" and r.test_code:
                    ext = ".py" if framework == "pytest" else ".ts"
                    scenario = r.scenario_id
                    first_file = os.path.join(output_dir, f"{scenario}{ext}")
                    if os.path.exists(first_file):
                        return Path(first_file)

        return Path(output_dir)
