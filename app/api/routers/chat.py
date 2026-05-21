from fastapi import APIRouter, HTTPException
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