"""
Mobile pilot endpoints — device registry, session lifecycle.

Architecture inspired by Astur (Astur-mobile/Astur): per-session device locking,
protocol types first, no Appium dependency in the domain layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cherenkov.web.auth.deps import require_role
from cherenkov.web.auth.models import Role
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

router = APIRouter(tags=["mobile"])


# ── Request/response models ──────────────────────────────────────────────────

class RegisterDeviceRequest(BaseModel):
    device_id: str
    platform: PlatformName
    kind: DeviceKind
    name: str = ""
    os_version: str = ""
    api_level: str = ""


class ClaimSessionRequest(BaseModel):
    device_id: str
    app_package: str = ""
    app_activity: str = ""


class SessionStepRequest(BaseModel):
    action: str
    target: str = ""
    expected: str = ""
    actual: str = ""
    status: str = "pending"


class UpdateSessionRequest(BaseModel):
    status: MobileSessionStatus
    error: str = ""


# ── Device endpoints ─────────────────────────────────────────────────────────

@router.get("/api/v1/mobile/devices")
async def list_devices():
    """List all registered devices and their current claim state."""
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
    """Register a new device in the registry."""
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
    """Get a specific device's info and current session."""
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
    """Claim a device and open a new session. Fails if device is already claimed."""
    registry = get_registry()
    try:
        session = registry.claim(
            device_id=req.device_id,
            app_package=req.app_package,
            app_activity=req.app_activity,
        )
    except DeviceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Device {req.device_id!r} not found")
    except DeviceClaimedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return session.to_dict()


@router.get("/api/v1/mobile/sessions")
async def list_sessions():
    """List all sessions (active and closed)."""
    registry = get_registry()
    sessions = registry.list_sessions()
    return {"sessions": [s.to_dict() for s in sessions], "total": len(sessions)}


@router.get("/api/v1/mobile/sessions/{session_id}")
async def get_session(session_id: str):
    """Get details for a specific session."""
    registry = get_registry()
    session = registry.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session.to_dict()


@router.patch("/api/v1/mobile/sessions/{session_id}")
async def update_session(session_id: str, req: UpdateSessionRequest, _role=Depends(require_role(Role.reviewer))):
    """Update a session's status (e.g. running → failed)."""
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    registry.update_session_status(session_id, req.status, req.error)
    return {"updated": session_id, "status": req.status.value}


@router.post("/api/v1/mobile/sessions/{session_id}/steps")
async def append_step(session_id: str, req: SessionStepRequest, _role=Depends(require_role(Role.reviewer))):
    """Append a step record to a session's execution log."""
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    step = req.model_dump()
    registry.append_step(session_id, step)
    return {"appended": step}


@router.delete("/api/v1/mobile/sessions/{session_id}")
async def close_session(session_id: str, _role=Depends(require_role(Role.reviewer))):
    """Release the device claim and close the session."""
    registry = get_registry()
    if not registry.get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    registry.release(session_id)
    return {"closed": session_id}


# ── Legacy pilot endpoints (backwards compat) ────────────────────────────────

@router.get("/api/v1/mobile/pilot/status")
async def get_mobile_pilot_status():
    """Legacy: return the first active session as a flat pilot status dict."""
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
    """Legacy: claim the default emulator and start a session."""
    registry = get_registry()
    try:
        session = registry.claim(device_id="emulator-5554")
        registry.update_session_status(session.session_id, MobileSessionStatus.RUNNING)
        return {"status": "started", "session_id": session.session_id}
    except DeviceClaimedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DeviceNotFoundError:
        raise HTTPException(status_code=503, detail="Default emulator not available")
