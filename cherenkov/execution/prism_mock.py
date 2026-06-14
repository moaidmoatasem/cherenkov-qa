"""
CHERENKOV execution/prism_mock.py — dynamic mock server using Stoplight/Prism inside Docker.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import os
import subprocess
import time
import requests
from cherenkov.core.errors import get_logger


class PrismMockServer:
    """Manages the lifecycle of an ephemeral dynamic Stoplight Prism mock server in Docker."""

    def __init__(self, spec_path: str, port: int = 4010, run_id: str | None = None):
        self.spec_path = os.path.abspath(spec_path)
        self.port = port
        self.run_id = run_id or "default"
        self.container_name = f"cherenkov-prism-{self.run_id}"
        self.log = get_logger("PRISM", self.run_id)

    def start(self) -> bool:
        """Pulls the Prism image (if missing), starts the container, and blocks until healthy."""
        self.log.info(
            "starting prism container", container=self.container_name, port=self.port
        )

        # 1. Force teardown of any pre-existing container with same name
        self.stop()

        # 2. Run the Prism container dynamically mounting the spec
        cmd = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            self.container_name,
            "-p",
            f"{self.port}:4010",
            "-v",
            f"{self.spec_path}:/spec.json:ro",
            "stoplight/prism:5",
            "mock",
            "-h",
            "0.0.0.0",
            "--multiprocess=false",
            "/spec.json",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            self.log.error("failed to start prism container", error=e.stderr)
            return False

        # 3. Wait for the mock server to respond to requests
        url = f"http://localhost:{self.port}"
        max_attempts = 15
        for attempt in range(1, max_attempts + 1):
            try:
                # We hit health or query the root to verify server is listening
                resp = requests.get(url, timeout=1)
                self.log.info("prism dynamic mock server is online", attempts=attempt)
                return True
            except requests.RequestException:
                time.sleep(0.5)

        self.log.error("prism dynamic mock server failed to respond in time")
        self.stop()
        return False

    def stop(self) -> None:
        """Forces stop and removal of the ephemeral Prism container."""
        # Stop and remove the container
        stop_cmd = ["docker", "stop", self.container_name]
        try:
            subprocess.run(stop_cmd, capture_output=True, text=True)
            self.log.info(
                "prism container stopped and removed", container=self.container_name
            )
        except Exception:
            pass
