from app.langchain_components.retrievers import RetrieverService
from app.langchain_components.embeddings import OpenRouterEmbeddings


class RetrievalService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.retriever = RetrieverService(embeddings)

    async def search(self, query: str, top_k: int = 5):
        return await self.retriever.search(query, top_k)

    def get_chunk_by_id(self, chunk_id: str):
        return self.retriever.get_chunk_by_id(chunk_id)