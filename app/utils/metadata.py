from datetime import datetime
from typing import Any


def create_metadata(
    source: str,
    title: str | None = None,
    url: str | None = None,
    topic: str = "general",
    document_type: str = "text",
    **kwargs: Any,
) -> dict[str, Any]:
    metadata = {
        "source": source,
        "title": title or "",
        "url": url or "",
        "topic": topic,
        "document_type": document_type,
        "ingestion_timestamp": datetime.utcnow().isoformat(),
    }
    metadata.update(kwargs)
    return metadata


def merge_metadata(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    result.update(updates)
    return result