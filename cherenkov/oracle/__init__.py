# CHERENKOV oracle package (E4-3).

from cherenkov.oracle.interface import Oracle, OracleResult
from cherenkov.oracle.spec_prism import SpecPrismOracle
from cherenkov.oracle.prod_snapshot import ProdSnapshotOracle
from cherenkov.oracle.visual_oracle import VisualOracle, classify_visual_change

__all__ = [
    "Oracle",
    "OracleResult",
    "SpecPrismOracle",
    "ProdSnapshotOracle",
    "VisualOracle",
    "classify_visual_change",
]
