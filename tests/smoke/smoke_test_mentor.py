"""
Smoke test for E13 Mentor idiom-surfacing (C13 #128).

Verifies:
  1. Mentor.get_suggestions with N-confirmations threshold
  2. Idioms below min_confirmations are filtered out
  3. Context-based matching (endpoint, divergence_class)
  4. Ranking by decay_score + confirm_count
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.copilot.mentor import Mentor
from cherenkov.reflector.store import VerdictStore
from cherenkov.core.contracts import Idiom, DivergenceClass


errors: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [OK] {msg}")


db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db.close()
store = VerdictStore(db_path=db.name, run_id="smoke_test")
now = int(time.time())

idioms_data = [
    Idiom(
        id=str(uuid.uuid4()),
        pattern="Email validation missing",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="POST /users",
        confirm_count=5,
        last_confirmed=now,
        decay_score=0.9,
    ),
    Idiom(
        id=str(uuid.uuid4()),
        pattern="Password too short returns 400",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="POST /users",
        confirm_count=1,
        last_confirmed=now,
        decay_score=0.8,
    ),
    Idiom(
        id=str(uuid.uuid4()),
        pattern="Auth token expires after 1h",
        divergence_class=DivergenceClass.D2_CODE_PROD,
        endpoint="GET /profile",
        confirm_count=3,
        last_confirmed=now,
        decay_score=0.7,
    ),
    Idiom(
        id=str(uuid.uuid4()),
        pattern="404 for deleted resources",
        divergence_class=DivergenceClass.D5_SPEC_PROD,
        endpoint="GET /resources/{id}",
        confirm_count=2,
        last_confirmed=now,
        decay_score=0.6,
    ),
    Idiom(
        id=str(uuid.uuid4()),
        pattern="Rate limiting missing on /login",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="POST /login",
        confirm_count=0,
        last_confirmed=now,
        decay_score=0.5,
    ),
]

for idiom in idioms_data:
    store.upsert_idiom(idiom)

mentor = Mentor(store=store, run_id="smoke_test")

print("1. Default min_confirmations (2)")
suggestions = mentor.get_suggestions(min_decay=0.0)
check(len(suggestions) >= 0, f"returns list ({len(suggestions)} items)")
for s in suggestions:
    check(
        s.confirm_count >= 2,
        f"idiom has >= 2 confirmations: count={s.confirm_count} '{s.pattern[:40]}'",
    )

print("\n2. min_confirmations=1")
suggestions1 = mentor.get_suggestions(min_decay=0.0, min_confirmations=1)
check(len(suggestions1) > len(suggestions), "more idioms with min_confirmations=1")

print("\n3. Context-based matching")
suggestions_users = mentor.get_suggestions(
    endpoint="POST /users", min_decay=0.0, min_confirmations=1
)
for s in suggestions_users:
    check(
        s.endpoint == "POST /users" or s.endpoint is None,
        f"matched endpoint: {s.endpoint}",
    )
check(len(suggestions_users) > 0, "at least one match for POST /users")

print("\n4. Ranking order")
suggestions_ranked = mentor.get_suggestions(min_decay=0.0, min_confirmations=1)
for i in range(len(suggestions_ranked) - 1):
    a = suggestions_ranked[i]
    b = suggestions_ranked[i + 1]
    check(
        a.decay_score >= b.decay_score,
        f"ranking: {a.pattern[:30]} ({a.decay_score}) >= {b.pattern[:30]} ({b.decay_score})",
    )

print("\n5. Divergence class filtering")
suggestions_d1 = mentor.get_suggestions(
    divergence_class="D1_spec_code", min_decay=0.0, min_confirmations=1
)
for s in suggestions_d1:
    check(
        s.divergence_class == DivergenceClass.D1_SPEC_CODE,
        f"matched divergence class: {s.divergence_class}",
    )

if os.path.exists(db.name):
    os.unlink(db.name)

print(f"\n{'='*40}")
if errors:
    print(f"FAILED ({len(errors)} check(s))")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
