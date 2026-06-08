import unittest
from cherenkov.core.knowledge_result import KnowledgeResult, KnowledgeKind


class TestKnowledgeKind(unittest.TestCase):
    def test_kinds(self):
        self.assertIn(KnowledgeKind.IDIOM, KnowledgeKind)
        self.assertIn(KnowledgeKind.FEEDBACK, KnowledgeKind)
        self.assertIn(KnowledgeKind.VERDICT, KnowledgeKind)
        self.assertIn(KnowledgeKind.INSIGHT, KnowledgeKind)


class TestKnowledgeResult(unittest.TestCase):
    def test_default_init(self):
        kr = KnowledgeResult(id="t1", kind=KnowledgeKind.IDIOM, key="/api/test", summary="a test")
        self.assertEqual(kr.id, "t1")
        self.assertEqual(kr.kind, KnowledgeKind.IDIOM)
        self.assertEqual(kr.key, "/api/test")
        self.assertEqual(kr.summary, "a test")
        self.assertTrue(kr.created_at)

    def test_to_event_payload(self):
        kr = KnowledgeResult(
            id="t1", kind=KnowledgeKind.VERDICT, key="/api/users",
            summary="verdict for users", source="skeptic", confidence=0.95,
            tags=["regression"]
        )
        p = kr.to_event_payload()
        self.assertEqual(p["id"], "t1")
        self.assertEqual(p["kind"], "verdict")
        self.assertEqual(p["key"], "/api/users")
        self.assertEqual(p["confidence"], 0.95)
        self.assertEqual(p["tags"], ["regression"])

    def test_created_at_auto_set(self):
        kr = KnowledgeResult(id="t2", kind=KnowledgeKind.INSIGHT, key="/x", summary="x")
        self.assertIn("T", kr.created_at)

    def test_ttl_default_zero(self):
        kr = KnowledgeResult(id="t3", kind=KnowledgeKind.SPEC_FACT, key="/y", summary="y")
        self.assertEqual(kr.ttl_seconds, 0)
