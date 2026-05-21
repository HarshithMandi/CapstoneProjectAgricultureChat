from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.core.exceptions import SessionNotFoundError

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "agri-rag-chatbot",
    }