"""
CHERENKOV ai/interface.py — model-agnostic inference client seam.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import abc


class InferenceClient(abc.ABC):
    """Abstract base class representing an inference capability seam.

    This is the core seam that Epoch 1 (Substrate Router) will build upon.
    """

    @abc.abstractmethod
    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        max_reprompts: int = 2,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> dict:
        """Return a parsed JSON object from the model, or raise OllamaJSONError."""
        pass

    @abc.abstractmethod
    def complete_code(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        *,
        temperature: float = 0.1,
        run_id: str | None = None,
    ) -> str:
        """For the GENERATE stage: we want raw TS code, not JSON."""
        pass
