import os
import json
import sqlite3
import pytest
from pathlib import Path

from cherenkov.core.config import Config
from cherenkov.core.contracts import (
    ReasoningRequest,
    ReasoningResult,
    VerdictRecord,
    VerdictOutcome,
    DivergenceClass,
    Idiom,
)
from cherenkov.substrate.certification import ModelCertificationManager
from cherenkov.substrate.router import SubstrateRouter
from cherenkov.ai.accounting import CostAccountant
from cherenkov.copilot.mentor import Mentor
from cherenkov.reflector.store import VerdictStore


class DummyProvider:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls = []

    def generate(self, request: ReasoningRequest) -> ReasoningResult:
        self.calls.append(request)
        return ReasoningResult(
            content=self.reply,
            provider="dummy",
            model="dummy-model",
        )

    def capabilities(self):
        from cherenkov.substrate.provider import ProviderCapabilities
        return ProviderCapabilities(
            capability_tiers=["small"],
            requires_egress=False,
            provider_name="dummy",
        )


def test_model_certification(tmp_path):
    gold_set_file = tmp_path / "gold_set.json"
    gold_set_data = {
        "items": [
            {
                "prompt": "Test word 'HELLO'.",
                "expected_contains": ["HELLO"]
            }
        ]
    }
    gold_set_file.write_text(json.dumps(gold_set_data), encoding="utf-8")

    # Set Config to use our temp gold set
    old_path = Config.CERTIFICATION_GOLD_SET_PATH
    Config.CERTIFICATION_GOLD_SET_PATH = str(gold_set_file)

    try:
        manager = ModelCertificationManager()
        
        # certify_tier now reports a RAG-Triad *composite* score in
        # faithfulness_score (faithfulness*0.6 + rag_overall*0.4), certified when
        # composite >= Config.CERTIFICATION_MIN_FAITHFULNESS. Assert on the
        # contract (certified flag + threshold band), not brittle exact floats.
        threshold = Config.CERTIFICATION_MIN_FAITHFULNESS

        # Test passing provider
        passing_prov = DummyProvider("Here is the HELLO word.")
        res = manager.certify_tier("small", passing_prov)
        assert res.certified is True
        assert res.faithfulness_score >= threshold

        # Test failing provider
        failing_prov = DummyProvider("No matching keyword.")
        res_fail = manager.certify_tier("small", failing_prov)
        assert res_fail.certified is False
        assert res_fail.faithfulness_score < threshold

    finally:
        Config.CERTIFICATION_GOLD_SET_PATH = old_path


def test_mentor_and_governance_kpis(tmp_path):
    db_file = tmp_path / "test_verdicts.db"
    store = VerdictStore(db_path=str(db_file))
    
    # Store some verdicts
    v1 = VerdictRecord(
        id="v1",
        hypothesis_id="h1",
        outcome=VerdictOutcome.ACCEPT,
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="GET /api/users",
        source="skeptic",
        timestamp=100,
    )
    v2 = VerdictRecord(
        id="v2",
        hypothesis_id="h2",
        outcome=VerdictOutcome.REJECT,
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="GET /api/users",
        source="skeptic",
        timestamp=200,
    )
    v3 = VerdictRecord(
        id="v3",
        hypothesis_id="h3",
        outcome=VerdictOutcome.ESCAPED_DEFECT,
        divergence_class=DivergenceClass.D2_CODE_PROD,
        endpoint="POST /api/login",
        source="healing",
        timestamp=300,
    )
    store.record_verdict(v1)
    store.record_verdict(v2)
    store.record_verdict(v3)

    # Store some idioms
    idiom1 = Idiom(
        id="idiom1",
        pattern="Test idiom pattern",
        divergence_class=DivergenceClass.D1_SPEC_CODE,
        endpoint="GET /api/users",
        confirm_count=2,
        last_confirmed=400,
        decay_score=0.9,
    )
    store.upsert_idiom(idiom1)

    # Test Mentor suggestions
    mentor = Mentor(store=store)
    suggestions = mentor.get_suggestions(endpoint="/api/users")
    assert len(suggestions) == 1
    assert suggestions[0].id == "idiom1"

    # Test cost accountant governance KPIs using the test DB
    # We temporarily monkeypatch VerdictStore default path or pass store dependency
    # Let's override store db_path temporarily in VerdictStore._default_db_path or just patch VerdictStore
    import cherenkov.reflector.store
    old_default = cherenkov.reflector.store._default_db_path
    cherenkov.reflector.store._default_db_path = lambda: str(db_file)

    try:
        acc = CostAccountant()
        kpis = acc.get_governance_kpis()
        assert kpis["defect_escape_count"] == 1
        assert kpis["total_verdicts"] == 3
        # accepts=1, rejects=1 -> false positive rate = 1 / 2 = 0.5
        assert kpis["false_positive_rate"] == 0.5
        # (accepts=1 + escaped=1) / total=3 = 2/3 = 0.6667
        assert kpis["maintenance_efficiency"] == 0.6667
    finally:
        cherenkov.reflector.store._default_db_path = old_default


def test_router_certification_gate(tmp_path):
    from cherenkov.core.errors import CertificationError

    gold_set_file = tmp_path / "gold_set.json"
    gold_set_data = {
        "items": [
            {
                "prompt": "Test word 'HELLO'.",
                "expected_contains": ["HELLO"]
            }
        ]
    }
    gold_set_file.write_text(json.dumps(gold_set_data), encoding="utf-8")

    old_path = Config.CERTIFICATION_GOLD_SET_PATH
    old_enabled = Config.CERTIFICATION_ENABLED
    
    Config.CERTIFICATION_GOLD_SET_PATH = str(gold_set_file)
    Config.CERTIFICATION_ENABLED = True

    try:
        router = SubstrateRouter()
        
        # Mock provider_for_tier to return failing dummy
        import cherenkov.substrate.router
        old_provider_for_tier = cherenkov.substrate.router.provider_for_tier
        cherenkov.substrate.router.provider_for_tier = lambda tier: DummyProvider("Fail response")
        
        req = ReasoningRequest(task="Test task", capability_tier="small")
        with pytest.raises(CertificationError):
            router.route(req)
            
        # Switch provider to passing dummy
        cherenkov.substrate.router.provider_for_tier = lambda tier: DummyProvider("Here is HELLO")
        # Creating new router instance so cache is clean
        router2 = SubstrateRouter()
        res = router2.route(req)
        assert res.provider == "dummy"
        
        cherenkov.substrate.router.provider_for_tier = old_provider_for_tier
    finally:
        Config.CERTIFICATION_GOLD_SET_PATH = old_path
        Config.CERTIFICATION_ENABLED = old_enabled

