"""
CHERENKOV divergence — Epoch 3 Divergence Engine (L2).

Exports the three primary agents:
  SkepticAgent    — generates DivergenceHypothesis list from spec claims
  WitnessAgent    — deterministically reproduces or rejects each hypothesis
  AdversarialSelfPlay — kills tautological tests before they ship
"""
from cherenkov.divergence.skeptic import SkepticAgent
from cherenkov.divergence.witness import WitnessAgent
from cherenkov.divergence.self_play import AdversarialSelfPlay, BrokenImplServer, SelfPlayResult

__all__ = [
    "SkepticAgent",
    "WitnessAgent",
    "AdversarialSelfPlay",
    "BrokenImplServer",
    "SelfPlayResult",
]
