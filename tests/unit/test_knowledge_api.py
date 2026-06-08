import unittest
from unittest.mock import patch, MagicMock
from cherenkov.knowledge.api.routes import router


class TestKnowledgeAPIRoutes(unittest.TestCase):
    def test_router_has_route(self):
        routes = [r.path for r in router.routes]
        self.assertIn("/api/v1/knowledge/query", routes)

    def test_router_is_apirouter(self):
        from fastapi import APIRouter
        self.assertIsInstance(router, APIRouter)
