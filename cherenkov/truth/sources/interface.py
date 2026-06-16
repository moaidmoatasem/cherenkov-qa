"""
CHERENKOV truth/sources/interface.py — Source Adapter SPI interface.
"""

from __future__ import annotations

import abc
from cherenkov.core.contracts import Claim


class SourceAdapter(abc.ABC):
    """Abstract base class / plugin interface for all truth model source adapters.

    This enables normalized claims extraction from multiple sources of truth
    (such as specs, code, db schema, traffic, etc.).
    """

    @abc.abstractmethod
    def discover_claims(self, source_uri: str) -> list[Claim]:
        """Ingests a source at source_uri and returns a list of discovered Claims."""
        pass
