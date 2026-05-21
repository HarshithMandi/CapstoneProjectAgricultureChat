from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from app.db.mongo import get_documents_collection


class DocumentRepository:
    def __init__(self, collection: AsyncIOMotorCollection | None = None):
        self.collection = collection or get_documents_collection()

    async def create(self, document: dict) -> dict:
        document["created_at"] = datetime.utcnow()
        result = await self.collection.insert_one(document)
        return {"_id": str(result.inserted_id), **document}

    async def get(self, document_id: str) -> dict | None:
        doc = await self.collection.find_one({"_id": document_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def get_by_chunk_id(self, chunk_id: str) -> dict | None:
        doc = await self.collection.find_one({"chunks.id": chunk_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc