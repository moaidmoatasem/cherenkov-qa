import unittest
from cherenkov.core.events import CHERENKOVEvent, EventCategory, EventSeverity


class TestEventCategory(unittest.TestCase):
    def test_categories(self):
        self.assertIn(EventCategory.PIPELINE, EventCategory)
        self.assertIn(EventCategory.HITL, EventCategory)
        self.assertIn(EventCategory.HEALING, EventCategory)
        self.assertIn(EventCategory.KNOWLEDGE, EventCategory)
        self.assertIn(EventCategory.SYSTEM, EventCategory)


class TestCHERENKOVEvent(unittest.TestCase):
    def test_default_init(self):
        ev = CHERENKOVEvent(category=EventCategory.SYSTEM, name="test")
        self.assertEqual(ev.category, EventCategory.SYSTEM)
        self.assertEqual(ev.name, "test")
        self.assertEqual(ev.severity, EventSeverity.INFO)
        self.assertTrue(ev.event_id)
        self.assertTrue(ev.timestamp > 0)

    def test_to_dict(self):
        ev = CHERENKOVEvent(category=EventCategory.PIPELINE, name="pipeline.start",
                             payload={"run_id": "abc"}, severity=EventSeverity.INFO)
        d = ev.to_dict()
        self.assertEqual(d["name"], "pipeline.start")
        self.assertEqual(d["category"], "pipeline")
        self.assertEqual(d["payload"]["run_id"], "abc")
        self.assertIn("event_id", d)
        self.assertIn("timestamp", d)
        self.assertIn("source", d)
        self.assertIn("correlation_id", d)

    def test_pipeline_start_factory(self):
        ev = CHERENKOVEvent.pipeline_start("run-1", scenarios=5)
        self.assertEqual(ev.name, "pipeline.start")
        self.assertEqual(ev.category, EventCategory.PIPELINE)
        self.assertEqual(ev.correlation_id, "run-1")
        self.assertEqual(ev.payload["scenarios"], 5)

    def test_pipeline_complete_factory(self):
        ev = CHERENKOVEvent.pipeline_complete("run-1", success=True, passed=3, total=3)
        self.assertEqual(ev.name, "pipeline.complete")
        self.assertEqual(ev.severity, EventSeverity.INFO)
        self.assertTrue(ev.payload["success"])

    def test_pipeline_complete_failure_severity(self):
        ev = CHERENKOVEvent.pipeline_complete("run-1", success=False)
        self.assertEqual(ev.severity, EventSeverity.WARNING)

    def test_hitl_factories(self):
        ev = CHERENKOVEvent.hitl_approved("item-1", actor="bob")
        self.assertEqual(ev.name, "hitl.approved")
        self.assertEqual(ev.correlation_id, "item-1")

        ev2 = CHERENKOVEvent.hitl_rejected("item-2", reason="bad", actor="alice")
        self.assertEqual(ev2.name, "hitl.rejected")
        self.assertEqual(ev2.severity, EventSeverity.WARNING)

    def test_healing_suggested_factory(self):
        ev = CHERENKOVEvent.healing_suggested("scenario-1", "AuthExpiryHealer")
        self.assertEqual(ev.name, "healing.suggested")
        self.assertEqual(ev.correlation_id, "scenario-1")

    def test_knowledge_stored_factory(self):
        ev = CHERENKOVEvent.knowledge_stored("/api/test", "skeptic")
        self.assertEqual(ev.name, "knowledge.stored")
        self.assertEqual(ev.correlation_id, "/api/test")

    def test_system_health_factory(self):
        ev = CHERENKOVEvent.system_health("ok")
        self.assertEqual(ev.severity, EventSeverity.INFO)

        ev2 = CHERENKOVEvent.system_health("degraded", detail="slow")
        self.assertEqual(ev2.severity, EventSeverity.WARNING)
