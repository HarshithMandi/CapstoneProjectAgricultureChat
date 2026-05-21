from pydantic import BaseModel, Field


class URLIngestRequest(BaseModel):
    url: str = Field(..., description="URL to ingest")
    title: str | None = None
    topic: str | None = None


class URLsIngestRequest(BaseModel):
    urls: list[str] = Field(..., description="List of URLs to ingest")
    topic: str | None = None


class TextIngestRequest(BaseModel):
    text: str = Field(..., description="Raw text to ingest")
    title: str | None = None
    source: str | None = None
    topic: str | None = None
    document_type: str | None = None


class IngestResponse(BaseModel):
    document_ids: list[str]
    chunks_created: int
    status: str = "success"