from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow


class APKParser:
    """Parse Android APK metadata via `aapt dump badging`."""

    def parse(self, apk_path: str) -> MobileApp:
        apk = Path(apk_path)
        if not apk.exists():
            raise FileNotFoundError(f"APK not found: {apk_path}")

        try:
            result = subprocess.run(
                ["aapt", "dump", "badging", str(apk.resolve())],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            raise RuntimeError("aapt not found on PATH; install Android SDK build-tools")

        if result.returncode != 0:
            raise RuntimeError(f"aapt dump failed: {result.stderr.strip()}")

        lines = result.stdout.splitlines()
        app_id = ""
        name = ""
        version = ""

        for line in lines:
            if line.startswith("package:"):
                for part in line.split():
                    if part.startswith("name="):
                        app_id = part.split("=", 1)[1].strip("'")
                    elif part.startswith("versionName="):
                        version = part.split("=", 1)[1].strip("'")
            elif line.startswith("application-label:"):
                name = line.split(":", 1)[1].strip("'")

        return MobileApp(
            app_id=app_id or apk.stem,
            name=name or apk.stem,
            platform="android",
            version=version or "0.0.0",
            package_path=str(apk.resolve()),
        )


class HARParser:
    """Parse HTTP Archive (HAR) files and extract request/response entries."""

    def parse(self, har_path: str) -> list[dict[str, Any]]:
        har = Path(har_path)
        if not har.exists():
            raise FileNotFoundError(f"HAR file not found: {har_path}")

        raw = har.read_text(encoding="utf-8")
        data = json.loads(raw)

        entries = data.get("log", {}).get("entries", [])
        if not entries:
            entries = data.get("entries", [])

        results: list[dict[str, Any]] = []
        for entry in entries:
            req = entry.get("request", {})
            res = entry.get("response", {})
            results.append(
                {
                    "url": req.get("url", ""),
                    "method": req.get("method", "GET").upper(),
                    "status": res.get("status", 0),
                }
            )

        return results


class HILParser:
    """Parse HIL (Human Interface Log) trace files into MobileFlow objects."""

    def parse(self, hil_path: str) -> list[MobileFlow]:
        hil = Path(hil_path)
        if not hil.exists():
            raise FileNotFoundError(f"HIL file not found: {hil_path}")

        raw = hil.read_text(encoding="utf-8")
        data = json.loads(raw)

        if isinstance(data, list):
            items = data
        else:
            items = data.get("flows", [])

        flows: list[MobileFlow] = []
        for i, item in enumerate(items):
            flows.append(
                MobileFlow(
                    flow_id=item.get("flow_id", f"flow_{i}"),
                    name=item.get("name", f"Flow {i}"),
                    screens=item.get("screens", []),
                    actions=item.get("actions", []),
                )
            )

        return flows
