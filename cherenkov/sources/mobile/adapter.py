from __future__ import annotations

from pathlib import Path
from typing import Any

from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow
from cherenkov.sources.mobile.parsers import APKParser, HARParser, HILParser


class MobileSourceAdapter:
    """Adapter that ingests mobile-related source files and dispatches to the
    appropriate parser based on file extension."""

    def __init__(
        self,
        apk_parser: APKParser | None = None,
        har_parser: HARParser | None = None,
        hil_parser: HILParser | None = None,
    ) -> None:
        self._apk_parser = apk_parser or APKParser()
        self._har_parser = har_parser or HARParser()
        self._hil_parser = hil_parser or HILParser()

    def ingest(self, source_path: str) -> MobileApp | list[dict[str, Any]] | list[MobileFlow]:
        """Detect file type by extension and delegate to the matching parser.

        Supported extensions:
          - .apk  -> APKParser  -> MobileApp
          - .har  -> HARParser  -> list[dict]
          - .hil  -> HILParser  -> list[MobileFlow]
        """
        path = Path(source_path)
        suffix = path.suffix.lower()

        if suffix == ".apk":
            return self._apk_parser.parse(source_path)
        elif suffix == ".har":
            return self._har_parser.parse(source_path)
        elif suffix == ".hil":
            return self._hil_parser.parse(source_path)
        else:
            raise ValueError(
                f"Unsupported mobile source file: {suffix} "
                f"(expected .apk, .har, or .hil)"
            )
