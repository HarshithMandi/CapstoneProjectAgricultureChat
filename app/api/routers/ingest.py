from fastapi import APIRouter, HTTPException
from app.api.deps import get_chat_service
from app.schemas.ingest import URLIngestRequest, URLsIngestRequest, TextIngestRequest, IngestResponse
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/url", response_model=IngestResponse)
async def ingest_url(request: URLIngestRequest):
    service = IngestService()
    try:
        result = await service.ingest_url(
            url=request.url,
            title=request.title,
            topic=request.topic,
        )
        return IngestResponse(**result)
    finally:
        await service.close()


@router.post("/urls", response_model=IngestResponse)
async def ingest_urls(request: URLsIngestRequest):
    service = IngestService()
    try:
        result = await service.ingest_urls(
            urls=request.urls,
            topic=request.topic,
        )
        return IngestResponse(**result)
    finally:
        await service.close()


@router.post("/text", response_model=IngestResponse)
async def ingest_text(request: TextIngestRequest):
    service = IngestService()
    try:
        result = await service.ingest_text(
            text=request.text,
            title=request.title,
            source=request.source,
            topic=request.topic,
            document_type=request.document_type,
        )
        return IngestResponse(**result)
    finally:
        await service.close()