from __future__ import annotations


from cherenkov.copilot.autonomy import get_profile, set_profile, PROFILE_LEVELS


def run_profile(action: str = "show", level: str | None = None) -> int:
    if action == "set":
        if level is None:
            print("Error: --level is required for 'set' action")
            print(f"Valid levels: {', '.join(PROFILE_LEVELS.keys())}")
            return 1
        profile = set_profile(level)
        print(f"Autonomy profile set to: {profile.level} ({profile.label})")
        print(f"  Autonomy:     {profile.level}")
        print(f"  Auto-approve: {profile.auto_approve}")
        print(f"  Auto-triage:  {profile.auto_triage}")
        print(f"  Deep-rerank:  {profile.deep_rerank}")
        return 0

    profile = get_profile()
    print("=" * 60)
    print("  E13 Autonomy Ladder — Current Profile")
    print("=" * 60)
    print(f"  Level:         {profile.level}")
    print(f"  Label:         {profile.label}")
    print(f"  Description:   {profile.description}")
    print(f"  Auto-approve:  {profile.auto_approve}")
    print(f"  Auto-triage:   {profile.auto_triage}")
    print(f"  Deep-rerank:   {profile.deep_rerank}")
    print(f"  Auto-remediate:{profile.auto_remediate}")
    print()
    print("  Available profiles:")
    for name, p in PROFILE_LEVELS.items():
        marker = " <- current" if name == profile.level else ""
        print(f"    {name:14} {p.label}{marker}")
    print()
    print("  Set via:  cherenkov profile set --level <name>")
    print(f"  Or env:   CHERENKOV_COPILOT_AUTONOMY={profile.level}")
    print("=" * 60)
    return 0
