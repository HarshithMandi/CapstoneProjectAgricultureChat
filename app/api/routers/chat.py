import json

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from app.api.deps import get_chat_service, get_current_user
from app.schemas.chat import ChatRequest, ChatResponse, SessionCreate, Session, SessionUpdate
import logging

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/sessions", response_model=Session)
async def create_session(request: SessionCreate, current_user: dict = Depends(get_current_user)):
    service = get_chat_service()
    session = await service.create_session(request.title, user_id=current_user["_id"])
    return session


@router.get("/sessions", response_model=list[Session])
async def list_sessions(current_user: dict = Depends(get_current_user)):
    service = get_chat_service()
    return await service.list_sessions(current_user["_id"])


@router.get("/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to access this session")
    return session


@router.patch("/sessions/{session_id}", response_model=Session)
async def rename_session(
    session_id: str,
    request: SessionUpdate,
    current_user: dict = Depends(get_current_user),
):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to modify this session")

    renamed = await service.rename_session(session_id, request.title)
    if not renamed:
        raise HTTPException(status_code=404, detail="Session not found")
    return renamed


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this session")

    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to access this session")

    result = await service.send_message(session_id, request.message)
    return ChatResponse(**result)


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to access this session")

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


@router.post("/sessions/{session_id}/attachments/pdf")
async def upload_pdf_attachment(
    session_id: str,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
):
    service = get_chat_service()
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.get("role") != "admin" and session.get("user_id") != current_user["_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to access this session")

    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf") and (file.content_type or "").lower() != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    ingest = service.ingest
    try:
        result = await ingest.ingest_pdf_bytes(
            pdf_bytes=pdf_bytes,
            filename=filename,
            topic=(session.get("memory") or {}).get("topic") or "general",
            session_id=session_id,
            title=title,
        )
    except Exception as e:
        logger.exception("PDF upload/ingest failed for session %s file %s", session_id, filename)
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {str(e)}")

    return {
        **result,
        "session_id": session_id,
    }
