from __future__ import annotations

import asyncio
import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
from cherenkov.chat.agent import QAChatAgent
from cherenkov.chat.ports.memory import ConversationMemory
from cherenkov.chat.guard import get_guard

router = APIRouter()


class ChatMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Message content")


class CreateSessionRequest(BaseModel):
    persona_id: str = Field(default="qa_assistant", description="Persona to use for this session")


@lru_cache(maxsize=1)
def get_memory() -> ConversationMemory:
    return SQLiteConversationMemory()


def get_agent(memory: ConversationMemory = Depends(get_memory)) -> QAChatAgent:
    return QAChatAgent(memory=memory)


@router.post("/api/v1/chat/sessions")
async def create_session(
    body: CreateSessionRequest,
    agent: QAChatAgent = Depends(get_agent),
):
    session = await asyncio.to_thread(agent.create_session, body.persona_id)
    return {"session_id": session.session_id, "persona_id": session.persona_id}


@router.get("/api/v1/chat/sessions")
async def list_sessions(
    limit: int = 20,
    memory: ConversationMemory = Depends(get_memory),
):
    sessions = await asyncio.to_thread(memory.list_sessions, limit)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.get("/api/v1/chat/sessions/{session_id}")
async def get_session(
    session_id: str,
    agent: QAChatAgent = Depends(get_agent),
):
    session = await asyncio.to_thread(agent.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.post("/api/v1/chat/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: ChatMessageRequest,
    agent: QAChatAgent = Depends(get_agent),
):
    session = await asyncio.to_thread(agent.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    guard = get_guard()
    guard_result = guard.check_tool_call("chat_send_message", {"session_id": session_id, "content_length": len(body.content)})
    if not guard_result.allowed:
        raise HTTPException(status_code=403, detail=guard_result.reason)
    assistant_msg = await asyncio.to_thread(agent.chat, session_id, body.content)
    return {"role": "assistant", "content": assistant_msg.content}


@router.get("/api/v1/chat/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: int = 50,
    agent: QAChatAgent = Depends(get_agent),
    memory: ConversationMemory = Depends(get_memory),
):
    session = await asyncio.to_thread(agent.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await asyncio.to_thread(memory.get_messages, session_id, limit)
    return {"messages": [m.to_dict() for m in messages]}


@router.post("/api/v1/chat/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str,
    body: ChatMessageRequest,
    agent: QAChatAgent = Depends(get_agent),
):
    session = await asyncio.to_thread(agent.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    guard = get_guard()
    guard_result = guard.check_tool_call("chat_stream", {"session_id": session_id, "content_length": len(body.content)})
    if not guard_result.allowed:
        raise HTTPException(status_code=403, detail=guard_result.reason)

    async def event_stream():
        async for token in agent.chat_stream(session_id, body.content):
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        yield f"event: complete\ndata: {json.dumps({})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/v1/chat/sessions/{session_id}/close")
async def close_session(
    session_id: str,
    agent: QAChatAgent = Depends(get_agent),
    memory: ConversationMemory = Depends(get_memory),
):
    session = await asyncio.to_thread(agent.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await asyncio.to_thread(memory.close_session, session_id)
    return {"status": "closed"}
