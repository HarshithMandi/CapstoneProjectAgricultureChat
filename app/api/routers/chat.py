import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse, SessionCreate, Session

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=Session)
async def create_session(request: SessionCreate):
    service = get_chat_service()
    session = await service.create_session(request.title)
    return session


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(session_id: str, request: ChatRequest):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await service.send_message(session_id, request.message)
    return ChatResponse(**result)


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(session_id: str, request: ChatRequest):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        async for event in service.stream_message(session_id, request.message):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )