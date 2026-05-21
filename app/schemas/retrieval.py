from typing import Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class ChunkResponse(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any]
    similarity: float | None = None