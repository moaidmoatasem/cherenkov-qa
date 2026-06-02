"""
cherenkov/oracle/interface.py — E4-3: Oracle SPI.
Authority: v3.1 + delta.

Pluggable definition of 'correct'. Each oracle evaluates whether an observed
system behaviour matches the expected 'correct' behaviour.
"""

from __future__ import annotations

import abc
from typing import Any

from cherenkov.core.contracts import Claim


class OracleResult:
    """Result of an oracle evaluation."""

    def __init__(
        self,
        is_correct: bool,
        confidence: float = 1.0,
        detail: str = "",
        expected: Any = None,
        actual: Any = None,
    ):
        self.is_correct = is_correct
        self.confidence = confidence
        self.detail = detail
        self.expected = expected
        self.actual = actual


class Oracle(abc.ABC):
    """Abstract base class for oracles.

    Each oracle defines what 'correct' means for a given claim about the system.
    """

    @abc.abstractmethod
    def evaluate(self, claim: Claim, **kwargs: Any) -> OracleResult:
        """Evaluate whether the claim matches the oracle's definition of correct.

        Args:
            claim: The claim to evaluate.
            **kwargs: Oracle-specific context.

        Returns:
            OracleResult indicating correctness.
        """
        pass
