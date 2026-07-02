"""PlaybookRegistry — loads Playbook definitions from YAML files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from cherenkov.playbooks.models import Playbook

logger = logging.getLogger(__name__)

_DEFAULT_DIRS = [
    Path(".cherenkov/playbooks"),
    Path("cherenkov/playbooks/builtins"),
]


class PlaybookRegistry:
    """Discovers and holds Playbook definitions loaded from YAML files.

    Scans `search_dirs` for ``*.yaml`` / ``*.yml`` files, parses each as a
    Playbook, and makes them available for matching.
    """

    def __init__(self, search_dirs: Sequence[Path | str] | None = None) -> None:
        self._playbooks: list[Playbook] = []
        dirs = [Path(d) for d in search_dirs] if search_dirs is not None else _DEFAULT_DIRS
        for d in dirs:
            self._load_dir(d)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def playbooks(self) -> list[Playbook]:
        return list(self._playbooks)

    def get(self, name: str) -> Playbook | None:
        for pb in self._playbooks:
            if pb.name == name:
                return pb
        return None

    def add(self, playbook: Playbook) -> None:
        self._playbooks.append(playbook)

    def load_file(self, path: Path | str) -> Playbook | None:
        """Parse a single YAML file and register it. Returns the Playbook or None."""
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed; cannot load playbook files")
            return None

        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text())
            if not isinstance(raw, dict) or "name" not in raw:
                logger.warning("Skipping %s: missing 'name' field", path)
                return None
            pb = Playbook.from_dict(raw, source_path=str(path))
            self._playbooks.append(pb)
            logger.debug("Loaded playbook '%s' from %s", pb.name, path)
            return pb
        except Exception as exc:
            logger.warning("Failed to load playbook from %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_dir(self, directory: Path) -> None:
        if not directory.exists():
            return
        count_before = len(self._playbooks)
        for yaml_file in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            self.load_file(yaml_file)
        logger.debug(
            "Loaded %d playbook(s) from %s", len(self._playbooks) - count_before, directory
        )
