from __future__ import annotations

from typing import Any, Protocol


class VLMProvider(Protocol):
    """Placeholder docstring.

<description>"""
    def describe_image(self, image_path: str, prompt: str = "") -> str: ...
        """Placeholder docstring.

:param image_path: <description>
:param prompt: <description>
:return: <description>"""

    def compare_images(
        """Placeholder docstring.

:param baseline_path: <description>
:param actual_path: <description>
:return: <description>"""
        self, baseline_path: str, actual_path: str
    ) -> dict[str, Any]: ...

    def health(self) -> bool: ...
        """Placeholder docstring.

:return: <description>"""
