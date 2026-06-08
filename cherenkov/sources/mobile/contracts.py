from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class MobileApp:
    app_id: str
    name: str
    platform: Literal["android", "ios"]
    version: str
    package_path: str


@dataclass
class MobileScreen:
    screen_id: str
    name: str
    elements: list[dict]
    navigation: list[str]


@dataclass
class MobileFlow:
    flow_id: str
    name: str
    screens: list[str]
    actions: list[dict]
