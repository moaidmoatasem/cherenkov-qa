"""Unit tests for cherenkov.mobile — contracts and device registry."""

import pytest

from cherenkov.mobile.contracts import (
    DeviceKind,
    DeviceState,
    MobileSessionStatus,
    PlatformName,
)
from cherenkov.mobile.registry import (
    DeviceClaimedError,
    DeviceInfo,
    DeviceNotFoundError,
    DeviceRegistry,
)


@pytest.fixture()
def registry():
    r = DeviceRegistry()
    r.register_device(
        DeviceInfo(
            device_id="emulator-5554",
            platform=PlatformName.ANDROID,
            kind=DeviceKind.EMULATOR,
            state=DeviceState.ONLINE,
            name="Test AVD",
        )
    )
    return r


def test_list_devices(registry):
    devices = registry.list_devices()
    assert len(devices) == 1
    assert devices[0].device_id == "emulator-5554"


def test_claim_returns_session(registry):
    session = registry.claim("emulator-5554", app_package="com.example")
    assert session.session_id
    assert session.status == MobileSessionStatus.CLAIMED
    assert session.device.device_id == "emulator-5554"
    assert session.app_package == "com.example"


def test_double_claim_raises(registry):
    registry.claim("emulator-5554")
    with pytest.raises(DeviceClaimedError):
        registry.claim("emulator-5554")


def test_claim_unknown_device_raises(registry):
    with pytest.raises(DeviceNotFoundError):
        registry.claim("nonexistent-device")


def test_release_frees_device(registry):
    session = registry.claim("emulator-5554")
    registry.release(session.session_id)
    session2 = registry.claim("emulator-5554")
    assert session2.session_id != session.session_id


def test_session_status_update(registry):
    session = registry.claim("emulator-5554")
    registry.update_session_status(session.session_id, MobileSessionStatus.RUNNING)
    updated = registry.get_session(session.session_id)
    assert updated.status == MobileSessionStatus.RUNNING


def test_session_error_recorded(registry):
    session = registry.claim("emulator-5554")
    registry.update_session_status(
        session.session_id, MobileSessionStatus.FAILED, error="ADB not found"
    )
    updated = registry.get_session(session.session_id)
    assert updated.status == MobileSessionStatus.FAILED
    assert "ADB not found" in updated.error


def test_append_step(registry):
    session = registry.claim("emulator-5554")
    step = {"action": "tap", "target": "Login", "status": "done"}
    registry.append_step(session.session_id, step)
    updated = registry.get_session(session.session_id)
    assert len(updated.steps) == 1
    assert updated.steps[0]["action"] == "tap"


def test_session_for_device_none_when_free(registry):
    assert registry.session_for_device("emulator-5554") is None


def test_session_for_device_returns_session(registry):
    session = registry.claim("emulator-5554")
    found = registry.session_for_device("emulator-5554")
    assert found is not None
    assert found.session_id == session.session_id


def test_to_dict_shapes(registry):
    session = registry.claim("emulator-5554", app_package="com.test")
    d = session.to_dict()
    assert d["status"] == "claimed"
    assert d["device"]["platform"] == "android"
    assert d["device"]["kind"] == "emulator"
    assert d["app_package"] == "com.test"
