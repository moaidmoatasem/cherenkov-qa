"""
Smoke test for E13 Autonomy-ladder profiles (C14 #129).

Verifies:
  1. AutonomyProfile dataclass fields
  2. PROFILE_LEVELS contains all 4 levels
  3. get_profile() returns current config
  4. set_profile() changes config
  5. Each level has proper auto_* flags
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.copilot.autonomy import (
    AutonomyProfile,
    get_profile,
    set_profile,
    PROFILE_LEVELS,
)


errors: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [OK] {msg}")


print("1. PROFILE_LEVELS definition")
check(len(PROFILE_LEVELS) == 4, f"4 levels defined (got {len(PROFILE_LEVELS)})")
for name in ["assisted", "augmented", "agentic", "predictive"]:
    check(name in PROFILE_LEVELS, f"level '{name}' exists")

print("\n2. AutonomyProfile structure")
profile = PROFILE_LEVELS["assisted"]
check(isinstance(profile, AutonomyProfile), "instance of AutonomyProfile")
check(profile.level == "assisted", f"level={profile.level}")
check(isinstance(profile.auto_approve, bool), "auto_approve is bool")
check(isinstance(profile.auto_triage, bool), "auto_triage is bool")
check(isinstance(profile.auto_remediate, bool), "auto_remediate is bool")
check(isinstance(profile.deep_rerank, bool), "deep_rerank is bool")

print("\n3. Profile capability escalation")
assisted = PROFILE_LEVELS["assisted"]
augmented = PROFILE_LEVELS["augmented"]
agentic = PROFILE_LEVELS["agentic"]
predictive = PROFILE_LEVELS["predictive"]

check(assisted.auto_approve is False, "assisted: auto_approve=False")
check(assisted.auto_triage is False, "assisted: auto_triage=False")
check(augmented.auto_approve is False, "augmented: auto_approve=False")
check(augmented.auto_triage is True, "augmented: auto_triage=True")
check(agentic.auto_approve is True, "agentic: auto_approve=True")
check(agentic.auto_remediate is True, "agentic: auto_remediate=True")
check(predictive.auto_approve is True, "predictive: auto_approve=True")
check(predictive.auto_remediate is True, "predictive: auto_remediate=True")

print("\n4. get_profile()")
current = get_profile()
check(isinstance(current, AutonomyProfile), "returns AutonomyProfile")
check(current.level in PROFILE_LEVELS, f"current level is valid: {current.level}")

print("\n5. set_profile()")
original = get_profile()
updated = set_profile("augmented")
check(
    updated.level == "augmented", f"set_profile returns augmented (got {updated.level})"
)
check(updated.auto_triage is True, "augmented has auto_triage=True")
set_profile(original.level)
reset = get_profile()
check(reset.level == original.level, f"reset to {original.level}")

print("\n6. Invalid level handling")
try:
    set_profile("invalid_level")
    check(False, "should raise ValueError")
except ValueError:
    check(True, "ValueError for invalid level")

print(f"\n{'='*40}")
if errors:
    print(f"FAILED ({len(errors)} check(s))")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
