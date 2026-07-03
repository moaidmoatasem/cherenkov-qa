"""
Spec Guardian Daemon Watcher (Horizon 3)
Background process that monitors Git repos and APM telemetry.
"""

import time
import logging

import os
from pathlib import Path
from .trigger_loop import SpecGuardianTriggerLoop

logger = logging.getLogger(__name__)


class SpecGuardianWatcher:
    """
    Monitors target sources for drift or configuration changes.
    """

    def __init__(
        self,
        target_repo: str,
        target_url: str,
        source_type: str = "openapi",
        watch_files: list[str] = None,
    ):
        self.target_repo = Path(target_repo)
        self.watch_files = watch_files or ["openapi.yaml"]
        self.trigger_loop = SpecGuardianTriggerLoop(
            target_url=target_url, source_type=source_type
        )
        self._last_modified = {}

    def _get_mtime(self, file_path: Path) -> float:
        try:
            return os.path.getmtime(file_path)
        except OSError:
            return 0.0

    def start_watching(self, poll_interval: int = 10):
        """Begin the continuous background observation loop."""
        logger.info("Spec Guardian started watching %s", self.target_repo)

        # Initialize baselines
        for filename in self.watch_files:
            file_path = self.target_repo / filename
            self._last_modified[filename] = self._get_mtime(file_path)

        try:
            while True:
                for filename in self.watch_files:
                    file_path = self.target_repo / filename
                    current_mtime = self._get_mtime(file_path)

                    if current_mtime > self._last_modified[filename]:
                        logger.info("Detected change in %s", filename)
                        self._last_modified[filename] = current_mtime

                        # Trigger the D7-compliant validation loop
                        self.trigger_loop.trigger_validation(
                            {
                                "id": f"drift_{int(time.time())}",
                                "file_path": str(file_path),
                                "timestamp": current_mtime,
                            }
                        )

                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Spec Guardian stopping.")
