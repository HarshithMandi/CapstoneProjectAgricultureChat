from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client


def get_db():
    return get_mongo_client()[settings.MONGODB_DB]


async def close_mongo_client():
    global client
    if client:
        client.close()
        client = None


def get_sessions_collection():
    return get_db()["sessions"]


def get_messages_collection():
    return get_db()["messages"]


def get_documents_collection():
    return get_db()["documents"]


def get_users_collection():
    return get_db()["users"]
