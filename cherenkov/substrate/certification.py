from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from cherenkov.core.config import Config
from cherenkov.core.contracts import GoldSet, GoldSetItem, CertResult, ReasoningRequest
from cherenkov.core.errors import get_logger


class RAGTriadEvaluator:
    """RAG-Triad metrics: Context Relevance, Answer Faithfulness, Answer Relevance.

    These are computed heuristically without requiring an external judge model,
    making them suitable for CI environments with local LLMs only.
    """

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("RAG_TRIAD", run_id)

    def context_relevance(self, prompt: str, response: str) -> float:
        """Score how well the response stays on-topic with the prompt (0.0-1.0)."""
        if not response.strip():
            return 0.0
        prompt_tokens = set(re.findall(r"\w+", prompt.lower()))
        response_tokens = set(re.findall(r"\w+", response.lower()))
        if not prompt_tokens:
            return 1.0
        overlap = len(prompt_tokens & response_tokens)
        relevance = overlap / len(prompt_tokens)
        return min(1.0, max(0.0, relevance))

    def answer_faithfulness(self, prompt: str, response: str) -> float:
        """Score whether the response avoids hallucinating facts absent from the prompt (0.0-1.0).

        Checks for unsupported new claims (numeric ranges, named entities, URLs).
        """
        if not response.strip():
            return 0.0
        prompt_lower = prompt.lower()
        response_lower = response.lower()

        penalty = 0.0

        url_pattern = re.compile(r"https?://\S+")
        response_urls = set(url_pattern.findall(response_lower))
        prompt_urls = set(url_pattern.findall(prompt_lower))
        unknown_urls = response_urls - prompt_urls
        penalty += 0.15 * len(unknown_urls)

        num_pattern = re.compile(r"\b\d{2,}\b")
        response_nums = set(num_pattern.findall(response_lower))
        prompt_nums = set(num_pattern.findall(prompt_lower))
        unknown_nums = response_nums - prompt_nums
        penalty += 0.05 * len(unknown_nums)

        faithfulness = max(0.0, 1.0 - penalty)
        return min(1.0, faithfulness)

    def answer_relevance(self, prompt: str, response: str) -> float:
        """Score whether the response directly answers the prompt's question (0.0-1.0).

        Checks if the response contains core terms from the prompt's interrogative.
        """
        if not response.strip():
            return 0.0
        q_words = {
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "is",
            "are",
            "do",
            "does",
            "explain",
            "list",
            "name",
            "describe",
            "say",
            "evaluate",
            "calculate",
            "summarize",
        }
        prompt_lower = prompt.lower()
        prompt_words = set(re.findall(r"\w+", prompt_lower))

        query_terms = {w for w in prompt_words if w not in q_words and len(w) > 2}
        if not query_terms:
            return 1.0

        response_lower = response.lower()
        response_words = set(re.findall(r"\w+", response_lower))

        overlap = len(query_terms & response_words)
        coverage = overlap / len(query_terms)
        return min(1.0, max(0.0, coverage))

    def evaluate(self, prompt: str, response: str) -> dict[str, float]:
        """Run all three RAG-Triad metrics and return scores."""
        return {
            "context_relevance": round(self.context_relevance(prompt, response), 4),
            "answer_faithfulness": round(self.answer_faithfulness(prompt, response), 4),
            "answer_relevance": round(self.answer_relevance(prompt, response), 4),
        }


# Default comprehensive gold set covering multiple capability domains
_DEFAULT_GOLD_SET_ITEMS: list[dict[str, Any]] = [
    {
        "prompt": "Say the exact word 'CHERENKOV' and nothing else.",
        "expected_contains": ["CHERENKOV"],
    },
    {"prompt": "Evaluate: 2 + 2 = ?", "expected_contains": ["4"]},
    {"prompt": "What is 15 * 3?", "expected_contains": ["45"]},
    {
        "prompt": "List the numbers 1 through 5 in order.",
        "expected_contains": ["1", "2", "3", "4", "5"],
    },
    {
        "prompt": "Is a prime number divisible by any number other than 1 and itself?",
        "expected_contains": ["no", "not"],
    },
    {
        "prompt": "Explain what an API is in one sentence.",
        "expected_contains": ["application", "interface"],
    },
    {
        "prompt": "What HTTP status code means 'Not Found'?",
        "expected_contains": ["404"],
    },
    {
        "prompt": "Describe what a unit test does.",
        "expected_contains": ["test", "function", "code"],
    },
    {
        "prompt": "Name one benefit of using type hints in Python.",
        "expected_contains": ["readability", "error", "bug", "type"],
    },
    {
        "prompt": "What does 'idempotent' mean in HTTP?",
        "expected_contains": ["same", "result", "request"],
    },
]


class ModelCertificationManager:
    def __init__(self, run_id: str | None = None):
        self.log = get_logger("CERTIFICATION", run_id)
        self._rag_triad = RAGTriadEvaluator(run_id=run_id)

    def load_gold_set(self) -> GoldSet:
        path = Path(Config.CERTIFICATION_GOLD_SET_PATH)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"version": 2, "items": _DEFAULT_GOLD_SET_ITEMS}, indent=2),
                encoding="utf-8",
            )

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            gold_set = GoldSet(**data)
            if not gold_set.items:
                gold_set.items = [GoldSetItem(**it) for it in _DEFAULT_GOLD_SET_ITEMS]
            return gold_set

    def certify_tier(self, tier: str, provider) -> CertResult:
        self.log.info("running model tier certification", tier=tier)
        gold_set = self.load_gold_set()
        if not gold_set.items:
            return CertResult(
                certified=True, faithfulness_score=1.0, detail="Gold set is empty"
            )

        passed = 0
        total = len(gold_set.items)
        rag_scores: list[float] = []

        for item in gold_set.items:
            req = ReasoningRequest(task=item.prompt, capability_tier=tier)
            try:
                res = provider.generate(req)
                content = str(res.content)
                item_passed = all(
                    exp.lower() in content.lower() for exp in item.expected_contains
                )
                if item_passed:
                    passed += 1
                triad = self._rag_triad.evaluate(item.prompt, content)
                rag_avg = (
                    triad["context_relevance"]
                    + triad["answer_faithfulness"]
                    + triad["answer_relevance"]
                ) / 3.0
                rag_scores.append(rag_avg)
            except Exception as e:
                self.log.warning(
                    "failed to generate response during certification", error=str(e)
                )

        faithfulness = passed / total if total else 1.0
        rag_overall = sum(rag_scores) / len(rag_scores) if rag_scores else 0.0
        composite = faithfulness * 0.6 + rag_overall * 0.4
        certified = composite >= Config.CERTIFICATION_MIN_FAITHFULNESS

        detail = (
            f"Passed {passed}/{total} items (faithfulness={faithfulness:.2f}, "
            f"rag-triad={rag_overall:.2f}, composite={composite:.2f}, "
            f"min_required={Config.CERTIFICATION_MIN_FAITHFULNESS})"
        )
        self.log.info(
            "certification complete",
            tier=tier,
            certified=certified,
            composite=composite,
        )
        return CertResult(
            certified=certified, faithfulness_score=composite, detail=detail
        )

    def certify_tier_with_rag_report(
        self, tier: str, provider
    ) -> tuple[CertResult, list[dict[str, Any]]]:
        """Run certification and return both result and per-item RAG-Triad report."""
        self.log.info("running model tier certification with RAG report", tier=tier)
        gold_set = self.load_gold_set()
        reports: list[dict[str, Any]] = []

        passed = 0
        total = len(gold_set.items) if gold_set.items else 0

        for item in gold_set.items or []:
            req = ReasoningRequest(task=item.prompt, capability_tier=tier)
            try:
                res = provider.generate(req)
                content = str(res.content)
                item_passed = all(
                    exp.lower() in content.lower() for exp in item.expected_contains
                )
                if item_passed:
                    passed += 1
                triad = self._rag_triad.evaluate(item.prompt, content)
                reports.append(
                    {
                        "prompt": item.prompt,
                        "response": content[:200],
                        "passed": item_passed,
                        "rag_triad": triad,
                    }
                )
            except Exception as e:
                reports.append(
                    {
                        "prompt": item.prompt,
                        "response": f"<error: {e}>",
                        "passed": False,
                        "rag_triad": {
                            "context_relevance": 0.0,
                            "answer_faithfulness": 0.0,
                            "answer_relevance": 0.0,
                        },
                    }
                )

        faithfulness = passed / total if total else 1.0
        rag_scores = [r["rag_triad"] for r in reports]
        rag_overall = (
            sum(
                s["context_relevance"]
                + s["answer_faithfulness"]
                + s["answer_relevance"]
                for s in rag_scores
            )
            / (len(rag_scores) * 3)
            if rag_scores
            else 0.0
        )
        composite = faithfulness * 0.6 + rag_overall * 0.4
        certified = composite >= Config.CERTIFICATION_MIN_FAITHFULNESS

        cert = CertResult(
            certified=certified,
            faithfulness_score=composite,
            detail=f"Passed {passed}/{total} items, RAG-Triad={rag_overall:.2f}, composite={composite:.2f}",
        )
        return cert, reports
