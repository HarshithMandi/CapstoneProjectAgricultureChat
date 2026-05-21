"""Script to reindex all documents."""
import asyncio
from app.db.chroma import get_chroma_client
from app.db.mongo import get_documents_collection


async def main():
    client = get_chroma_client()
    collection = client.get_collection("agri_documents")
    print(f"Current collection has {collection.count()} documents")