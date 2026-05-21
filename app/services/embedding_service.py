from langchain_core.documents import Document
from app.langchain_components.embeddings import OpenRouterEmbeddings
from app.langchain_components.vectorstore import add_documents
import asyncio


class EmbeddingService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.embeddings = embeddings or OpenRouterEmbeddings()

    async def embed_and_store(self, chunks: list[Document]) -> list[str]:
        ids = add_documents(chunks, self.embeddings)
        return ids

    async def close(self):
        await self.embeddings.close()