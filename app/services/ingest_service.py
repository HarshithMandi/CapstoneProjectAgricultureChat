from app.services.scraping_service import ScrapingService
from app.services.processing_service import ProcessingService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.db.repositories.document import DocumentRepository
from app.langchain_components.documents import create_document


class IngestService:
    def __init__(self):
        self.scraping = ScrapingService()
        self.processing = ProcessingService()
        self.chunking = ChunkingService()
        self.embedding = EmbeddingService()
        self.doc_repo = DocumentRepository()

    async def ingest_url(self, url: str, title: str | None = None, topic: str | None = None) -> dict:
        scraped = await self.scraping.scrape_url(url)
        text = scraped["content"]
        title = title or scraped["title"]

        processed_text, metadata = self.processing.process_text(
            text,
            source=url,
            title=title,
            url=url,
            topic=topic,
            document_type="webpage",
        )

        chunks = self.chunking.chunk_text(processed_text, metadata)
        chunk_ids = await self.embedding.embed_and_store(chunks)

        doc_record = {
            "url": url,
            "title": title,
            "topic": topic or metadata["topic"],
            "chunk_ids": chunk_ids,
            "status": "ingested",
        }
        await self.doc_repo.create(doc_record)

        return {"document_ids": [metadata["doc_id"]], "chunks_created": len(chunk_ids)}

    async def ingest_text(
        self,
        text: str,
        title: str | None = None,
        source: str = "manual",
        topic: str = "general",
        document_type: str = "text",
    ) -> dict:
        processed_text, metadata = self.processing.process_text(
            text,
            source=source,
            title=title,
            topic=topic,
            document_type=document_type,
        )

        chunks = self.chunking.chunk_text(processed_text, metadata)
        chunk_ids = await self.embedding.embed_and_store(chunks)

        return {"document_ids": [metadata["doc_id"]], "chunks_created": len(chunk_ids)}

    async def ingest_urls(self, urls: list[str], topic: str | None = None) -> dict:
        results = []
        total_chunks = 0

        for url in urls:
            result = await self.ingest_url(url, topic=topic)
            results.extend(result["document_ids"])
            total_chunks += result["chunks_created"]

        return {"document_ids": results, "chunks_created": total_chunks}

    async def close(self):
        await self.scraping.close()
        await self.embedding.close()