from fastapi import APIRouter, HTTPException
from app.schemas.retrieval import SearchRequest, ChunkResponse
from app.langchain_components.retrievers import RetrieverService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search")
async def search(request: SearchRequest):
    retriever = RetrieverService()
    results = await retriever.search(request.query, request.top_k)
    return {"results": results}


@router.get("/chunk/{chunk_id}")
async def get_chunk(chunk_id: str):
    retriever = RetrieverService()
    chunk = retriever.get_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return chunk