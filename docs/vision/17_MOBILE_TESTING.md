# Vision 17: Mobile Testing (Maestro/Appium, 4-Tier Devices)

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #284 (Phase 5), #285 (Phase 6)

---

## Overview

Mobile Testing extends CHERENKOV to test mobile apps (Android/iOS) using Maestro and Appium. It enables:

- **Mobile source ingestion**: APK/HAR/HIL parsing
- **Pilot agent**: 3-step intent orchestration with circuit breaker
- **Mobile stages**: plan, generate, review (Maestro YAML)
- **Semantic visual oracle**: VLM-based screenshot analysis
- **Dual eject formats**: Maestro YAML + Appium Python
- **4-tier device support**: Browser emulation → Android emulator → iOS simulator → Physical device

---

## Architecture

```
┌─────────────────────────────────────┐
│  Mobile Source Adapter              │
│  - APK/HAR/HIL ingestion            │
│  - Mobile app metadata extraction   │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Mobile Stages                      │
│  - mobile_plan.py                   │
│  - mobile_generate.py               │
│  - mobile_review.py                 │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Pilot Agent                        │
│  - 3-step intent orchestration      │
│  - Circuit breaker (20 obs, 5 min)  │
│  - InMemoryRunner (stub)            │
│  - MaestroRunner (real)             │
│  - AppiumRunner (real)              │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Semantic Visual Oracle             │
│  - VLM-based screenshot analysis    │
│  - Anti-reward-hacking gate         │
│  - Pixel diff fallback              │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│  Mobile Eject                       │
│  - Maestro YAML (standalone)        │
│  - Appium Python (standalone)       │
│  - ZERO CHERENKOV imports           │
└─────────────────────────────────────┘
```

---

## 4-Tier Device Support

| Tier | Device | Use Case | Cost |
|------|--------|----------|------|
| **Tier 1** | Browser emulation | Quick smoke tests | $0 |
| **Tier 2** | Android emulator | Local development | $0 |
| **Tier 3** | iOS simulator | macOS development | $0 |
| **Tier 4** | Physical device | Production testing | $0 (local) or $50-100/mo (cloud) |

### Device Selection

```python
# cherenkov/mobile/device_selector.py
from cherenkov.core.devices import DeviceClass

def select_device_tier(device_class: DeviceClass) -> str:
    """Select device tier based on device class."""
    if device_class in [DeviceClass.GPU_WORKSTATION, DeviceClass.GPU_MID_RANGE]:
        return "android_emulator"  # Tier 2
    elif device_class == DeviceClass.CPU_HIGH_END:
        return "ios_simulator"  # Tier 3 (macOS only)
    else:
        return "browser_emulation"  # Tier 1
```

---

## Mobile Source Adapters

### Contracts

```python
# cherenkov/sources/mobile/contracts.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class MobileApp:
    app_id: str
    name: str
    platform: Literal["android", "ios"]
    version: str
    package_path: str

@dataclass
class MobileScreen:
    screen_id: str
    name: str
    elements: list[dict]
    navigation: list[str]

@dataclass
class MobileFlow:
    flow_id: str
    name: str
    screens: list[str]
    actions: list[dict]
```

### Parsers

```python
# cherenkov/sources/mobile/parsers.py
from pathlib import Path
from .contracts import MobileApp, MobileScreen, MobileFlow

class APKParser:
    def parse(self, apk_path: str) -> MobileApp:
        # Use apktool or similar
        # Extract package name, version, activities
        pass

class HARParser:
    def parse(self, har_path: str) -> list[dict]:
        import json
        with open(har_path) as f:
            har = json.load(f)

        return [
            {
                "url": entry["request"]["url"],
                "method": entry["request"]["method"],
                "status": entry["response"]["status"]
            }
            for entry in har["log"]["entries"]
        ]

class HILParser:
    def parse(self, hil_path: str) -> list[MobileFlow]:
        # Parse user interaction traces
        pass
```

### Adapter

```python
# cherenkov/sources/mobile/adapter.py
from cherenkov.sources.base import SourceAdapter
from .contracts import MobileApp
from .parsers import APKParser, HARParser, HILParser

class MobileSourceAdapter:
    def __init__(self):
        self.apk_parser = APKParser()
        self.har_parser = HARParser()
        self.hil_parser = HILParser()

    def ingest(self, source_path: str) -> MobileApp:
        path = Path(source_path)

        if path.suffix == ".apk":
            return self.apk_parser.parse(source_path)
        elif path.suffix == ".har":
            api_calls = self.har_parser.parse(source_path)
            # Convert to MobileApp
            pass
        elif path.suffix == ".hil":
            flows = self.hil_parser.parse(source_path)
            # Convert to MobileApp
            pass
        else:
            raise ValueError(f"Unsupported mobile source format: {path.suffix}")
```

---

## Pilot Agent

```python
# cherenkov/agents/pilot.py
from dataclasses import dataclass
from typing import Literal
import time

@dataclass
class PilotStep:
    step_id: str
    action: str
    target: str
    expected: str
    actual: str | None = None
    status: Literal["pending", "running", "done", "failed"] = "pending"

class InMemoryRunner:
    def __init__(self):
        self.steps: list[PilotStep] = []

    def execute_step(self, step: PilotStep) -> PilotStep:
        step.status = "running"
        time.sleep(0.1)
        step.actual = step.expected
        step.status = "done"
        self.steps.append(step)
        return step

class PilotAgent:
    def __init__(self, runner: InMemoryRunner, max_observations: int = 20, timeout_seconds: int = 300):
        self.runner = runner
        self.max_observations = max_observations
        self.timeout_seconds = timeout_seconds
        self.observations = 0
        self.start_time = None

    def run(self, intent: str) -> list[PilotStep]:
        self.start_time = time.time()
        self.observations = 0

        steps = self._parse_intent(intent)

        for step in steps:
            if self.observations >= self.max_observations:
                step.status = "failed"
                step.actual = "Circuit breaker: max observations reached"
                break

            if time.time() - self.start_time > self.timeout_seconds:
                step.status = "failed"
                step.actual = "Circuit breaker: timeout reached"
                break

            result = self.runner.execute_step(step)
            self.observations += 1

            if result.status == "failed":
                self._recover(result)
                break

        return self.runner.steps

    def _parse_intent(self, intent: str) -> list[PilotStep]:
        return [
            PilotStep(step_id="1", action="open_app", target="app", expected="app_opened"),
            PilotStep(step_id="2", action="navigate", target="screen", expected="screen_visible"),
            PilotStep(step_id="3", action="verify", target="element", expected="element_present")
        ]

    def _recover(self, failed_step: PilotStep):
        print(f"Pilot recovery: {failed_step.action} failed - {failed_step.actual}")
```

---

## Mobile Stages

### mobile_plan.py

```python
# cherenkov/stages/mobile_plan.py
from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow

class MobilePlanStage:
    def plan(self, app: MobileApp, flows: list[MobileFlow]) -> list[dict]:
        scenarios = []

        for flow in flows:
            scenarios.append({
                "flow_id": flow.flow_id,
                "name": flow.name,
                "screens": flow.screens,
                "actions": flow.actions
            })

        return scenarios
```

### mobile_generate.py

```python
# cherenkov/stages/mobile_generate.py
import yaml

class MobileGenerateStage:
    def generate(self, scenarios: list[dict]) -> str:
        tests = []

        for scenario in scenarios:
            test = {
                "appId": "com.example.app",
                "name": scenario["name"],
                "steps": []
            }

            for action in scenario["actions"]:
                step = {
                    "action": action["type"],
                    "target": action["target"]
                }
                test["steps"].append(step)

            tests.append(test)

        return yaml.dump({"tests": tests}, default_flow_style=False)
```

### mobile_review.py

```python
# cherenkov/stages/mobile_review.py
class MobileReviewStage:
    def review(self, yaml_content: str) -> dict:
        import yaml
        try:
            data = yaml.safe_load(yaml_content)

            if "tests" not in data:
                return {"status": "failed", "reason": "Missing 'tests' field"}

            for test in data["tests"]:
                if "appId" not in test:
                    return {"status": "failed", "reason": "Missing 'appId' in test"}
                if "steps" not in test:
                    return {"status": "failed", "reason": "Missing 'steps' in test"}

            return {"status": "approved", "tests": len(data["tests"])}
        except yaml.YAMLError as e:
            return {"status": "failed", "reason": f"Invalid YAML: {e}"}
```

---

## Semantic Visual Oracle

```python
# cherenkov/oracle/visual_oracle_vlm.py
from cherenkov.substrate.router import SubstrateRouter

class SemanticVisualOracle:
    def __init__(self, router: SubstrateRouter):
        self.router = router

    def analyze(self, screenshot: bytes, expected_description: str) -> dict:
        provider = self.router.get_vlm_provider()

        if not provider:
            return self._pixel_diff(screenshot, expected_description)

        prompt = f"""Analyze this mobile app screenshot.
Expected: {expected_description}

Describe what you see and whether it matches the expected description.
Rate confidence from 0.0 to 1.0."""

        response = provider.analyze(screenshot, prompt)
        confidence = self._parse_confidence(response.text)

        if confidence < 0.7:
            return {
                "status": "uncertain",
                "confidence": confidence,
                "description": response.text,
                "action": "escalate_to_hitl"
            }

        return {
            "status": "passed" if confidence > 0.8 else "failed",
            "confidence": confidence,
            "description": response.text
        }

    def _pixel_diff(self, screenshot: bytes, expected_description: str) -> dict:
        return {
            "status": "pixel_diff_only",
            "confidence": 0.5,
            "description": "VLM not available, using pixel diff only"
        }

    def _parse_confidence(self, text: str) -> float:
        import re
        match = re.search(r'confidence[:\s]+([0-9.]+)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.5
```

---

## Mobile Eject

### Maestro YAML

```python
# cherenkov/execution/mobile_eject_maestro.py
import yaml
from pathlib import Path

class MaestroEjector:
    def eject(self, yaml_content: str, output_dir: str):
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        data = yaml.safe_load(yaml_content)

        for i, test in enumerate(data.get("tests", [])):
            test_file = output_path / f"test_{i+1}_{test['name']}.yaml"

            standalone_test = {
                "appId": test["appId"],
                "name": test["name"],
                "steps": test["steps"]
            }

            with open(test_file, "w") as f:
                yaml.dump(standalone_test, f, default_flow_style=False)

        readme = output_path / "README.md"
        with open(readme, "w") as f:
            f.write(f"""# Mobile Tests (Maestro)

Generated by CHERENKOV. These are standalone Maestro tests.

## Run Tests

```bash
# Install Maestro
curl -Ls "https://get.maestro.mobile.dev" | bash

# Run all tests
maestro test .
```

## Tests

{len(data.get('tests', []))} tests generated.
""")

        return output_path
```

### Appium Python

```python
# cherenkov/execution/mobile_eject_appium.py
from pathlib import Path

class AppiumEjector:
    def eject(self, yaml_content: str, output_dir: str):
        import yaml

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        data = yaml.safe_load(yaml_content)

        for i, test in enumerate(data.get("tests", [])):
            test_file = output_path / f"test_{i+1}_{test['name']}.py"
            test_code = self._generate_appium_test(test)

            with open(test_file, "w") as f:
                f.write(test_code)

        requirements = output_path / "requirements.txt"
        with open(requirements, "w") as f:
            f.write("Appium-Python-Client>=3.0.0\n")
            f.write("pytest>=7.0.0\n")

        return output_path

    def _generate_appium_test(self, test: dict) -> str:
        test_name = test["name"].replace(" ", "_").lower()

        code = f'''"""Appium test: {test["name"]}"""
import pytest
from appium import webdriver
from appium.options import UiAutomator2Options

class Test{test_name.title().replace("_", "")}:
    @pytest.fixture
    def driver(self):
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.app = "/path/to/app.apk"

        driver = webdriver.Remote("http://localhost:4723", options=options)
        yield driver
        driver.quit()

    def test_{test_name}(self, driver):
'''

        for step in test.get("steps", []):
            action = step.get("action")
            target = step.get("target")

            if action == "tap":
                code += f'        driver.find_element("id", "{target}").click()\n'
            elif action == "type":
                text = step.get("text", "")
                code += f'        driver.find_element("id", "{target}").send_keys("{text}")\n'
            elif action == "assert_visible":
                code += f'        assert driver.find_element("id", "{target}").is_displayed()\n'

        return code
```

---

## Mobile Reflector Extensions

```python
# cherenkov/reflector/mobile_extensions.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class MobileFailure:
    failure_id: str
    classification: Literal["mobile_bug", "mobile_flaky", "mobile_env"]
    endpoint: str
    method: str
    reason: str
    device_info: dict

class MobileReflectorExtension:
    def __init__(self, reflector):
        self.reflector = reflector

    def classify_mobile_failure(self, failure: MobileFailure):
        self.reflector.store_verdict(
            verdict=failure.classification,
            endpoint=failure.endpoint,
            method=failure.method,
            reason=failure.reason,
            metadata={"device_info": failure.device_info}
        )

        if failure.classification == "mobile_bug":
            self.reflector.boost_idiom(f"mobile_bug_{failure.endpoint}")
        elif failure.classification == "mobile_flaky":
            self.reflector.suppress_idiom(f"mobile_flaky_{failure.endpoint}")
        elif failure.classification == "mobile_env":
            self.reflector.suppress_idiom(f"mobile_env_{failure.endpoint}")
```

---

## Mobile Self-Play Gate

```python
# cherenkov/divergence/self_play.py (extend)
from cherenkov.oracle.visual_oracle_vlm import SemanticVisualOracle

class MobileSelfPlayGate:
    def __init__(self, oracle: SemanticVisualOracle):
        self.oracle = oracle

    def validate(self, screenshot: bytes, expected_description: str) -> dict:
        correct_result = self.oracle.analyze(screenshot, expected_description)

        broken_description = "Completely different screen"
        broken_result = self.oracle.analyze(screenshot, broken_description)

        malicious_screenshot = self._create_malicious_screenshot()
        malicious_result = self.oracle.analyze(malicious_screenshot, expected_description)

        gate_passed = (
            correct_result["status"] == "passed" and
            broken_result["status"] == "failed" and
            malicious_result["status"] == "uncertain"
        )

        return {
            "gate_passed": gate_passed,
            "correct_mock": correct_result,
            "broken_mock": broken_result,
            "malicious_input": malicious_result
        }
```

---

## Mobile Smoke Tests

```python
# tests/smoke/mobile/test_mobile_pipeline.py
import pytest
from pathlib import Path

def test_mobile_ingest():
    from cherenkov.stages.ingest import IngestStage

    test_apk = Path("tests/fixtures/test.apk")
    if not test_apk.exists():
        pytest.skip("Test APK not found")

    ingest = IngestStage()
    app = ingest.ingest(str(test_apk))

    assert app.app_id
    assert app.platform in ["android", "ios"]

def test_mobile_plan():
    from cherenkov.stages.mobile_plan import MobilePlanStage
    from cherenkov.sources.mobile.contracts import MobileApp, MobileFlow

    app = MobileApp(
        app_id="com.test.app",
        name="Test App",
        platform="android",
        version="1.0",
        package_path="/tmp/test.apk"
    )

    flows = [
        MobileFlow(
            flow_id="login",
            name="Login Flow",
            screens=["login", "home"],
            actions=[
                {"type": "tap", "target": "login_button"},
                {"type": "type", "target": "username_field", "text": "testuser"}
            ]
        )
    ]

    planner = MobilePlanStage()
    scenarios = planner.plan(app, flows)

    assert len(scenarios) > 0

def test_mobile_generate():
    from cherenkov.stages.mobile_generate import MobileGenerateStage

    scenarios = [
        {
            "flow_id": "login",
            "name": "Login Flow",
            "screens": ["login", "home"],
            "actions": [
                {"type": "tap", "target": "login_button"}
            ]
        }
    ]

    generator = MobileGenerateStage()
    yaml_content = generator.generate(scenarios)

    assert "tests:" in yaml_content
    assert "Login Flow" in yaml_content
```

---

## References

- EPIC #284 (Phase 5: Mobile Testing Core)
- EPIC #285 (Phase 6: Mobile Execution)
- Issue #362-#376 (Mobile testing tickets)
- `docs/PHASE_PLAN.md` (Phase 5-6 details)
- `cherenkov/sources/mobile/` (to be created)
- `cherenkov/agents/pilot.py` (to be created)
- `cherenkov/oracle/visual_oracle_vlm.py` (to be created)
