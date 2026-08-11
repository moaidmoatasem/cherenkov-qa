from __future__ import annotations

from typing import Protocol

from cherenkov.knowledge.domain.models import (
    KnowledgeItem,
    KnowledgeQuery,
    KnowledgeQueryResult,
)


class KnowledgeMeshRepository(Protocol):
    """Placeholder docstring.

<description>"""
    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult: ...
        """Placeholder docstring.

:param query: <description>
:return: <description>"""

    def store(self, item: KnowledgeItem) -> str: ...
        """Placeholder docstring.

:param item: <description>
:return: <description>"""

    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]: ...
        """Placeholder docstring.

:param pattern: <description>
:param limit: <description>
:return: <description>"""

    def get_by_id(self, item_id: str) -> KnowledgeQueryResult | None: ...
        """Placeholder docstring.

:param item_id: <description>
:return: <description>"""
