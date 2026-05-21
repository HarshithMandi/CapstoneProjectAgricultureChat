from typing import Any
from app.services.ingest_service import IngestService
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.db.repositories.session import SessionRepository
from app.db.repositories.message import MessageRepository
from app.langchain_components.embeddings import OpenRouterEmbeddings


class ChatService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.retrieval = RetrievalService(embeddings)
        self.llm = LLMService()
        self.memory = MemoryService()
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        self.embeddings = embeddings

    async def create_session(self, title: str | None = None) -> dict:
        session = await self.session_repo.create(title)
        return session

    async def get_session(self, session_id: str) -> dict | None:
        return await self.session_repo.get(session_id)

    async def send_message(self, session_id: str, message: str) -> dict:
        await self.message_repo.create(session_id, "user", message)
        await self.memory.extract_and_store_context(session_id, message)

        results = await self.retrieval.search(message, top_k=5)

        context_parts = []
        sources = []
        for result in results:
            context_parts.append(result["content"])
            sources.append({
                "source": result["metadata"].get("source", "unknown"),
                "similarity": result["similarity"],
            })

        context = "\n\n".join(context_parts) if context_parts else ""
        chat_history = await self.memory.get_chat_history(session_id)

        response = await self.llm.generate_with_context(message, context, chat_history)

        await self.message_repo.create(session_id, "assistant", response)

        return {
            "message": response,
            "sources": sources,
            "session_id": session_id,
        }

    async def close(self):
        if self.embeddings:
            await self.embeddings.close()
        await self.llm.close()