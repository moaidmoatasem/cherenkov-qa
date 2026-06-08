from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from cherenkov.chat.adapters.sqlite_memory import SQLiteConversationMemory
from cherenkov.chat.agent import QAChatAgent

router = APIRouter()
_memory = SQLiteConversationMemory()
_agent = QAChatAgent(memory=_memory)


@router.post("/api/v1/chat/sessions")
async def create_session(persona_id: str = "qa_assistant"):
    session = _agent.create_session(persona_id)
    return {"session_id": session.session_id, "persona_id": session.persona_id}


@router.get("/api/v1/chat/sessions")
async def list_sessions(limit: int = 20):
    sessions = _memory.list_sessions(limit)
    return {"sessions": [s.to_dict() for s in sessions]}


@router.get("/api/v1/chat/sessions/{session_id}")
async def get_session(session_id: str):
    session = _agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.post("/api/v1/chat/sessions/{session_id}/messages")
async def send_message(session_id: str, body: dict):
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' field")
    session = _agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    assistant_msg = _agent.chat(session_id, content)
    return {"role": "assistant", "content": assistant_msg.content}


@router.get("/api/v1/chat/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 50):
    session = _agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = _memory.get_messages(session_id, limit)
    return {"messages": [m.to_dict() for m in messages]}


@router.post("/api/v1/chat/sessions/{session_id}/stream")
async def stream_chat(session_id: str, body: dict):
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' field")
    session = _agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        async for token in _agent.chat_stream(session_id, content):
            yield f"data: {json.dumps({'event': 'token', 'data': {'token': token}})}\n\n"
        yield f"data: {json.dumps({'event': 'complete', 'data': {}})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/v1/chat/sessions/{session_id}/close")
async def close_session(session_id: str):
    session = _agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    _memory.close_session(session_id)
    return {"status": "closed"}
