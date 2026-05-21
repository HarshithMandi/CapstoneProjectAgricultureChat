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
        # Prefer semantic overlap chunks by default (best general signal).
        docs_with_scores = await self._asearch(query, top_k, where={"chunk_type": "semantic"})
        if len(docs_with_scores) < top_k:
            # Fallback to any chunk type to fill remaining slots.
            extra = await self._asearch(query, top_k)
            seen_ids = {d.metadata.get("chunk_id") for d, _s in docs_with_scores}
            for doc, score in extra:
                cid = doc.metadata.get("chunk_id")
                if cid and cid in seen_ids:
                    continue
                docs_with_scores.append((doc, score))
                if len(docs_with_scores) >= top_k:
                    break

        for doc, score in docs_with_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": float(score),
            })
        return results

    async def _asearch(self, query: str, top_k: int, where: dict | None = None):
        from app.langchain_components.vectorstore import asimilarity_search
        return await asimilarity_search(query, top_k, self.embeddings, where=where)

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