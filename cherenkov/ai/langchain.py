from __future__ import annotations

from typing import Any, Optional, Type
from pydantic import BaseModel, Field

try:
    from langchain_core.tools import BaseTool
except ImportError:

    class BaseTool:  # type: ignore
        pass


from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.ports.memory import ConversationMemory
from cherenkov.substrate.router import SubstrateRouter


class CherenkovToolInput(BaseModel):
    query: str = Field(description="The QA or testing query to run through CHERENKOV.")


class CherenkovTool(BaseTool):
    """LangChain tool exposing CHERENKOV QA capabilities."""

    name: str = "cherenkov_qa"
    description: str = "Use CHERENKOV to run API conformance tests, visual QA, performance scans, or accessibility checks against a target."
    args_schema: Type[BaseModel] = CherenkovToolInput

    _agent: Any = None
    _session_id: str = "langchain_session"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        # Initialize internal agent if we have the package installed
        memory = ConversationMemory()  # type: ignore
        router = SubstrateRouter()
        self._agent = QAChatAgent(memory=memory, substrate_router=router)

    def _run(self, query: str, run_manager: Optional[Any] = None) -> str:
        """Run the CHERENKOV query synchronously."""
        msg = self._agent.chat(self._session_id, query)
        return msg.content

    async def _arun(self, query: str, run_manager: Optional[Any] = None) -> str:
        """Run the CHERENKOV query asynchronously."""
        # Simple async wrapper around sync chat for the tool
        return self._run(query, run_manager)
