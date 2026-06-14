from __future__ import annotations

from typing import Protocol, Any


class VLMProvider(Protocol):
    def describe_image(self, image_path: str, prompt: str = "") -> str: ...

    def compare_images(
        self, baseline_path: str, actual_path: str
    ) -> dict[str, Any]: ...

    def health(self) -> bool: ...
