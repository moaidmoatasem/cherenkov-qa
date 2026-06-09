from cherenkov.ports.event_bus import EventBus
from cherenkov.ports.knowledge_repository import KnowledgeRepository
from cherenkov.ports.device_registry import DeviceRegistry
from cherenkov.ports.vlm_provider import VLMProvider


def test_event_bus_protocol_methods():
    assert hasattr(EventBus, "publish")
    assert hasattr(EventBus, "subscribe")
    assert hasattr(EventBus, "unsubscribe")


def test_event_bus_protocol_property():
    assert hasattr(EventBus, "handlers")


def test_knowledge_repository_protocol_methods():
    assert hasattr(KnowledgeRepository, "store")
    assert hasattr(KnowledgeRepository, "get")
    assert hasattr(KnowledgeRepository, "search")
    assert hasattr(KnowledgeRepository, "delete")
    assert hasattr(KnowledgeRepository, "list_by_kind")


def test_device_registry_protocol_methods():
    assert hasattr(DeviceRegistry, "register")
    assert hasattr(DeviceRegistry, "unregister")
    assert hasattr(DeviceRegistry, "get")
    assert hasattr(DeviceRegistry, "list")


def test_vlm_provider_protocol_methods():
    assert hasattr(VLMProvider, "describe_image")
    assert hasattr(VLMProvider, "compare_images")
    assert hasattr(VLMProvider, "health")
