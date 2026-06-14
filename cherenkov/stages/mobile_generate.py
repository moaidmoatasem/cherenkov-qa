"""
CHERENKOV stages/mobile_generate.py — Maestro YAML test generator stage.
Authority: v3.1 + delta.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from cherenkov.stages.mobile_plan import MobileScenario


@dataclass
class MobileGenerateOutput:
    scenario_id: str
    yaml_content: str
    status: str = "ok"


class MobileGenerateStage:
    """Produces Maestro-compatible YAML flows from planned mobile scenarios."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id

    def run(self, scenario: MobileScenario) -> MobileGenerateOutput:
        t0 = time.time()
        yaml_lines = ["appId: com.example.app"]
        yaml_lines.append("---")
        yaml_lines.append(f"name: {scenario.name}")
        yaml_lines.append("")
        for i, step in enumerate(scenario.steps, 1):
            step_id = step.lower().replace(" ", "_")
            if "tap " in step:
                element = step.replace("tap ", "")
                yaml_lines.append("- tapOn:")
                yaml_lines.append(f'    text: "{element}"')
            elif "enter " in step:
                parts = step.replace("enter ", "").split(" ", 1)
                field = parts[0] if len(parts) == 1 else parts[0]
                yaml_lines.append("- inputText:")
                yaml_lines.append(f'    text: "test_{field}"')
            elif "launch" in step or "wait" in step:
                yaml_lines.append("- waitFor: 2")
            elif "capture" in step:
                yaml_lines.append("- takeScreenshot:")
                yaml_lines.append(
                    f'    path: "screenshots/{scenario.id}_{step_id}.png"'
                )
            elif "verify" in step or "visible" in step:
                yaml_lines.append("- assertVisible:")
                yaml_lines.append('    text: ".*"')
            else:
                yaml_lines.append("- runFlow:")
                yaml_lines.append("    when:")
                yaml_lines.append(f'      visible: "{step}"')
        yaml_content = "\n".join(yaml_lines)

        dt = int((time.time() - t0) * 1000)
        if self.run_id:
            print(f"[MOBILE_GENERATE] stage success — {scenario.id} — {dt}ms")
        return MobileGenerateOutput(scenario_id=scenario.id, yaml_content=yaml_content)
