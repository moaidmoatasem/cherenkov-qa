"""
CHERENKOV execution/mobile_eject_appium.py — Appium Python test ejector.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from cherenkov.core.errors import get_logger


class AppiumEjector:
    """Converts Maestro YAML test definitions into standalone Appium Python
    test files with zero CHERENKOV imports."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "appium-eject"
        self.log = get_logger("APPIUM_EJECT", self.run_id)

    def _generate_appium_test(self, test: dict) -> str:
        """Generates a pytest-based Appium test method from a Maestro test definition."""
        test_name = test.get("name", "untitled_test")
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in test_name)
        steps = test.get("steps", [])

        lines = [
            "import pytest",
            "from appium import webdriver",
            "from appium.webdriver.common.appiumby import AppiumBy",
            "",
            "",
            f"def test_{safe_name}(driver):",
        ]

        for step in steps:
            if isinstance(step, dict):
                if "assertVisible" in step:
                    text = step["assertVisible"]
                    lines.append(
                        f"    element = driver.find_element(AppiumBy.XPATH, \"//*[contains(text(), '{text}')]\")"
                    )
                    lines.append("    assert element.is_displayed()")
                elif "tapOn" in step:
                    target = step["tapOn"]
                    lines.append(
                        f"    element = driver.find_element(AppiumBy.XPATH, \"//*[contains(text(), '{target}')]\")"
                    )
                    lines.append("    element.click()")
                elif "inputText" in step:
                    target = step.get("inputText", "")
                    text = step.get("text", "")
                    lines.append(
                        f"    element = driver.find_element(AppiumBy.XPATH, \"//*[contains(text(), '{target}')]\")"
                    )
                    lines.append(f"    element.send_keys('{text}')")
                elif "scroll" in step:
                    direction = step["scroll"]
                    lines.append(
                        f"    driver.swipe(500, 1500, 500, 500)  # scroll {direction}"
                    )
                elif "waitForVisible" in step:
                    target = step["waitForVisible"]
                    timeout = step.get("timeout", 5000)
                    lines.append(
                        f"    driver.find_element(AppiumBy.XPATH, \"//*[contains(text(), '{target}')]\")"
                    )
                    lines.append(
                        f"    # waited for visibility of '{target}' (timeout={timeout}ms)"
                    )
                else:
                    lines.append(f"    # unhandled step: {list(step.keys())[0]}")
            else:
                lines.append(f"    # unhandled step: {step}")

        return "\n".join(lines) + "\n"

    def eject(self, yaml_content: str, output_dir: str) -> Path:
        """Parses a multi-test Maestro YAML input and writes standalone Appium
        Python test files, conftest.py, requirements.txt, and README.md.
        Returns the output Path."""
        output_path = Path(os.path.abspath(output_dir))
        output_path.mkdir(parents=True, exist_ok=True)

        data = yaml.safe_load(yaml_content)
        tests = data if isinstance(data, list) else [data]

        for i, test in enumerate(tests):
            test_name = test.get("name", f"test_{i:03d}")
            safe_name = "".join(
                c if c.isalnum() or c == "_" else "_" for c in test_name
            )
            test_code = self._generate_appium_test(test)
            file_path = output_path / f"test_{safe_name}.py"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            self.log.info("wrote test file", filename=file_path.name)

        conftest_content = (
            "import pytest\n"
            "from appium import webdriver\n"
            "\n"
            "\n"
            '@pytest.fixture(scope="function")\n'
            "def driver():\n"
            "    desired_caps = {\n"
            '        "platformName": "Android",\n'
            '        "automationName": "UiAutomator2",\n'
            '        "deviceName": "emulator-5554",\n'
            '        "appPackage": "com.example.app",\n'
            '        "appActivity": ".MainActivity",\n'
            "    }\n"
            '    driver = webdriver.Remote("http://localhost:4723", desired_caps)\n'
            "    yield driver\n"
            "    driver.quit()\n"
        )
        conftest_path = output_path / "conftest.py"
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftest_content)
        self.log.info("wrote conftest.py")

        requirements_content = "Appium-Python-Client>=3.0.0\n" "pytest>=7.0.0\n"
        requirements_path = output_path / "requirements.txt"
        with open(requirements_path, "w", encoding="utf-8") as f:
            f.write(requirements_content)
        self.log.info("wrote requirements.txt")

        readme_content = (
            "# Ejected Appium Mobile Tests\n\n"
            "## Prerequisites\n"
            "- Install Appium server: `npm install -g appium`\n"
            "- Install UiAutomator2 driver: `appium driver install uiautomator2`\n"
            "- Ensure an Android emulator or iOS simulator is running\n\n"
            "## Setup\n\n"
            "```bash\n"
            "pip install -r requirements.txt\n"
            "```\n\n"
            "## Run Tests\n\n"
            "Start Appium server:\n"
            "```bash\n"
            "appium\n"
            "```\n\n"
            "Run tests:\n"
            "```bash\n"
            "pytest -v\n"
            "```\n"
        )
        readme_path = output_path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        self.log.info("wrote README.md")

        return output_path
