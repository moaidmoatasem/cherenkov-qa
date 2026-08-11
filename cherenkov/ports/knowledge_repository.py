from __future__ import annotations

from typing import Protocol

from cherenkov.core.knowledge_result import KnowledgeResult


class KnowledgeRepository(Protocol):
    """Placeholder docstring.

<description>"""
    def store(self, result: KnowledgeResult) -> None: ...
        """Placeholder docstring.

:param result: <description>
:return: <description>"""

    def get(self, key: str) -> KnowledgeResult | None: ...
        """Placeholder docstring.

:param key: <description>
:return: <description>"""

    def search(self, query: str, limit: int = 10) -> list[KnowledgeResult]: ...
        """Placeholder docstring.

:param query: <description>
:param limit: <description>
:return: <description>"""

    def delete(self, key: str) -> bool: ...
        """Placeholder docstring.

:param key: <description>
:return: <description>"""

    def list_by_kind(self, kind: str, limit: int = 50) -> list[KnowledgeResult]: ...
        """Placeholder docstring.

:param kind: <description>
:param limit: <description>
:return: <description>"""
