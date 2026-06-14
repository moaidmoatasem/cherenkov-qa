# Vision 16: Chat Agent (Tool-Calling, Persona Registry)

**Date:** 2026-06-08
**Status:** Active
**Related EPIC:** #283 (Phase 4)

---

## Overview

The Chat Agent is CHERENKOV's conversational interface — a tool-calling agent that queries the Second Brain, explains divergences, and runs tests. It enables:

- **Natural language queries**: "Why was this test rejected?" → agent calls `explain_divergence`
- **Tool orchestration**: Agent selects and calls CHERENKOV tools (query_verdicts, query_idioms, run_test)
- **Persona composition**: System prompt includes project context, idioms, Truth Model
- **Streaming responses**: SSE endpoint for real-time token streaming
- **MCP integration**: External MCP clients can query knowledge

---

## Architecture

```
┌─────────────────────────────────────┐
│  QAChatAgent                        │
│  - chat(session_id, message)        │
│  - Tool orchestration               │
│  - Context window management        │
└──────────────┬──────────────────────┘
               │
               ├─→ ConversationMemory (session history)
               ├─→ PersonaRegistry (system prompt composition)
               ├─→ SubstrateRouter (LLM calls)
               └─→ CHERENKOV tools (query_verdicts, explain_divergence, run_test)
```

---

## Domain Models

```python
# cherenkov/chat/domain/models.py
from dataclasses import dataclass, field
from typing import Literal
from datetime import datetime
import uuid

@dataclass
class Message:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant", "system", "tool"] = "user"
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
```

---

## Conversation Memory

### Port Interface

```python
# cherenkov/chat/ports/memory.py
from typing import Protocol
from cherenkov.chat.domain.models import Session, Message

class ConversationMemory(Protocol):
    def create_session(self) -> str: ...
    def add_message(self, session_id: str, message: Message) -> None: ...
    def get_messages(self, session_id: str, limit: int = 20) -> list[Message]: ...
    def close_session(self, session_id: str) -> None: ...
```

### SQLite Adapter

```python
# cherenkov/chat/adapters/sqlite_memory.py
import sqlite3
import json
from cherenkov.chat.domain.models import Session, Message

class SQLiteConversationMemory:
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()
        conn.close()

    def create_session(self) -> str:
        import uuid
        session_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sessions (session_id, metadata) VALUES (?, ?)",
            (session_id, json.dumps({}))
        )
        conn.commit()
        conn.close()

        return session_id

    def add_message(self, session_id: str, message: Message) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (message_id, session_id, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
            (message.message_id, session_id, message.role, message.content, json.dumps(message.metadata))
        )
        conn.commit()
        conn.close()

    def get_messages(self, session_id: str, limit: int = 20) -> list[Message]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT message_id, role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            messages.append(Message(
                message_id=row[0],
                role=row[1],
                content=row[2],
                timestamp=row[3],
                metadata=json.loads(row[4]) if row[4] else {}
            ))

        return list(reversed(messages))  # Oldest first

    def close_session(self, session_id: str) -> None:
        # Persist to KnowledgeRepository
        messages = self.get_messages(session_id, limit=1000)

        from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
        from cherenkov.knowledge.domain.models import KnowledgeItem

        repo = SQLiteKnowledgeRepository()
        item = KnowledgeItem(
            item_id=f"chat_session_{session_id}",
            source="chat",
            data={
                "session_id": session_id,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat()
                    }
                    for m in messages
                ]
            },
            metadata={"message_count": len(messages)}
        )
        repo.store(item)
```

---

## Persona Registry

```python
# cherenkov/chat/domain/persona.py
from dataclasses import dataclass
from typing import Any

@dataclass
class Persona:
    name: str
    system_prompt: str
    context: dict[str, Any]

class PersonaRegistry:
    def __init__(self):
        self.personas: dict[str, Persona] = {}
        self._register_default_personas()

    def _register_default_personas(self):
        self.register(Persona(
            name="qa_assistant",
            system_prompt="""You are CHERENKOV QA Assistant, an expert in API conformance testing.

Your role:
- Help users understand test failures and divergences
- Explain why tests were rejected or approved
- Suggest improvements to test assertions
- Answer questions about the CHERENKOV pipeline

You have access to tools:
- query_verdicts: Query test verdicts
- query_idioms: Query learned patterns
- explain_divergence: Explain a divergence
- run_test: Run a test (user-initiated only)

Guiding principles:
- Be concise and direct
- Cite specific evidence from verdicts and idioms
- Never auto-edit test code (D7 invariant)
- Suggest-only healing (never auto-apply)
""",
            context={}
        ))

    def register(self, persona: Persona) -> None:
        self.personas[persona.name] = persona

    def get(self, name: str) -> Persona | None:
        return self.personas.get(name)

    def compose_prompt(self, persona_name: str, project_context: dict, idioms: list, tools: list) -> str:
        persona = self.get(persona_name)
        if not persona:
            return ""

        prompt = persona.system_prompt

        if project_context:
            prompt += f"\n\nProject Context:\n{project_context}"

        if idioms:
            prompt += "\n\nLearned Patterns (top idioms):\n"
            for idiom in idioms[:5]:
                prompt += f"- {idiom}\n"

        if tools:
            prompt += "\n\nAvailable Tools:\n"
            for tool in tools:
                prompt += f"- {tool['name']}: {tool['description']}\n"

        return prompt
```

---

## QAChatAgent

```python
# cherenkov/chat/agents/qa_agent.py
from typing import Generator
from cherenkov.chat.domain.models import Message
from cherenkov.chat.ports.memory import ConversationMemory
from cherenkov.chat.domain.persona import PersonaRegistry
from cherenkov.substrate.router import SubstrateRouter

class QAChatAgent:
    def __init__(
        self,
        memory: ConversationMemory,
        persona_registry: PersonaRegistry,
        router: SubstrateRouter,
        tools: list[dict],
        max_tool_calls: int = 5,
        token_budget: int = 4096
    ):
        self.memory = memory
        self.persona_registry = persona_registry
        self.router = router
        self.tools = tools
        self.max_tool_calls = max_tool_calls
        self.token_budget = token_budget

    def chat(self, session_id: str, user_message: str) -> Generator[str, None, None]:
        # Add user message
        user_msg = Message(role="user", content=user_message)
        self.memory.add_message(session_id, user_msg)

        # Get conversation history
        messages = self.memory.get_messages(session_id, limit=20)

        # Compose system prompt
        from cherenkov.knowledge.graph_rag import GraphRAG
        from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

        repo = SQLiteKnowledgeRepository()
        rag = GraphRAG(repo)
        idioms = rag.query("idioms", limit=5)

        system_prompt = self.persona_registry.compose_prompt(
            persona_name="qa_assistant",
            project_context={},
            idioms=[i.data for i in idioms],
            tools=self.tools
        )

        # Build message list
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Call LLM
        tool_call_count = 0
        while tool_call_count < self.max_tool_calls:
            response = self.router.chat(llm_messages)

            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    tool_result = self._execute_tool(tool_call)

                    llm_messages.append({
                        "role": "tool",
                        "content": str(tool_result),
                        "tool_call_id": tool_call["id"]
                    })

                    tool_call_count += 1

                continue
            else:
                assistant_msg = Message(role="assistant", content=response["content"])
                self.memory.add_message(session_id, assistant_msg)

                for token in response["tokens"]:
                    yield token

                break

    def _execute_tool(self, tool_call: dict) -> dict:
        tool_name = tool_call["function"]["name"]
        tool_args = tool_call["function"]["arguments"]

        tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = tool["execute"](**tool_args)
            return result
        except Exception as e:
            return {"error": str(e)}
```

---

## CHERENKOV Tools

```python
# cherenkov/chat/tools/registry.py
from typing import Any

def get_tools() -> list[dict]:
    return [
        {
            "name": "query_verdicts",
            "description": "Query test verdicts by endpoint or pattern",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["endpoint"]
            },
            "execute": query_verdicts
        },
        {
            "name": "query_idioms",
            "description": "Query learned patterns (idioms)",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["pattern"]
            },
            "execute": query_idioms
        },
        {
            "name": "explain_divergence",
            "description": "Explain a divergence using knowledge graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "method": {"type": "string"}
                },
                "required": ["endpoint", "method"]
            },
            "execute": explain_divergence
        },
        {
            "name": "run_test",
            "description": "Run a test (user-initiated only)",
            "parameters": {
                "type": "object",
                "properties": {
                    "spec_path": {"type": "string"},
                    "endpoint": {"type": "string"}
                },
                "required": ["spec_path", "endpoint"]
            },
            "execute": run_test
        }
    ]

def query_verdicts(endpoint: str, limit: int = 10) -> dict:
    from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
    from cherenkov.knowledge.domain.models import KnowledgeQuery

    repo = SQLiteKnowledgeRepository()
    query = KnowledgeQuery(query=endpoint, source="verdicts", limit=limit)
    result = repo.query(query)

    return result.to_dict()

def query_idioms(pattern: str, limit: int = 10) -> dict:
    from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
    from cherenkov.knowledge.domain.models import KnowledgeQuery

    repo = SQLiteKnowledgeRepository()
    query = KnowledgeQuery(query=pattern, source="idioms", limit=limit)
    result = repo.query(query)

    return result.to_dict()

def explain_divergence(endpoint: str, method: str) -> dict:
    from cherenkov.knowledge.graph_rag import GraphRAG
    from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

    repo = SQLiteKnowledgeRepository()
    rag = GraphRAG(repo)
    result = rag.explain_divergence(endpoint, method)

    return result.to_dict()

def run_test(spec_path: str, endpoint: str) -> dict:
    from cherenkov.core.orchestrator import OrchestrationEngine

    engine = OrchestrationEngine()
    result = engine.run_pipeline(spec_path, endpoints=[endpoint])

    return {"status": "completed", "result": result}
```

---

## SSE Streaming

```python
# cherenkov/chat/api/streaming.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.get("/api/v1/chat/sessions/{session_id}/stream")
async def stream_chat(session_id: str, message: str):
    async def event_generator():
        from cherenkov.chat.agents.qa_agent import QAChatAgent
        from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
        from cherenkov.chat.domain.persona import PersonaRegistry
        from cherenkov.substrate.router import SubstrateRouter
        from cherenkov.chat.tools.registry import get_tools

        memory = SQLiteConversationMemory()
        persona_registry = PersonaRegistry()
        router = SubstrateRouter()
        tools = get_tools()

        agent = QAChatAgent(
            memory=memory,
            persona_registry=persona_registry,
            router=router,
            tools=tools
        )

        for token in agent.chat(session_id, message):
            event = {"event": "token", "data": {"token": token}}
            yield f"data: {json.dumps(event)}\n\n"

        event = {"event": "complete", "data": {}}
        yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## ChatPanel React Component

```tsx
// cherenkov/web/ui/src/components/ChatPanel.tsx
import React, { useState, useEffect, useRef } from 'react';

interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
}

export function ChatPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/v1/chat/sessions', { method: 'POST' })
      .then(r => r.json())
      .then(data => setSessionId(data.session_id));
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    fetch(`/api/v1/chat/sessions/${sessionId}/messages`)
      .then(r => r.json())
      .then(data => setMessages(data.messages));
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;

    const userMessage: Message = {
      message_id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsStreaming(true);

    const eventSource = new EventSource(
      `/api/v1/chat/sessions/${sessionId}/stream?message=${encodeURIComponent(input)}`
    );

    let assistantContent = '';

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event === 'token') {
        assistantContent += data.data.token;

        setMessages(msgs => {
          const lastMsg = msgs[msgs.length - 1];
          if (lastMsg?.role === 'assistant') {
            return [...msgs.slice(0, -1), { ...lastMsg, content: assistantContent }];
          } else {
            return [...msgs, {
              message_id: Date.now().toString(),
              role: 'assistant',
              content: assistantContent,
              timestamp: new Date().toISOString()
            }];
          }
        });
      } else if (data.event === 'tool_call') {
        setMessages(msgs => [...msgs, {
          message_id: Date.now().toString(),
          role: 'tool',
          content: `🔧 Calling ${data.data.name}(${JSON.stringify(data.data.args)})`,
          timestamp: new Date().toISOString()
        }]);
      } else if (data.event === 'tool_result') {
        setMessages(msgs => [...msgs, {
          message_id: Date.now().toString(),
          role: 'tool',
          content: `✅ Result: ${JSON.stringify(data.data.output)}`,
          timestamp: new Date().toISOString()
        }]);
      } else if (data.event === 'complete') {
        setIsStreaming(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
    };
  };

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.map(msg => (
          <div key={msg.message_id} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role}</div>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Ask a question..."
          disabled={isStreaming}
        />
        <button onClick={sendMessage} disabled={isStreaming || !input.trim()}>
          {isStreaming ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
```

---

## MCP Integration

```python
# cherenkov/mcp/handlers.py (extend)
from cherenkov.mcp.protocol import MCPHandler, MCPRequest, MCPResponse
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery

class QueryVerdictsHandler(MCPHandler):
    def handle(self, request: MCPRequest) -> MCPResponse:
        endpoint = request.params.get("endpoint")
        limit = request.params.get("limit", 10)

        repo = SQLiteKnowledgeRepository()
        query = KnowledgeQuery(query=endpoint, source="verdicts", limit=limit)
        result = repo.query(query)

        return MCPResponse(result=result.to_dict())

def register_knowledge_handlers(server):
    server.register_handler("query_verdicts", QueryVerdictsHandler())
    # ... other handlers
```

---

## Testing

```python
# tests/unit/test_chat_agent.py
from cherenkov.chat.agents.qa_agent import QAChatAgent
from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
from cherenkov.chat.domain.persona import PersonaRegistry
from cherenkov.substrate.router import SubstrateRouter
from cherenkov.chat.tools.registry import get_tools

def test_chat_agent_responds():
    memory = SQLiteConversationMemory(":memory:")
    persona_registry = PersonaRegistry()
    router = SubstrateRouter()
    tools = get_tools()

    agent = QAChatAgent(
        memory=memory,
        persona_registry=persona_registry,
        router=router,
        tools=tools
    )

    session_id = memory.create_session()
    response = list(agent.chat(session_id, "Hello"))

    assert len(response) > 0
```

---

## References

- EPIC #283 (Phase 4: Chat Agents)
- Issue #354-#361 (Chat agent tickets)
- `docs/PHASE_PLAN.md` (Phase 4 details)
- `cherenkov/chat/` (to be created)
