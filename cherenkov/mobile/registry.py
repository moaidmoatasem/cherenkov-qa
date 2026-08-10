"""
CHERENKOV mobile/registry.py — device registry with claim/release semantics.

Inspired by Astur's per-worker device locking: a device is claimed by exactly
one session at a time; a second claim attempt raises DeviceClaimedError.
"""

from __future__ import annotations

import threading
import uuid

from cherenkov.mobile.contracts import (
    DeviceInfo,
    DeviceKind,
    DeviceState,
    MobileSession,
    MobileSessionStatus,
    PlatformName,
)


class DeviceClaimedError(Exception):
    """Raised when a device is already claimed by another session."""

class DeviceNotFoundError(Exception):
    """Raised when a requested device_id is not in the registry."""

class DeviceRegistry:
    """Thread-safe registry of known devices with claim/release lifecycle.

    Each device can be held by at most one session at a time. This mirrors
    Astur's per-Playwright-worker device locking, adapted for concurrent HTTP
    requests to the CHERENKOV dashboard server.
    """

    def __init__(self) -> None:
        """Initialize empty DeviceRegistry instance."""
        self._lock = threading.Lock()
        self._devices: dict[str, DeviceInfo] = {}
        self._sessions: dict[str, MobileSession] = {}
        self._device_to_session: dict[str, str] = {}

    # ── Device management ────────────────────────────────────────────────────

    def register_device(self, device: DeviceInfo) -> None:
        """Register a new device in the registry.

        Args:
            device: DeviceInfo object describing the target device.
        """
        with self._lock:
            self._devices[device.device_id] = device

    def list_devices(self) -> list[DeviceInfo]:
        """List all currently registered devices.

        Returns:
            List of DeviceInfo instances.
        """
        with self._lock:
            return list(self._devices.values())

    def get_device(self, device_id: str) -> DeviceInfo | None:
        """Retrieve registered device metadata by ID.

        Args:
            device_id: Unique identifier string of the device.

        Returns:
            DeviceInfo instance if found, or None.
        """
        with self._lock:
            return self._devices.get(device_id)

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def claim(
        self,
        device_id: str,
        app_package: str = "",
        app_activity: str = "",
    ) -> MobileSession:
        """Claim a device for exclusive use and return a new session.

        Args:
            device_id: Target device identifier to claim.
            app_package: Optional target application package name.
            app_activity: Optional target activity name.

        Returns:
            New claimed MobileSession instance.

        Raises:
            DeviceNotFoundError: device_id not registered.
            DeviceClaimedError: device is already held by another session.
        """
        with self._lock:
            if device_id not in self._devices:
                raise DeviceNotFoundError(device_id)
            if device_id in self._device_to_session:
                existing = self._device_to_session[device_id]
                raise DeviceClaimedError(
                    f"Device {device_id!r} is already claimed by session {existing!r}"
                )
            session = MobileSession(
                session_id=str(uuid.uuid4()),
                device=self._devices[device_id],
                status=MobileSessionStatus.CLAIMED,
                app_package=app_package,
                app_activity=app_activity,
            )
            self._sessions[session.session_id] = session
            self._device_to_session[device_id] = session.session_id
            return session

    def get_session(self, session_id: str) -> MobileSession | None:
        """Retrieve an active or historic mobile session by ID.

        Args:
            session_id: Unique session UUID string.

        Returns:
            MobileSession instance if found, or None.
        """
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> list[MobileSession]:
        """List all active and closed mobile sessions.

        Returns:
            List of MobileSession instances.
        """
        with self._lock:
            return list(self._sessions.values())

    def update_session_status(
        self, session_id: str, status: MobileSessionStatus, error: str = ""
    ) -> None:
        """Update status and optional error message for a session.

        Args:
            session_id: Target session UUID string.
            status: Target MobileSessionStatus value.
            error: Optional error detail message string.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = status
                if error:
                    session.error = error

    def append_step(self, session_id: str, step: dict) -> None:
        """Append an executed step log entry to a session.

        Args:
            session_id: Target session UUID string.
            step: Step data dictionary describing the executed action.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.steps.append(step)

    def release(self, session_id: str) -> None:
        """Release the device claim and mark the session closed.

        Args:
            session_id: Target session UUID string to release.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            session.status = MobileSessionStatus.CLOSED
            device_id = session.device.device_id
            self._device_to_session.pop(device_id, None)

    def session_for_device(self, device_id: str) -> MobileSession | None:
        """Find the active session currently claiming a device.

        Args:
            device_id: Target device identifier.

        Returns:
            Active MobileSession instance claiming the device, or None.
        """
        with self._lock:
            sid = self._device_to_session.get(device_id)
            return self._sessions.get(sid) if sid else None

# Module-level singleton used by the FastAPI routes.
_registry = DeviceRegistry()

# Pre-register a default Android emulator so the API works out-of-the-box
# in dev/CI environments that have AVD running on 5554.
_registry.register_device(
    DeviceInfo(
        device_id="emulator-5554",
        platform=PlatformName.ANDROID,
        kind=DeviceKind.EMULATOR,
        state=DeviceState.UNKNOWN,
        name="Android Emulator",
    )
)

def get_registry() -> DeviceRegistry:
    """Get the global DeviceRegistry singleton instance.

    Returns:
        The module-level DeviceRegistry instance.
    """
    return _registry
