"""
CHERENKOV reflector — Epoch 7 Reflector & Verdict Memory.

Net-new learning loop fed by healing/diagnose.py (FailureClass) +
divergence/witness.py (ReproductionResult) + human Verdict.

Exports:
  VerdictStore    — SQLite persistence for verdicts and idioms
  Reflector       — consumes verdicts, reranks Skeptic hypotheses, accumulates idioms
  get_reflector   — process-wide Reflector singleton (used by MCP chat tools)
"""

from cherenkov.reflector.store import VerdictStore
from cherenkov.reflector.reflector import Reflector, get_reflector

__all__ = [
    "VerdictStore",
    "Reflector",
    "get_reflector",
]
