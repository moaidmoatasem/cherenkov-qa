from __future__ import annotations

import json
from pathlib import Path
from cherenkov.core.config import Config
from cherenkov.core.contracts import GoldSet, CertResult, ReasoningRequest
from cherenkov.core.errors import get_logger

class ModelCertificationManager:
    def __init__(self, run_id: str | None = None):
        self.log = get_logger("CERTIFICATION", run_id)

    def load_gold_set(self) -> GoldSet:
        path = Path(Config.CERTIFICATION_GOLD_SET_PATH)
        if not path.exists():
            # Generate default gold set if it doesn't exist
            default_gold_set = {
                "items": [
                    {
                        "prompt": "Say the exact word 'CHERENKOV' and nothing else.",
                        "expected_contains": ["CHERENKOV"]
                    },
                    {
                        "prompt": "Evaluate: 2 + 2 = ?",
                        "expected_contains": ["4"]
                    }
                ]
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(default_gold_set, indent=2), encoding="utf-8")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return GoldSet(**data)

    def certify_tier(self, tier: str, provider) -> CertResult:
        """Runs the Gold-Set evaluation on the given provider model for this tier."""
        self.log.info("running model tier certification", tier=tier)
        gold_set = self.load_gold_set()
        if not gold_set.items:
            return CertResult(certified=True, faithfulness_score=1.0, detail="Gold set is empty")

        passed = 0
        total = len(gold_set.items)
        
        for item in gold_set.items:
            req = ReasoningRequest(
                task=item.prompt,
                capability_tier=tier
            )
            try:
                res = provider.generate(req)
                content = str(res.content)
                item_passed = True
                for exp in item.expected_contains:
                    if exp.lower() not in content.lower():
                        item_passed = False
                        break
                if item_passed:
                    passed += 1
            except Exception as e:
                self.log.warning("failed to generate response during certification", error=str(e))
                
        faithfulness = passed / total
        certified = faithfulness >= Config.CERTIFICATION_MIN_FAITHFULNESS
        
        detail = f"Passed {passed}/{total} items (min required faithfulness: {Config.CERTIFICATION_MIN_FAITHFULNESS})"
        self.log.info("certification complete", tier=tier, certified=certified, faithfulness=faithfulness)
        return CertResult(certified=certified, faithfulness_score=faithfulness, detail=detail)
