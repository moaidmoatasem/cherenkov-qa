from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity


def test_event_categories():
    assert EventCategory.PIPELINE in EventCategory
    assert EventCategory.HITL in EventCategory
    assert EventCategory.HEALING in EventCategory
    assert EventCategory.KNOWLEDGE in EventCategory
    assert EventCategory.SYSTEM in EventCategory


def test_cherenkov_event_default_init():
    ev = CHERENKOVEvent(category=EventCategory.SYSTEM, name="test")
    assert ev.category == EventCategory.SYSTEM
    assert ev.name == "test"
    assert ev.severity == EventSeverity.INFO
    assert ev.event_id
    assert ev.timestamp > 0


def test_cherenkov_event_to_dict():
    ev = CHERENKOVEvent(category=EventCategory.PIPELINE, name="pipeline.start",
                        payload={"run_id": "abc"}, severity=EventSeverity.INFO)
    d = ev.to_dict()
    assert d["name"] == "pipeline.start"
    assert d["category"] == "pipeline"
    assert d["payload"]["run_id"] == "abc"
    assert "event_id" in d
    assert "timestamp" in d
    assert "source" in d
    assert "correlation_id" in d


def test_pipeline_start_factory():
    ev = CHERENKOVEvent.pipeline_start("run-1", scenarios=5)
    assert ev.name == "pipeline.start"
    assert ev.category == EventCategory.PIPELINE
    assert ev.correlation_id == "run-1"
    assert ev.payload["scenarios"] == 5


def test_pipeline_complete_factory():
    ev = CHERENKOVEvent.pipeline_complete("run-1", success=True, passed=3, total=3)
    assert ev.name == "pipeline.complete"
    assert ev.severity == EventSeverity.INFO
    assert ev.payload["success"]


def test_pipeline_complete_failure_severity():
    ev = CHERENKOVEvent.pipeline_complete("run-1", success=False)
    assert ev.severity == EventSeverity.WARNING


def test_hitl_factories():
    ev = CHERENKOVEvent.hitl_approved("item-1", actor="bob")
    assert ev.name == "hitl.approved"
    assert ev.correlation_id == "item-1"

    ev2 = CHERENKOVEvent.hitl_rejected("item-2", reason="bad", actor="alice")
    assert ev2.name == "hitl.rejected"
    assert ev2.severity == EventSeverity.WARNING


def test_healing_suggested_factory():
    ev = CHERENKOVEvent.healing_suggested("scenario-1", "AuthExpiryHealer")
    assert ev.name == "healing.suggested"
    assert ev.correlation_id == "scenario-1"


def test_knowledge_stored_factory():
    ev = CHERENKOVEvent.knowledge_stored("/api/test", "skeptic")
    assert ev.name == "knowledge.stored"
    assert ev.correlation_id == "/api/test"


def test_system_health_factory():
    ev = CHERENKOVEvent.system_health("ok")
    assert ev.severity == EventSeverity.INFO

    ev2 = CHERENKOVEvent.system_health("degraded", detail="slow")
    assert ev2.severity == EventSeverity.WARNING
