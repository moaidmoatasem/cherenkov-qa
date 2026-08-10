import os
import re
from pathlib import Path

repo_root = Path(__file__).parent.parent.resolve()
docs_dir = repo_root / "docs"

replacements_by_file = {
    "docs/cli-reference.md": [
        ("API_REFERENCE.md", "TECHNICAL_DESIGN.md"),
    ],
    "docs/TECHNICAL_DESIGN.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
    ],
    "docs/GETTING_STARTED.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
    ],
    "docs/SCOPE_LEDGER.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
    ],
    "docs/EXECUTION_PLAN.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
    ],
    "docs/PLATFORM_OPERATING_MODEL.md": [
        ("ROADMAP_2026H2.md", "PRODUCT_STRATEGY_ROADMAP.md"),
    ],
    "docs/QUICKSTART_PETSTORE.md": [
        ("guides/dashboard.md", "dashboard/FE_DESIGN_SPEC.md"),
    ],
    "docs/USER_JOURNEYS.md": [
        ("ROADMAP_2026H2.md", "PRODUCT_STRATEGY_ROADMAP.md"),
    ],
    "docs/process/VALIDATION_EVIDENCE_LEDGER.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/process/GITHUB_PM.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/process/QA_VALIDATION_RUNBOOK.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
        ("../../.cherenkov/evidence/validation_gate_pass.json", "../../evidence/e0.1_petstore.json"),
    ],
    "docs/vision/08_DELIVERY_PLAN.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/vision/SPIKE_CHAINED_JOURNEYS.md": [
        ("../../PHASE_PLAN.md", "../PHASE_PLAN.md"),
        ("../../STATUS.md", "../STATUS.md"),
    ],
    "docs/vision/desktopConsiderations_agentsWarRoom.md": [
        ("../../PHASE_PLAN.md", "../PHASE_PLAN.md"),
    ],
    "docs/vision/ux and flows considerations and revampin.md": [
        ("../../dashboard/FE_DESIGN_SPEC.md", "../dashboard/FE_DESIGN_SPEC.md"),
        ("../../PHASE_PLAN.md", "../PHASE_PLAN.md"),
    ],
    "docs/vision/14_KUBERNETES_CONSIDERATIONS.md": [
        ("../ROADMAP_PACKAGING.md", "../PHASE_PLAN.md"),
    ],
    "docs/vision/16_CHAT_AGENT.md": [
        ("[tool_args](**tool_args)", "`tool_args`"),
    ],
    "docs/vision/#MOBILE TESTING PLAN_agentsPLans.md": [
        ("../../PHASE_PLAN.md", "../PHASE_PLAN.md"),
        ("../../STATUS.md", "../STATUS.md"),
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/vision/K8s_Phase0 Plan — Final Locked.md": [
        ("../../PHASE_PLAN.md", "../PHASE_PLAN.md"),
        ("../../STATUS.md", "../STATUS.md"),
    ],
    "docs/reviews/README.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
        ("../ROADMAP_2026H2.md", "../PRODUCT_STRATEGY_ROADMAP.md"),
    ],
    "docs/demos/CATCH_THE_AI_CHEATING.md": [
        ("../ROADMAP_AQE.md", "../PRODUCT_STRATEGY_ROADMAP.md"),
    ],
    "docs/specs/MCP_VERIFICATION_SERVER.md": [
        ("../ROADMAP_AQE.md", "../PRODUCT_STRATEGY_ROADMAP.md"),
    ],
    "docs/reports/INTEGRATION_RESEARCH_REPORT.md": [
        ("docs/process/VALIDATION_EVIDENCE_LEDGER.md", "../process/VALIDATION_EVIDENCE_LEDGER.md"),
        ("../docs/HANDOVER.md", "../../HANDOVER.md"),
        ("../docs/vision/00_VISION.md", "../vision/00_VISION.md"),
        ("../docs/vision/01_ARCHITECTURE.md", "../vision/01_ARCHITECTURE.md"),
        ("../docs/vision/06_AUTONOMOUS_QA_FABRIC.md", "../vision/06_AUTONOMOUS_QA_FABRIC.md"),
        ("../docs/vision/07_MASTER_PLAN.md", "../vision/07_MASTER_PLAN.md"),
        ("../docs/vision/08_DELIVERY_PLAN.md", "../vision/08_DELIVERY_PLAN.md"),
        ("../AGENTS.md", "../../AGENTS.md"),
        ("../CONTRIBUTING.md", "../../CONTRIBUTING.md"),
    ],
    "docs/engineering/README.md": [
        ("(CODE_OF_CONDUCT.md)", "(../CODE_OF_CONDUCT.md)"),
    ],
    "docs/engineering/SYNC_DRIVEN_DEV.md": [
        ("../../skills/sync-driven-dev.md", "../../skills/sync-driven-dev/SKILL.md"),
    ],
    "docs/plans/2026-06-08-mobile-testing-context.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/wiki/Contributing.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/wiki/Way-of-Work.md": [
        ("../HANDOVER.md", "../../HANDOVER.md"),
    ],
    "docs/onboarding/VIDEO_RECORDING_GUIDE.md": [
        ("docs/recordings/session_a.gif", "../recordings/session_a.gif"),
    ],
    "docs/onboarding/RECORDING_ASSETS/README.md": [
        ("RECORDING_ASSETS/gif/cherenkov_green_pass.gif", "gif/cherenkov_green_pass.gif"),
        ("RECORDING_ASSETS/thumbnails/session_a_thumb.png", "thumbnails/session_a_thumb.png"),
    ],
    "docs/archive/handovers/HANDOVER.md": [
        ("(STATUS.md)", "(../../STATUS.md)"),
        ("(PHASE_PLAN.md)", "(../../PHASE_PLAN.md)"),
        ("(QA_DEMO_KIT.md)", "(../../QA_DEMO_KIT.md)"),
        ("(QA_OUTREACH_TEMPLATES.md)", "(../../QA_OUTREACH_TEMPLATES.md)"),
        ("(PRODUCT_STRATEGY_ROADMAP.md)", "(../../PRODUCT_STRATEGY_ROADMAP.md)"),
        ("(INTEGRATION_STRATEGY.md)", "(../../INTEGRATION_STRATEGY.md)"),
        ("(recordings/)", "(../../recordings/)"),
        ("(adr/)", "(../../adr/)"),
        ("(adr/ADR-004-clean-architecture.md)", "(../../adr/ADR-004-clean-architecture.md)"),
        ("(engineering/BEST_PRACTICES.md)", "(../../engineering/BEST_PRACTICES.md)"),
        ("../HANDOVER.md", "../../../HANDOVER.md"),
        ("../AGENTS.md", "../../../AGENTS.md"),
    ],
    "docs/archive/handovers/SESSION_HANDOVER_2026-06-16.md": [
        ("(STATUS.md)", "(../../STATUS.md)"),
        ("(NORTH_STAR.md)", "(../../NORTH_STAR.md)"),
        ("(VISION_AQE_2026.md)", "(../../VISION_AQE_2026.md)"),
        ("(ROADMAP_AQE.md)", "(../../PRODUCT_STRATEGY_ROADMAP.md)"),
        ("(EXECUTION_PLAN.md)", "(../../EXECUTION_PLAN.md)"),
        ("(demos/CATCH_THE_AI_CHEATING.md)", "(../../demos/CATCH_THE_AI_CHEATING.md)"),
    ],
    "docs/archive/handovers/AGENT_HANDOVER_2026-06-18.md": [
        ("../cherenkov/core/settings.py", "../../../cherenkov/core/settings.py"),
        ("(config)", "(../../config)"),
    ],
    "docs/archive/handovers/AGENT_HANDOVER_2026-06-17.md": [
        ("../cherenkov/core/settings.py", "../../../cherenkov/core/settings.py"),
    ],
    "docs/_archive/ROADMAP_RECONCILIATION.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
        ("../AGENTS.md", "../../AGENTS.md"),
        ("process/QA_VALIDATION_RUNBOOK.md", "../process/QA_VALIDATION_RUNBOOK.md"),
        ("vision/10_HORIZON_2.md", "../vision/10_HORIZON_2.md"),
    ],
    "docs/_archive/INTEGRATION_HANDOVER_REPORT.md": [
        ("(STATUS.md)", "(../STATUS.md)"),
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
        ("../AGENTS.md", "../../AGENTS.md"),
        ("(PHASE_PLAN.md)", "(../PHASE_PLAN.md)"),
    ],
    "docs/_archive/ROADMAP_NEXT.md": [
        ("(HANDOVER.md)", "(../HANDOVER.md)"),
        ("(SCOPE_LEDGER.md)", "(../SCOPE_LEDGER.md)"),
        ("(PHASE_PLAN.md)", "(../PHASE_PLAN.md)"),
        ("process/VALIDATION_EVIDENCE_LEDGER.md", "../process/VALIDATION_EVIDENCE_LEDGER.md"),
        ("reviews/README.md", "../reviews/README.md"),
    ],
    "docs/_archive/DEFERRED_VISION_ARCHIVE.md": [
        ("(PHASE_PLAN.md)", "(../PHASE_PLAN.md)"),
        ("(STATUS.md)", "(../STATUS.md)"),
    ],
}

total_changed = 0
for rel_file, replacements in replacements_by_file.items():
    file_path = repo_root / rel_file
    if not file_path.exists():
        print(f"Warning: file {rel_file} does not exist!")
        continue
    content = file_path.read_text(encoding="utf-8")
    orig_content = content
    for old_str, new_str in replacements:
        content = content.replace(old_str, new_str)
    if content != orig_content:
        file_path.write_text(content, encoding="utf-8")
        total_changed += 1
        print(f"Updated {rel_file}")

print(f"\nDone updating {total_changed} files.")
