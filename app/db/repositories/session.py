from datetime import datetime
from typing import Any
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from app.db.mongo import get_sessions_collection, get_messages_collection


class SessionRepository:
    def __init__(self, collection: AsyncIOMotorCollection | None = None):
        self.collection = collection or get_sessions_collection()

    async def create(self, title: str | None = None, user_id: str | None = None) -> dict:
        session = {
            "title": title or "New Chat",
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "memory": {},
        }
        result = await self.collection.insert_one(session)
        return {
            "_id": str(result.inserted_id),
            "title": session["title"],
            "user_id": session["user_id"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "memory": session["memory"],
        }

    async def get(self, session_id: str) -> dict | None:
        session = await self.collection.find_one({"_id": ObjectId(session_id)})
        if session:
            session["_id"] = str(session["_id"])
            messages = await self.get_messages(session_id)
            session["messages"] = messages
        return session

    async def update(self, session_id: str, updates: dict[str, Any]) -> dict | None:
        updates["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": updates},
        )
        return await self.get(session_id)

    async def update_memory(self, session_id: str, key: str, value: Any) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {f"memory.{key}": value, "updated_at": datetime.utcnow()}},
        )

    async def get_messages(self, session_id: str) -> list[dict]:
        cursor = self.collection.database["messages"].find(
            {"session_id": session_id}
        ).sort("timestamp", 1)
        messages = await cursor.to_list(None)
        for msg in messages:
            msg["_id"] = str(msg["_id"])
        return messages
