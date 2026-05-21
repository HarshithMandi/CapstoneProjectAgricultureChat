from typing import Any
from app.db.repositories.session import SessionRepository
from app.db.repositories.message import MessageRepository


class MemoryService:
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()

    async def get_session_memory(self, session_id: str) -> dict[str, Any]:
        session = await self.session_repo.get(session_id)
        if not session:
            return {}
        return session.get("memory", {})

    async def update_memory(self, session_id: str, key: str, value: Any) -> None:
        await self.session_repo.update_memory(session_id, key, value)

    async def extract_and_store_context(
        self,
        session_id: str,
        message: str,
    ) -> None:
        message_lower = message.lower()

        crops = ["rice", "wheat", "corn", "maize", "cotton", "sugarcane", "potato", "tomato"]
        locations = ["india", "usa", "china", "brazil", "australia"]

        for crop in crops:
            if crop in message_lower:
                await self.update_memory(session_id, "crop", crop)
                break

        for location in locations:
            if location in message_lower:
                await self.update_memory(session_id, "location", location)
                break

    async def get_chat_history(self, session_id: str) -> list[dict]:
        messages = await self.message_repo.get_by_session(session_id)
        return [{"role": m["role"], "content": m["content"]} for m in messages]