from typing import Any
from urllib.parse import urlparse

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


def _is_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _source_key(metadata: dict[str, Any]) -> str:
    url = metadata.get("url") or ""
    source = metadata.get("source") or ""
    if _is_url(url):
        return url.strip()
    if _is_url(source):
        return source.strip()
    return (
        metadata.get("doc_id")
        or metadata.get("chunk_id")
        or source.strip()
        or metadata.get("title")
        or "unknown"
    )


def _format_sources(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for result in results:
        metadata = result.get("metadata") or {}
        key = _source_key(metadata)
        source = metadata.get("source") or "unknown"
        url = metadata.get("url") or (source if _is_url(source) else "")
        score = result.get("similarity")
        chunk_id = metadata.get("chunk_id")

        if key not in grouped:
            grouped[key] = {
                "title": metadata.get("title") or "",
                "source": source,
                "url": url,
                "topic": metadata.get("topic") or "",
                "document_type": metadata.get("document_type") or "",
                "doc_id": metadata.get("doc_id") or "",
                "chunk_ids": [],
                "chunk_count": 0,
                "best_score": score,
                "reference_type": "web" if _is_url(url) else "rag",
            }

        reference = grouped[key]
        reference["chunk_count"] += 1
        if chunk_id:
            reference["chunk_ids"].append(chunk_id)
        if score is not None and (reference["best_score"] is None or score < reference["best_score"]):
            reference["best_score"] = score

    return sorted(
        grouped.values(),
        key=lambda item: (item["best_score"] is None, item["best_score"] or 0),
    )


class ChatService:
    def __init__(self, embeddings: OpenRouterEmbeddings | None = None):
        self.embeddings = embeddings or OpenRouterEmbeddings()
        self.retrieval = RetrievalService(self.embeddings)
        self.ingest = IngestService()
        self.llm = LLMService()
        self.memory = MemoryService()
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
        self.greeting_message = "Hi! Do you have any agriculture-related questions you'd like help with?"

    async def create_session(self, title: str | None = None, user_id: str | None = None) -> dict:
        session = await self.session_repo.create(title, user_id=user_id)
        await self.message_repo.create(session["_id"], "assistant", self.greeting_message)
        return session

    async def get_session(self, session_id: str) -> dict | None:
        return await self.session_repo.get(session_id)

    async def list_sessions(self, user_id: str) -> list[dict]:
        return await self.session_repo.list_for_user(user_id)

    async def rename_session(self, session_id: str, title: str) -> dict | None:
        return await self.session_repo.update(session_id, {"title": title.strip()})

    async def delete_session(self, session_id: str) -> bool:
        return await self.session_repo.delete(session_id)

    async def _touch_session_for_message(self, session_id: str, message: str) -> None:
        session = await self.session_repo.get(session_id)
        title = None
        if session and session.get("title") == "New Chat":
            title = message.strip().replace("\n", " ")[:60] or None
        await self.session_repo.touch(session_id, title=title)

    async def _search_context(self, session_id: str, message: str) -> list[dict[str, Any]]:
        global_results = await self.retrieval.search(message, top_k=5)
        session_results = await self.retrieval.search(message, top_k=5, where={"session_id": session_id})

        merged: dict[str, dict[str, Any]] = {}
        for result in [*session_results, *global_results]:
            metadata = result.get("metadata") or {}
            key = metadata.get("chunk_id") or metadata.get("doc_id") or result.get("content", "")[:80]
            if key not in merged or result.get("similarity", 1e9) < merged[key].get("similarity", 1e9):
                merged[key] = result

        ordered = sorted(merged.values(), key=lambda item: item.get("similarity") if item.get("similarity") is not None else 1e9)
        return ordered[:5]

    async def send_message(self, session_id: str, message: str) -> dict:
        await self.message_repo.create(session_id, "user", message)
        await self._touch_session_for_message(session_id, message)
        await self.memory.extract_and_store_context(session_id, message)

        session_memory = await self.memory.get_session_memory(session_id)
        if not is_farming_related(message, session_memory=session_memory):
            refusal = farming_refusal_message()
            await self.message_repo.create(session_id, "assistant", refusal)
            return {"message": refusal, "sources": [], "session_id": session_id}

        try:
            results = await self._search_context(session_id, message)
        except Exception:
            logger.exception("Retrieval failed; continuing without RAG context")
            results = []

        context_parts = []
        for result in results:
            context_parts.append(result["content"])

        context = "\n\n".join(context_parts) if context_parts else ""
        sources = _format_sources(results)
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
        await self._touch_session_for_message(session_id, message)
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
            results = await self._search_context(session_id, message)
        except Exception:
            logger.exception("Retrieval failed; continuing without RAG context")
            results = []

        context_parts: list[str] = []
        for result in results:
            context_parts.append(result["content"])

        context = "\n\n".join(context_parts) if context_parts else ""
        sources = _format_sources(results)
        chat_history = await self.memory.get_chat_history(session_id)

        yield {"type": "meta", "sources": sources, "session_id": session_id}

        full_response = ""
        async for token in self.llm.stream_generate_with_context(message, context, chat_history):
            full_response += token
            yield {"type": "token", "content": token}

        await self.message_repo.create(session_id, "assistant", full_response)
        yield {"type": "done"}

    async def close(self):
        await self.ingest.close()
        await self.embeddings.close()
        await self.llm.close()
