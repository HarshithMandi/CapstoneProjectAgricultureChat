from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

try:
    from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError
except Exception:  # pragma: no cover - pymongo is installed in normal environments
    AutoReconnect = ServerSelectionTimeoutError = Exception

client: AsyncIOMotorClient | None = None
_fallback_db: "InMemoryDatabase | None" = None


def _is_connectivity_error(exc: Exception) -> bool:
    return isinstance(exc, (AutoReconnect, ServerSelectionTimeoutError, OSError))


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        actual = document.get(key)
        if key == "_id":
            if str(actual) != str(expected):
                return False
            continue
        if actual != expected:
            return False
    return True


@dataclass
class InMemoryInsertOneResult:
    inserted_id: ObjectId


@dataclass
class InMemoryDeleteResult:
    deleted_count: int


@dataclass
class InMemoryUpdateResult:
    matched_count: int = 0
    modified_count: int = 0


class InMemoryCursor:
    def __init__(self, documents: list[dict[str, Any]]):
        self._documents = documents

    def sort(self, key: str, direction: int):
        reverse = direction < 0

        def sort_key(document: dict[str, Any]):
            value = document.get(key)
            return (value is None, value)

        self._documents = sorted(self._documents, key=sort_key, reverse=reverse)
        return self

    async def to_list(self, length: int | None):
        if length is None:
            return [document.copy() for document in self._documents]
        return [document.copy() for document in self._documents[:length]]


class InMemoryCollection:
    def __init__(self, name: str, database: "InMemoryDatabase"):
        self.name = name
        self.database = database
        self._documents: list[dict[str, Any]] = []

    async def insert_one(self, document: dict[str, Any]):
        stored = document.copy()
        stored.setdefault("_id", ObjectId())
        self._documents.append(stored)
        return InMemoryInsertOneResult(inserted_id=stored["_id"])

    async def find_one(self, query: dict[str, Any]):
        for document in self._documents:
            if _matches(document, query):
                return document.copy()
        return None

    async def count_documents(self, query: dict[str, Any]):
        return sum(1 for document in self._documents if _matches(document, query))

    def find(self, query: dict[str, Any]):
        matches = [document.copy() for document in self._documents if _matches(document, query)]
        return InMemoryCursor(matches)

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        for document in self._documents:
            if not _matches(document, query):
                continue
            updates = update.get("$set", update)
            document.update(updates)
            return InMemoryUpdateResult(matched_count=1, modified_count=1)
        return InMemoryUpdateResult()

    async def delete_one(self, query: dict[str, Any]):
        for index, document in enumerate(self._documents):
            if _matches(document, query):
                self._documents.pop(index)
                return InMemoryDeleteResult(deleted_count=1)
        return InMemoryDeleteResult(deleted_count=0)

    async def delete_many(self, query: dict[str, Any]):
        kept = []
        deleted = 0
        for document in self._documents:
            if _matches(document, query):
                deleted += 1
            else:
                kept.append(document)
        self._documents = kept
        return InMemoryDeleteResult(deleted_count=deleted)


class InMemoryDatabase:
    def __init__(self):
        self._collections: dict[str, InMemoryCollection] = {}

    def __getitem__(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection(name, self)
        return self._collections[name]


@dataclass
class ResilientCollection:
    motor_collection: Any
    fallback_collection: InMemoryCollection
    _using_fallback: bool = False

    @property
    def database(self):
        if self._using_fallback:
            return self.fallback_collection.database
        return self.motor_collection.database

    def _switch_to_fallback(self, exc: Exception):
        global _fallback_db
        if _fallback_db is None:
            _fallback_db = self.fallback_collection.database
        self._using_fallback = True
        return self.fallback_collection

    async def insert_one(self, document: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.insert_one(document)
        try:
            return await self.motor_collection.insert_one(document)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).insert_one(document)
            raise

    async def find_one(self, query: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.find_one(query)
        try:
            return await self.motor_collection.find_one(query)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).find_one(query)
            raise

    async def count_documents(self, query: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.count_documents(query)
        try:
            return await self.motor_collection.count_documents(query)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).count_documents(query)
            raise

    def find(self, query: dict[str, Any]):
        if self._using_fallback:
            return self.fallback_collection.find(query)
        try:
            return self.motor_collection.find(query)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return self._switch_to_fallback(exc).find(query)
            raise

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.update_one(query, update)
        try:
            return await self.motor_collection.update_one(query, update)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).update_one(query, update)
            raise

    async def delete_one(self, query: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.delete_one(query)
        try:
            return await self.motor_collection.delete_one(query)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).delete_one(query)
            raise

    async def delete_many(self, query: dict[str, Any]):
        if self._using_fallback:
            return await self.fallback_collection.delete_many(query)
        try:
            return await self.motor_collection.delete_many(query)
        except Exception as exc:
            if _is_connectivity_error(exc):
                return await self._switch_to_fallback(exc).delete_many(query)
            raise


def _get_fallback_db() -> InMemoryDatabase:
    global _fallback_db
    if _fallback_db is None:
        _fallback_db = InMemoryDatabase()
    return _fallback_db


def get_mongo_client() -> AsyncIOMotorClient:
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client


def get_db():
    return get_mongo_client()[settings.MONGODB_DB]


def _wrap_collection(collection_name: str):
    motor_collection = get_db()[collection_name]
    fallback_collection = _get_fallback_db()[collection_name]
    return ResilientCollection(motor_collection=motor_collection, fallback_collection=fallback_collection)


async def close_mongo_client():
    global client
    if client:
        client.close()
        client = None


def get_sessions_collection():
    return _wrap_collection("sessions")


def get_messages_collection():
    return _wrap_collection("messages")


def get_documents_collection():
    return _wrap_collection("documents")


def get_users_collection():
    return _wrap_collection("users")
