from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from app.db.mongo import get_messages_collection


class MessageRepository:
    def __init__(self, collection: AsyncIOMotorCollection | None = None):
        self.collection = collection or get_messages_collection()

    async def create(self, session_id: str, role: str, content: str) -> dict:
        message = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
        }
        result = await self.collection.insert_one(message)
        return {"_id": str(result.inserted_id), **message}

    async def get_by_session(self, session_id: str) -> list[dict]:
        cursor = self.collection.find({"session_id": session_id}).sort("timestamp", 1)
        messages = await cursor.to_list(None)
        for msg in messages:
            msg["_id"] = str(msg["_id"])
        return messages

    async def delete_by_session(self, session_id: str) -> None:
        await self.collection.delete_many({"session_id": session_id})