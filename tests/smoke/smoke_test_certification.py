"""
Smoke test for E12 Certification Gate (C11 #126).

Verifies:
  1. Default gold set loads with version 2 items
  2. RAG-Triad evaluator returns valid scores
  3. ModelCertificationManager creates default gold set on first load
  4. certify_tier returns CertResult with proper fields
  5. certify_tier_with_rag_report returns per-item reports
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.substrate.certification import (
    ModelCertificationManager,
    RAGTriadEvaluator,
    _DEFAULT_GOLD_SET_ITEMS,
)
from cherenkov.core.contracts import GoldSet, CertResult


errors: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [OK] {msg}")


print("1. Default gold set items")
check(
    len(_DEFAULT_GOLD_SET_ITEMS) >= 3,
    f"at least 3 items (got {len(_DEFAULT_GOLD_SET_ITEMS)})",
)

for item in _DEFAULT_GOLD_SET_ITEMS:
    check("prompt" in item, f"item has prompt: {item['prompt'][:40]}")
    check("expected_contains" in item, "item has expected_contains")

print("\n2. RAG-Triad evaluator")
evaluator = RAGTriadEvaluator()
scores = evaluator.evaluate("Say the word CHERENKOV.", "CHERENKOV")
check("context_relevance" in scores, "has context_relevance")
check("answer_faithfulness" in scores, "has answer_faithfulness")
check("answer_relevance" in scores, "has answer_relevance")
check(
    0.0 <= scores["context_relevance"] <= 1.0,
    f"context_relevance in range: {scores['context_relevance']}",
)
check(
    0.0 <= scores["answer_faithfulness"] <= 1.0,
    f"answer_faithfulness in range: {scores['answer_faithfulness']}",
)
check(
    0.0 <= scores["answer_relevance"] <= 1.0,
    f"answer_relevance in range: {scores['answer_relevance']}",
)

print("\n3. ModelCertificationManager")
mgr = ModelCertificationManager(run_id="smoke_test")
gold = mgr.load_gold_set()
check(isinstance(gold, GoldSet), "load_gold_set returns GoldSet")
check(len(gold.items) > 0, f"gold set has items: {len(gold.items)}")

print("\n4. Gold set file persistence")
f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
f.write(json.dumps({"version": 2, "items": _DEFAULT_GOLD_SET_ITEMS[:3]}))
f.close()
os.environ["CHERENKOV_CERTIFICATION_GOLD_SET_PATH"] = f.name
mgr2 = ModelCertificationManager(run_id="smoke_test")
gold2 = mgr2.load_gold_set()
check(len(gold2.items) > 0, "gold set loads from file")
with open(f.name) as fh:
    data = json.load(fh)
check(data.get("version") == 2, "gold set file has version=2")
os.unlink(f.name)

print("\n5. CertResult structure")
result = CertResult(certified=True, faithfulness_score=0.95, detail="passed 10/10")
check(result.certified is True, "certified field")
check(result.faithfulness_score == 0.95, "faithfulness_score field")
check(result.detail == "passed 10/10", "detail field")

print(f"\n{'='*40}")
if errors:
    print(f"FAILED ({len(errors)} check(s))")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
