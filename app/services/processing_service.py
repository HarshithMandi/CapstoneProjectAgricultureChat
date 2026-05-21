from app.utils.text import clean_text, normalize_agriculture_terms, remove_duplicate_lines
from app.utils.metadata import create_metadata
from urllib.parse import urlparse


def _looks_like_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class ProcessingService:
    def __init__(self):
        pass

    def process_text(self, text: str, **metadata) -> tuple[str, dict]:
        cleaned = clean_text(text)
        cleaned = normalize_agriculture_terms(cleaned)
        cleaned = remove_duplicate_lines(cleaned)

        doc_metadata = create_metadata(
            source=metadata.get("source", "unknown"),
            title=metadata.get("title"),
            url=metadata.get("url") or (metadata.get("source") if _looks_like_url(metadata.get("source")) else None),
            topic=metadata.get("topic", "general"),
            document_type=metadata.get("document_type", "text"),
        )

        return cleaned, doc_metadata

    def process_documents(self, documents: list[dict]) -> list[tuple[str, dict]]:
        results = []
        for doc in documents:
            processed_text, metadata = self.process_text(
                doc.get("content", ""),
                source=doc.get("source", "unknown"),
                title=doc.get("title"),
                url=doc.get("url"),
                topic=doc.get("topic", "general"),
                document_type=doc.get("document_type", "text"),
            )
            results.append((processed_text, metadata))
        return results
