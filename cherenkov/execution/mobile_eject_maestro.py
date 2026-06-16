"""
CHERENKOV execution/mobile_eject_maestro.py — Maestro YAML ejector.
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from cherenkov.core.errors import get_logger


class MaestroEjector:
    """Ejects standalone Maestro YAML test files from a multi-test input,
    stripping all CHERENKOV imports (anti-lock-in)."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "maestro-eject"
        self.log = get_logger("MAESTRO_EJECT", self.run_id)

    def eject(self, yaml_content: str, output_dir: str) -> Path:
        """Parses a multi-test Maestro YAML input, writes individual test
        files and a README with run instructions.  Returns the output Path."""
        output_path = Path(os.path.abspath(output_dir))
        output_path.mkdir(parents=True, exist_ok=True)

        data = yaml.safe_load(yaml_content)
        tests = data if isinstance(data, list) else [data]

        for i, test in enumerate(tests):
            test_name = test.get("name", f"test_{i:03d}")
            safe_name = "".join(
                c if c.isalnum() or c in ("-", "_") else "_" for c in test_name
            )
            file_path = output_path / f"{safe_name}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(test, f, default_flow_style=False, sort_keys=False)
            self.log.info("wrote test file", filename=file_path.name)

        readme_content = (
            "# Ejected Maestro Mobile Tests\n\n"
            "## Prerequisites\n"
            "- Install Maestro: `curl -Ls https://get.maestro.mobile.dev | bash`\n"
            "- Ensure an Android emulator or iOS simulator is running\n\n"
            "## Run Tests\n\n"
            "Run all tests:\n"
            "```bash\n"
            "maestro test .\n"
            "```\n\n"
            "Run a single test:\n"
            "```bash\n"
            "maestro test <test_name>.yaml\n"
            "```\n\n"
            "Run with JUnit output:\n"
            "```bash\n"
            "maestro test --format junit --output results.xml .\n"
            "```\n"
        )
        readme_path = output_path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        self.log.info("wrote README.md")

        return output_path
