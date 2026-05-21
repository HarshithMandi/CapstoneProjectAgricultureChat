from typing import Any
from app.langchain_components.embeddings import OpenRouterEmbeddings
from app.langchain_components.vectorstore import get_retriever
from app.db.chroma import get_chroma_collection


class RetrieverService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.embeddings = embeddings or OpenRouterEmbeddings()
        self._retriever = None

    @property
    def retriever(self):
        if self._retriever is None:
            self._retriever = get_retriever(self.embeddings)
        return self._retriever

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        results = []
        docs_with_scores = await self._asearch(query, top_k)
        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": float(score),
            })
        return results

    async def _asearch(self, query: str, top_k: int):
        from app.langchain_components.vectorstore import asimilarity_search
        return await asimilarity_search(query, top_k, self.embeddings)

    def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        collection = get_chroma_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "content": result["documents"][0],
                "metadata": result["metadatas"][0],
            }
        return None