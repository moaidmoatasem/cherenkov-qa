from __future__ import annotations

from pathlib import Path

from cherenkov.knowledge.domain.models import KnowledgeItem
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository


class AgentMemoryRAGBridge:
    def __init__(
        self, repository: KnowledgeMeshRepository, memory_dir: str = "agent_memory"
    ):
        self.repository = repository
        self.memory_dir = Path(memory_dir)

    def sync_agent_memory(self) -> int:
        if not self.memory_dir.exists():
            return 0
        count = 0
        for md_file in self.memory_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            item = KnowledgeItem(
                item_id=f"agent_memory_{md_file.stem}",
                source="agent_memory",
                data={"filename": md_file.name, "content": content},
                metadata={"path": str(md_file), "size": len(content)},
            )
            self.repository.store(item)
            count += 1
        return count
