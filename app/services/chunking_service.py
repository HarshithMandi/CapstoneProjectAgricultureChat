from langchain_core.documents import Document
from app.langchain_components.splitters import get_recursive_splitter, split_documents
from app.langchain_components.documents import create_document
from app.utils.ids import generate_document_id


class ChunkingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = get_recursive_splitter(chunk_size, chunk_overlap)

    def chunk_text(
        self,
        text: str,
        metadata: dict,
        doc_id: str | None = None,
    ) -> list[Document]:
        doc_id = doc_id or generate_document_id()
        doc = create_document(text, metadata, doc_id=doc_id)
        chunks = split_documents([doc], self.splitter)

        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            chunk.metadata["chunk_id"] = f"{doc_id}_chunk_{i}"

        return chunks

    def chunk_multiple(
        self,
        texts: list[tuple[str, dict]],
    ) -> list[Document]:
        all_chunks = []
        for text, metadata in texts:
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
        return all_chunks