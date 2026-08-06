"""JourneyRegistry — discovers journey definitions from YAML.

Follows the same discovery contract as PlaybookRegistry
(``cherenkov/playbooks/registry.py``): a builtins directory shipped with the
package, plus a project-local ``.cherenkov/journeys`` that takes precedence, so
a team can retune or add a workflow without touching Python.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from cherenkov.journeys.contracts import JourneyDefinition

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtins"
# Project-local definitions load last so they win on id collision.
_DEFAULT_DIRS = [_BUILTIN_DIR, Path(".cherenkov/journeys")]

DEFAULT_JOURNEY_ID = "api-conformance"


class JourneyRegistry:
    def __init__(self, search_dirs: Sequence[Path | str] | None = None) -> None:
        self._journeys: dict[str, JourneyDefinition] = {}
        dirs = [Path(d) for d in search_dirs] if search_dirs is not None else _DEFAULT_DIRS
        for directory in dirs:
            self._load_dir(directory)

    @property
    def journeys(self) -> list[JourneyDefinition]:
        return list(self._journeys.values())

    def get(self, journey_id: str) -> JourneyDefinition | None:
        return self._journeys.get(journey_id)

    def default(self) -> JourneyDefinition | None:
        return self._journeys.get(DEFAULT_JOURNEY_ID) or next(
            iter(self._journeys.values()), None
        )

    def add(self, journey: JourneyDefinition) -> None:
        self._journeys[journey.id] = journey

    def load_file(self, path: Path | str) -> JourneyDefinition | None:
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed; cannot load journey files")
            return None

        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or "id" not in raw:
                logger.warning("Skipping %s: missing 'id' field", path)
                return None
            journey = JourneyDefinition.model_validate(raw)
        except Exception as exc:
            # A malformed user journey must not take down the engine: the
            # builtin is still there and the API reports what loaded.
            logger.warning("Failed to load journey from %s: %s", path, exc)
            return None

        if journey.id in self._journeys:
            logger.debug("Journey %r overridden by %s", journey.id, path)
        self._journeys[journey.id] = journey
        return journey

    def _load_dir(self, directory: Path) -> None:
        if not directory.is_dir():
            return
        for yaml_file in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            self.load_file(yaml_file)


_registry: JourneyRegistry | None = None


def get_journey_registry(refresh: bool = False) -> JourneyRegistry:
    global _registry
    if _registry is None or refresh:
        _registry = JourneyRegistry()
    return _registry
