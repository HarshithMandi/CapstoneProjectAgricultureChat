from typing import Any

import logging
from app.services.ingest_service import IngestService
from app.services.retrieval_service import RetrievalService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.db.repositories.session import SessionRepository
from app.db.repositories.message import MessageRepository
from app.langchain_components.embeddings import OpenRouterEmbeddings
from app.utils.text import is_farming_related, farming_refusal_message

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.embeddings = embeddings or OpenRouterEmbeddings()
        self.retrieval = RetrievalService(self.embeddings)
        self.llm = LLMService()
        self.memory = MemoryService()
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()

    async def create_session(self, title: str | None = None) -> dict:
        session = await self.session_repo.create(title)
        return session

    async def get_session(self, session_id: str) -> dict | None:
        return await self.session_repo.get(session_id)

    async def send_message(self, session_id: str, message: str) -> dict:
        await self.message_repo.create(session_id, "user", message)
        await self.memory.extract_and_store_context(session_id, message)

        session_memory = await self.memory.get_session_memory(session_id)
        if not is_farming_related(message, session_memory=session_memory):
            refusal = farming_refusal_message()
            await self.message_repo.create(session_id, "assistant", refusal)
            return {"message": refusal, "sources": [], "session_id": session_id}

        try:
            results = await self.retrieval.search(message, top_k=5)
        except Exception:
            logger.exception("Retrieval failed; continuing without RAG context")
            results = []

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

    async def stream_message(self, session_id: str, message: str):
        await self.message_repo.create(session_id, "user", message)
        await self.memory.extract_and_store_context(session_id, message)

        session_memory = await self.memory.get_session_memory(session_id)
        if not is_farming_related(message, session_memory=session_memory):
            refusal = farming_refusal_message()
            yield {"type": "meta", "sources": [], "session_id": session_id}
            yield {"type": "token", "content": refusal}
            await self.message_repo.create(session_id, "assistant", refusal)
            yield {"type": "done"}
            return

        try:
            results = await self.retrieval.search(message, top_k=5)
        except Exception:
            logger.exception("Retrieval failed; continuing without RAG context")
            results = []

        context_parts: list[str] = []
        sources: list[dict[str, Any]] = []
        for result in results:
            context_parts.append(result["content"])
            sources.append(
                {
                    "source": result["metadata"].get("source", "unknown"),
                    "similarity": result["similarity"],
                }
            )

        context = "\n\n".join(context_parts) if context_parts else ""
        chat_history = await self.memory.get_chat_history(session_id)

        yield {"type": "meta", "sources": sources, "session_id": session_id}

        full_response = ""
        async for token in self.llm.stream_generate_with_context(message, context, chat_history):
            full_response += token
            yield {"type": "token", "content": token}

        await self.message_repo.create(session_id, "assistant", full_response)
        yield {"type": "done"}

    async def close(self):
        await self.embeddings.close()
        await self.llm.close()