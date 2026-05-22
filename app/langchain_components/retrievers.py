from typing import Any
from urllib.parse import urlparse
from app.langchain_components.embeddings import OpenRouterEmbeddings
from app.langchain_components.vectorstore import get_retriever
from app.db.chroma import get_chroma_collection


def _source_key(metadata: dict[str, Any]) -> str:
    source = metadata.get("url") or metadata.get("source") or metadata.get("doc_id") or metadata.get("chunk_id") or "unknown"
    parsed = urlparse(str(source))
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    return str(source).strip().lower()


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
        candidate_k = max(top_k * 6, 20)
        # Prefer semantic overlap chunks by default (best general signal).
        docs_with_scores = await self._asearch(query, candidate_k, where={"chunk_type": "semantic", **(where or {})})
        selected = self._diversify_by_source(docs_with_scores, top_k)

        if len(selected) < top_k:
            # Fallback to any chunk type to fill remaining slots.
            extra = await self._asearch(query, candidate_k, where=where)
            seen_ids = {d.metadata.get("chunk_id") for d, _s in selected}
            combined = list(selected)
            for doc, score in extra:
                cid = doc.metadata.get("chunk_id")
                if cid and cid in seen_ids:
                    continue
                combined.append((doc, score))
                if cid:
                    seen_ids.add(cid)
                if len(combined) >= candidate_k:
                    break
            selected = self._diversify_by_source(combined, top_k)

        for doc, score in selected:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": float(score),
            })
        return results

    def _diversify_by_source(self, docs_with_scores: list[tuple[Any, float]], top_k: int) -> list[tuple[Any, float]]:
        if top_k <= 0:
            return []

        max_per_source = 1 if top_k <= 3 else 2
        selected: list[tuple[Any, float]] = []
        source_counts: dict[str, int] = {}
        seen_chunk_ids: set[str] = set()

        for doc, score in docs_with_scores:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id and chunk_id in seen_chunk_ids:
                continue

            key = _source_key(doc.metadata)
            if source_counts.get(key, 0) >= max_per_source:
                continue

            selected.append((doc, score))
            source_counts[key] = source_counts.get(key, 0) + 1
            if chunk_id:
                seen_chunk_ids.add(chunk_id)
            if len(selected) >= top_k:
                return selected

        for doc, score in docs_with_scores:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id and chunk_id in seen_chunk_ids:
                continue
            selected.append((doc, score))
            if chunk_id:
                seen_chunk_ids.add(chunk_id)
            if len(selected) >= top_k:
                return selected

        return selected

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
