"""
cherenkov/core/devices.py — Hardware and environment capability detection.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceClass(str, Enum):
    """Device class classification enumeration (desktop, server, mobile, etc.)."""

    DESKTOP = "desktop"
    TABLET = "tablet"
    MOBILE = "mobile"
    SERVER = "server"
    UNKNOWN = "unknown"


class VLMTier(str, Enum):
    """VLM execution tier enumeration (none, local, cloud)."""

    NONE = "none"
    LOCAL = "local"
    CLOUD = "cloud"


class DeviceInfo:
    """Hardware and execution environment capability detector."""

    device_class: DeviceClass
    vlm_tier: VLMTier
    has_gpu: bool
    has_docker: bool
    has_camera: bool
    has_mic: bool
    os_name: str
    os_version: str
    cpu_count: int
    memory_gb: float

    def __init__(self):
        """Initialize DeviceInfo by probing system capabilities."""
        self.device_class = self._detect_device_class()
        self.vlm_tier = self._detect_vlm_tier()
        self.has_gpu = self._check_gpu()
        self.has_docker = self._check_docker()
        self.has_camera = False
        self.has_mic = False
        self.os_name = platform.system()
        self.os_version = platform.version()
        self.cpu_count = os.cpu_count() or 1
        self.memory_gb = self._get_memory_gb()

    @staticmethod
    def _detect_device_class() -> DeviceClass:
        system = platform.system().lower()
        if "linux" in system:
            return DeviceClass.SERVER
        if "windows" in system:
            return DeviceClass.DESKTOP
        if "darwin" in system:
            return DeviceClass.DESKTOP
        return DeviceClass.UNKNOWN

    @staticmethod
    def _detect_vlm_tier() -> VLMTier:
        provider = os.getenv("CHERENKOV_TIER_VISION_PROVIDER", "ollama").lower()
        if provider == "ollama":
            return VLMTier.LOCAL
        if provider in ("openai", "anthropic"):
            return VLMTier.CLOUD
        return VLMTier.NONE

    @staticmethod
    def _check_gpu() -> bool:
        nvidia_smi = os.getenv("CHERENKOV_SKIP_GPU_CHECK", "")
        if nvidia_smi:
            return False
        try:
            result = subprocess.run(
                ["nvidia-smi"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _check_docker() -> bool:
        try:
            result = subprocess.run(
                ["docker", "info"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _get_memory_gb() -> float:
        try:
            import psutil

            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            return 0.0

    def to_dict(self) -> dict:
        """Convert device information fields into a dictionary.

        Returns:
            dict: Dictionary representation of detected system resources and capabilities.
        """
        return {
            "device_class": self.device_class.value,
            "vlm_tier": self.vlm_tier.value,
            "has_gpu": self.has_gpu,
            "has_docker": self.has_docker,
            "has_camera": self.has_camera,
            "has_mic": self.has_mic,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "cpu_count": self.cpu_count,
            "memory_gb": round(self.memory_gb, 1),
        }

