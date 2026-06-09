from cherenkov.core.knowledge_result import KnowledgeResult, KnowledgeKind


def test_kinds():
    assert KnowledgeKind.IDIOM in KnowledgeKind
    assert KnowledgeKind.FEEDBACK in KnowledgeKind
    assert KnowledgeKind.VERDICT in KnowledgeKind
    assert KnowledgeKind.INSIGHT in KnowledgeKind


def test_knowledge_result_default_init():
    kr = KnowledgeResult(id="t1", kind=KnowledgeKind.IDIOM, key="/api/test", summary="a test")
    assert kr.id == "t1"
    assert kr.kind == KnowledgeKind.IDIOM
    assert kr.key == "/api/test"
    assert kr.summary == "a test"
    assert kr.created_at


def test_to_event_payload():
    kr = KnowledgeResult(
        id="t1", kind=KnowledgeKind.VERDICT, key="/api/users",
        summary="verdict for users", source="skeptic", confidence=0.95,
        tags=["regression"]
    )
    p = kr.to_event_payload()
    assert p["id"] == "t1"
    assert p["kind"] == "verdict"
    assert p["key"] == "/api/users"
    assert p["confidence"] == 0.95
    assert p["tags"] == ["regression"]


def test_created_at_auto_set():
    kr = KnowledgeResult(id="t2", kind=KnowledgeKind.INSIGHT, key="/x", summary="x")
    assert "T" in kr.created_at


def test_ttl_default_zero():
    kr = KnowledgeResult(id="t3", kind=KnowledgeKind.SPEC_FACT, key="/y", summary="y")
    assert kr.ttl_seconds == 0
