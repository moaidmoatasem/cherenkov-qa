"""
CHERENKOV reflector — Epoch 7 Reflector & Verdict Memory.

Net-new learning loop fed by healing/diagnose.py (FailureClass) +
divergence/witness.py (ReproductionResult) + human Verdict.

Exports:
  VerdictStore    — SQLite persistence for verdicts and idioms
  Reflector       — consumes verdicts, reranks Skeptic hypotheses, accumulates idioms
"""
from cherenkov.reflector.store import VerdictStore
from cherenkov.reflector.reflector import Reflector

__all__ = [
    "VerdictStore",
    "Reflector",
]
