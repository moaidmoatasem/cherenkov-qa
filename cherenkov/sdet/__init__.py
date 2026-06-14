"""
CHERENKOV sdet/ — Epoch 11 Coverage SDET.

Two capabilities that turn the generator into a self-driving SDET:

  * assertion_gate — E11-2: a meaningful-assertion gate that rejects
    tautological tests via the adversarial self-play broken-impl run.
  * coverage_loop  — E11-1: a bounded generate→run→read-trace→repair loop
    that drives meaningful, passing coverage to a configured threshold.

Both are orchestrators over injected callables (generate / run / repair), so
they are deterministic and unit-testable without a live model or server —
mirroring the design of `divergence/self_play.py`.
"""

from cherenkov.sdet.assertion_gate import MeaningfulAssertionGate
from cherenkov.sdet.coverage_loop import CoverageLoop, RunOutcome

__all__ = ["MeaningfulAssertionGate", "CoverageLoop", "RunOutcome"]
