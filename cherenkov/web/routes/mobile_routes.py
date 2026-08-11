"""
Mobile pilot endpoints — device registry, session lifecycle.

Architecture inspired by Astur (Astur-mobile/Astur): per-session device locking,
protocol types first, no Appium dependency in the domain layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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
    get_registry,
)
from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role

router = APIRouter(tags=["mobile"])


# ── Request/response models ──────────────────────────────────────────────────

# ── Request/response models ──────────────────────────────────────────────────

class RegisterDeviceRequest(BaseModel):
    """Payload model for registering a mobile testing device."""
    device_id: str
    platform: PlatformName
    kind: DeviceKind
    name: str = ""
    os_version: str = ""
    api_level: str = ""


class ClaimSessionRequest(BaseModel):
    """Payload model for claiming a device and initiating a mobile testing session."""
    device_id: str
    app_package: str = ""
    app_activity: str = ""


class SessionStepRequest(BaseModel):
    """Payload model for recording a step execution within a mobile session."""
    action: str
    target: str = ""
    expected: str = ""
    actual: str = ""
    status: str = "pending"


class UpdateSessionRequest(BaseModel):
    """Payload model for updating the status of an active mobile session."""
    status: MobileSessionStatus
    error: str = ""


# ── Device endpoints ─────────────────────────────────────────────────────────

@router.get("/api/v1/mobile/devices")
async def list_devices():
    """List all registered devices and their current claim state.

    Returns:
        Dictionary payload containing list of device dictionaries and total count.
    """
    registry = get_registry()
    devices = registry.list_devices()
    result = []
    for d in devices:
        session = registry.session_for_device(d.device_id)
        result.append({
            **d.to_dict(),
            "claimed_by": session.session_id if session else None,
        })
    return {"devices": result, "total": len(result)}


@router.post("/api/v1/mobile/devices")
async def register_device(req: RegisterDeviceRequest, _role=Depends(require_role(Role.reviewer))):
    """Register a new device in the registry.

    Args:
        req: RegisterDeviceRequest object containing device parameters.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary containing registered device dictionary.
    """
    registry = get_registry()
    device = DeviceInfo(
        device_id=req.device_id,
        platform=req.platform,
        kind=req.kind,
        state=DeviceState.UNKNOWN,
        name=req.name,
        os_version=req.os_version,
        api_level=req.api_level,
    )
    registry.register_device(device)
    return {"registered": device.to_dict()}


@router.get("/api/v1/mobile/devices/{device_id}")
async def get_device(device_id: str):
    """Get a specific device's info and current session.

    Args:
        device_id: Target device identifier string.

    Returns:
        Dictionary containing device details and current session claim info.

    Raises:
        HTTPException: 404 Not Found if device_id is not registered.
    """
    registry = get_registry()
    device = registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id!r} not found")
    session = registry.session_for_device(device_id)
    return {
        **device.to_dict(),
        "claimed_by": session.session_id if session else None,
    }


# ── Session endpoints ─────────────────────────────────────────────────────────

@router.post("/api/v1/mobile/sessions")
async def create_session(req: ClaimSessionRequest, _role=Depends(require_role(Role.reviewer))):
    """Claim a device and open a new session. Fails if device is already claimed.

    Args:
        req: ClaimSessionRequest payload.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary representation of created MobileSession.

    Raises:
        HTTPException: 404 if device not found, or 409 if device already claimed.
    """
    registry = get_registry()
    try:
        session = registry.claim(
            device_id=req.device_id,
            app_package=req.app_package,
            app_activity=req.app_activity,
        )
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Device {req.device_id!r} not found") from None
    except DeviceClaimedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return session.to_dict()


@router.get("/api/v1/mobile/sessions")
async def list_sessions():
    """List all sessions (active and closed).

    Returns:
        Dictionary payload listing sessions array and total count.
    """
    registry = get_registry()
    sessions = registry.list_sessions()
    return {"sessions": [s.to_dict() for s in sessions], "total": len(sessions)}


@router.get("/api/v1/mobile/sessions/{session_id}")
async def get_session(session_id: str):
    """Get details for a specific session.

    Args:
        session_id: Unique session identifier string.

    Returns:
        Dictionary representing the MobileSession.

    Raises:
        HTTPException: 404 Not Found if session_id is missing.
    """
    registry = get_registry()
    session = registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session.to_dict()


@router.patch("/api/v1/mobile/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest, _role=Depends(require_role(Role.reviewer))):
    """Update a session's status (e.g. running → failed).

    Args:
        session_id: Target session ID string.
        req: UpdateSessionRequest payload containing status and optional error.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary summarizing updated status.

    Raises:
        HTTPException: 404 Not Found if session_id does not exist.
    """
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    registry.update_session_status(session_id, req.status, req.error)
    return {"updated": session_id, "status": req.status.value}


@router.post("/api/v1/mobile/sessions/{session_id}/steps")
async def append_step(session_id: str, req: SessionStepRequest, _role=Depends(require_role(Role.reviewer))):
    """Append a step record to a session's execution log.

    Args:
        session_id: Target session ID string.
        req: SessionStepRequest payload.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary payload containing appended step parameters.

    Raises:
        HTTPException: 404 Not Found if session_id does not exist.
    """
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    step = req.model_dump()
    registry.append_step(session_id, step)
    return {"appended": step}


@router.delete("/api/v1/mobile/sessions/{session_id}")
async def close_session(session_id: str, _role=Depends(require_role(Role.reviewer))):
    """Release the device claim and close the session.

    Args:
        session_id: Target session ID string.
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming session closure.

    Raises:
        HTTPException: 404 Not Found if session_id does not exist.
    """
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    registry.release(session_id)
    return {"closed": session_id}


# ── Legacy pilot endpoints (backwards compat) ────────────────────────────────

@router.get("/api/v1/mobile/pilot/status")
async def get_mobile_pilot_status():
    """Legacy: return the first active session as a flat pilot status dict.

    Returns:
        Dictionary status payload for legacy dashboard widget compatibility.
    """
    registry = get_registry()
    sessions = registry.list_sessions()
    active = next(
        (s for s in sessions if s.status not in (
            MobileSessionStatus.CLOSED, MobileSessionStatus.IDLE
        )),
        None,
    )
    if active:
        return {
            "status": active.status.value,
            "session_id": active.session_id,
            "device_id": active.device.device_id,
            "current_step": len(active.steps),
            "total_steps": len(active.steps),
            "steps": active.steps,
        }
    return {
        "status": "idle",
        "session_id": None,
        "device_id": None,
        "current_step": 0,
        "total_steps": 0,
        "steps": [],
    }


@router.post("/api/v1/mobile/pilot/start")
async def start_mobile_pilot(_role=Depends(require_role(Role.reviewer))):
    """Legacy: claim the default emulator and start a session.

    Args:
        _role: Required reviewer role authorization dependency.

    Returns:
        Dictionary confirming started status and session ID.

    Raises:
        HTTPException: 409 if device claimed, 503 if default emulator unavailable.
    """
    registry = get_registry()
    try:
        session = registry.claim(device_id="emulator-5554")
        registry.update_session_status(session.session_id, MobileSessionStatus.RUNNING)
        return {"status": "started", "session_id": session.session_id}
    except DeviceClaimedError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except DeviceNotFoundError:
        raise HTTPException(status_code=503, detail="Default emulator not available") from None
