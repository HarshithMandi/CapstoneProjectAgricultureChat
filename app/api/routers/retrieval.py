from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import require_admin
from app.schemas.retrieval import SearchRequest, ChunkResponse
from app.langchain_components.retrievers import RetrieverService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search")
async def search(request: SearchRequest, _admin: dict = Depends(require_admin)):
    retriever = RetrieverService()
    results = await retriever.search(request.query, request.top_k)
    return {"results": results}


@router.get("/chunk/{chunk_id}")
async def get_chunk(chunk_id: str, _admin: dict = Depends(require_admin)):
    retriever = RetrieverService()
    chunk = retriever.get_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk
