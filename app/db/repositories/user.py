from datetime import datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongo import get_users_collection


class UserRepository:
    def __init__(self, collection: AsyncIOMotorCollection | None = None):
        self.collection = collection or get_users_collection()

    async def count(self) -> int:
        return await self.collection.count_documents({})

    async def create(
        self,
        email: str,
        password_hash: str,
        role: str = "user",
        full_name: str | None = None,
    ) -> dict:
        now = datetime.utcnow()
        user = {
            "email": email.lower(),
            "password_hash": password_hash,
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        result = await self.collection.insert_one(user)
        user["_id"] = str(result.inserted_id)
        return user

    async def get_by_email(self, email: str) -> dict | None:
        user = await self.collection.find_one({"email": email.lower()})
        return self._serialize(user)

    async def get_by_id(self, user_id: str) -> dict | None:
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        return self._serialize(user)

    async def list(self) -> list[dict]:
        cursor = self.collection.find({}).sort("created_at", -1)
        users = await cursor.to_list(None)
        return [self._serialize(user) for user in users if user]

    async def update(self, user_id: str, updates: dict[str, Any]) -> dict | None:
        updates = {key: value for key, value in updates.items() if value is not None}
        if not updates:
            return await self.get_by_id(user_id)
        updates["updated_at"] = datetime.utcnow()
        try:
            await self.collection.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
        except Exception:
            return None
        return await self.get_by_id(user_id)

    def _serialize(self, user: dict | None) -> dict | None:
        if not user:
            return None
        user["_id"] = str(user["_id"])
        return user
