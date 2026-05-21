from typing import Any
from langchain_core.documents import Document
from datetime import datetime
import uuid


def create_document(
    content: str,
    metadata: dict[str, Any] | None = None,
    doc_id: str | None = None,
    chunk_id: str | None = None,
) -> Document:
    chunk_id = chunk_id or str(uuid.uuid4())
    doc_id = doc_id or str(uuid.uuid4())

    default_metadata = {
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "source": "unknown",
        "title": "",
        "url": "",
        "topic": "general",
        "chunk_index": 0,
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "document_type": "text",
    }

    if metadata:
        default_metadata.update(metadata)

    return Document(page_content=content, metadata=default_metadata)


def metadata_from_source(
    source: str,
    title: str | None = None,
    topic: str | None = None,
    url: str | None = None,
    document_type: str = "text",
) -> dict[str, Any]:
    return {
        "source": source,
        "title": title or "",
        "topic": topic or "general",
        "url": url or "",
        "document_type": document_type,
    }