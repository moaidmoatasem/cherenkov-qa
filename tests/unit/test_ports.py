import unittest
from cherenkov.ports.event_bus import EventBus
from cherenkov.ports.knowledge_repository import KnowledgeRepository
from cherenkov.ports.device_registry import DeviceRegistry
from cherenkov.ports.vlm_provider import VLMProvider


class TestEventBusProtocol(unittest.TestCase):
    def test_protocol_methods(self):
        self.assertTrue(hasattr(EventBus, "publish"))
        self.assertTrue(hasattr(EventBus, "subscribe"))
        self.assertTrue(hasattr(EventBus, "unsubscribe"))

    def test_protocol_property(self):
        self.assertTrue(hasattr(EventBus, "handlers"))


class TestKnowledgeRepositoryProtocol(unittest.TestCase):
    def test_protocol_methods(self):
        self.assertTrue(hasattr(KnowledgeRepository, "store"))
        self.assertTrue(hasattr(KnowledgeRepository, "get"))
        self.assertTrue(hasattr(KnowledgeRepository, "search"))
        self.assertTrue(hasattr(KnowledgeRepository, "delete"))
        self.assertTrue(hasattr(KnowledgeRepository, "list_by_kind"))


class TestDeviceRegistryProtocol(unittest.TestCase):
    def test_protocol_methods(self):
        self.assertTrue(hasattr(DeviceRegistry, "register"))
        self.assertTrue(hasattr(DeviceRegistry, "unregister"))
        self.assertTrue(hasattr(DeviceRegistry, "get"))
        self.assertTrue(hasattr(DeviceRegistry, "list"))


class TestVLMProviderProtocol(unittest.TestCase):
    def test_protocol_methods(self):
        self.assertTrue(hasattr(VLMProvider, "describe_image"))
        self.assertTrue(hasattr(VLMProvider, "compare_images"))
        self.assertTrue(hasattr(VLMProvider, "health"))
