"""
Mobile pilot status and control endpoints.
"""
from fastapi import APIRouter

router = APIRouter(tags=["mobile"])

_mobile_pilot_status = {
    "status": "idle",
    "current_step": 0,
    "total_steps": 6,
    "steps": [
        {"step_id": "1", "action": "Connect device", "target": "android-emulator",
         "expected": "device online", "actual": "", "status": "pending"},
        {"step_id": "2", "action": "Install APK", "target": "app-debug.apk",
         "expected": "install success", "actual": "", "status": "pending"},
        {"step_id": "3", "action": "Launch app", "target": "com.example.app",
         "expected": "app foreground", "actual": "", "status": "pending"},
        {"step_id": "4", "action": "Run login test", "target": "LoginScreen",
         "expected": "200 OK", "actual": "", "status": "pending"},
        {"step_id": "5", "action": "Run checkout flow", "target": "CheckoutScreen",
         "expected": "order confirmed", "actual": "", "status": "pending"},
        {"step_id": "6", "action": "Collect logs", "target": "logcat",
         "expected": "logs saved", "actual": "", "status": "pending"},
    ],
}


@router.get("/api/v1/mobile/pilot/status")
async def get_mobile_pilot_status():
    return _mobile_pilot_status


@router.post("/api/v1/mobile/pilot/start")
async def start_mobile_pilot():
    _mobile_pilot_status["status"] = "running"
    return {"status": "started"}
