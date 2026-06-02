"""
cherenkov/truth/emitters/interface.py — E4-1: Artifact Emitter SPI.
Authority: v3.1 + delta.

Plugin interface for outputs. Each emitter produces an artifact from a truth model
or divergence report.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

from cherenkov.core.contracts import DivergenceReport
from cherenkov.core.truth_model import TruthModel


class Emitter(abc.ABC):
    """Abstract base class for artifact emitters.

    Each emitter takes a TruthModel (and optionally divergences) and produces
    an artifact at the given output path.
    """

    @abc.abstractmethod
    def emit(
        self,
        truth_model: TruthModel,
        output_path: Path,
        divergences: list[DivergenceReport] | None = None,
        **kwargs: Any,
    ) -> Path:
        """Emit an artifact to output_path and return the path to the produced file(s).

        Args:
            truth_model: The current TruthModel.
            output_path: Directory or file path for output.
            divergences: Optional list of divergence reports to include.
            **kwargs: Emitter-specific options.

        Returns:
            Path to the produced artifact(s).
        """
        pass
