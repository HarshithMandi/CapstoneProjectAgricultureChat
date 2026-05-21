from langchain_core.documents import Document
from app.langchain_components.embeddings import OpenRouterEmbeddings
from app.langchain_components.vectorstore import aadd_documents


class EmbeddingService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.embeddings = embeddings or OpenRouterEmbeddings()

    async def embed_and_store(self, chunks: list[Document]) -> list[str]:
        return await aadd_documents(chunks, self.embeddings)

    async def close(self):
        await self.embeddings.close()