from __future__ import annotations
from typing import Any
from cherenkov.reflector.store import ReflectorStore

class MobileReflectorExtensions:
    def __init__(self, store: ReflectorStore):
        self.store = store

    def record_mobile_session(self, app_id: str, session_data: dict):
        entry = {
            "type": "mobile_session",
            "app_id": app_id,
            "data": session_data,
        }
        self.store.append(entry)

    def record_tap(self, element_id: str, screenshot_path: str | None = None):
        entry = {
            "type": "tap",
            "element_id": element_id,
            "screenshot": screenshot_path,
        }
        self.store.append(entry)

    def record_screenshot(self, screen_name: str, screenshot_path: str, ocr_text: str | None = None):
        entry = {
            "type": "screenshot",
            "screen_name": screen_name,
            "screenshot": screenshot_path,
            "ocr_text": ocr_text,
        }
        self.store.append(entry)

    def get_mobile_sessions(self, app_id: str | None = None) -> list[dict]:
        entries = self.store.query(type="mobile_session")
        if app_id:
            entries = [e for e in entries if e.get("app_id") == app_id]
        return entries
