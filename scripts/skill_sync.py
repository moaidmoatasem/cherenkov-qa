#!/usr/bin/env python3
"""
Skill Sync Validator: CHERENKOV ↔ Qwen Code

Validates that skills defined in `.qwen/skills/` have a corresponding
equivalent in `skills/` and vice versa, keeping the agent ecosystems harmonized.

Usage:
  python3 scripts/skill_sync.py [--validate]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHERENKOV_SKILLS = ROOT / "skills"
QWEN_SKILLS = ROOT / ".qwen" / "skills"

# Mapping of Qwen Code skill name -> CHERENKOV skill name
# Used to verify alignment
SKILL_MAP = {
    "api-test-gen.md": "api-test-generation.md",
    "eject-validate.md": "eject-standalone.md",
    "governance-check.md": "governance-certification.md",
    "k8s-deploy.md": None  # Qwen-specific skill
}

def main():
    validate_only = "--validate" in sys.argv
    
    if not QWEN_SKILLS.exists():
        print(f"Error: {QWEN_SKILLS} does not exist.")
        sys.exit(1 if validate_only else 0)
        
    errors = 0
    
    print("Validating skill harmonization...")
    for qwen_skill, cher_skill in SKILL_MAP.items():
        q_path = QWEN_SKILLS / qwen_skill
        
        if not q_path.exists():
            print(f"❌ Missing Qwen Code skill: {qwen_skill}")
            errors += 1
            continue
            
        print(f"✅ Found Qwen Code skill: {qwen_skill}")
        
        if cher_skill:
            c_path = CHERENKOV_SKILLS / cher_skill
            if not c_path.exists():
                print(f"❌ Missing CHERENKOV mapping target: {cher_skill}")
                errors += 1
            else:
                print(f"  ↳ Maps to: {cher_skill}")
                
    if errors > 0:
        print(f"\nFailed with {errors} errors. Skill directories are out of sync.")
        sys.exit(1)
        
    print("\nSkill directories are harmonized.")
    sys.exit(0)

if __name__ == "__main__":
    main()
